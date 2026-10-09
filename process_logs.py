"""Replay CoAuthor interaction logs into session process features and an episode sequence.

Usage: python process_logs.py --logs <coauthor-v1.0 dir> --out results/process

Each .jsonl log is replayed delta by delta while tracking the provenance of every
character (p = prompt, u = user, a = API suggestion). The replayed human share of the
final text is compared with metadata `written_by_human` in the analysis step as a
correctness check of the replay.

Episode tokens (the unit of the process model and microsimulation):
  W   writing burst: consecutive user text events with gaps < --pause seconds
  P   pause: a gap >= --pause seconds between activity units
  QA  query whose suggestions were shown and one was selected (accepted)
  QR  query whose suggestions were shown and none was selected (rejected/dismissed)
  QN  query with no suggestions shown before the writer resumed; `answered_late` marks those
      whose suggestions appeared later, which then start a display episode with origin 'late'.
      Only never-answered QN count toward the unanswered rate. `suggestion-reopen` starts a
      display episode with origin 'reopen'; n_query counts user requests (origin 'request').
Pauses are observed inactivity, not "being stuck".
"""
from pathlib import Path
import argparse, json
import numpy as np
import pandas as pd

TEXT = ('text-insert', 'text-delete')


def apply_delta(labels, ops, source, counts):
    """Apply a Quill delta to the per-character label list; return the new list."""
    out, pos = [], 0
    for op in ops:
        if 'retain' in op:
            n = op['retain']; out.extend(labels[pos:pos + n]); pos += n
        elif 'insert' in op:
            ins = op['insert']
            n = len(ins) if isinstance(ins, str) else 1
            out.extend(source * n)
            counts[f'{source}_ins'] += n
        elif 'delete' in op:
            gone = labels[pos:pos + op['delete']]; pos += op['delete']
            if source == 'u':
                counts['u_del'] += len(gone)
                counts['a_del_by_u'] += gone.count('a')
    out.extend(labels[pos:])
    return out


def replay(path, pause):
    ev = [json.loads(line) for line in open(path, encoding='utf-8')]
    ev.sort(key=lambda e: e['eventNum'])
    init = ev[0]
    assert init['eventName'] == 'system-initialize', path
    labels = ['p'] * len(init['currentDoc'])
    counts = dict(u_ins=0, a_ins=0, u_del=0, a_del_by_u=0)
    t0 = init['eventTimestamp']
    episodes = []          # dicts: token, start, end, u_ins, u_del, a_ins, a_del, n_sugg, latency
    cur = None             # open writing burst
    query = None           # open query episode
    last_end = None

    def close_burst():
        nonlocal cur, last_end
        if cur is not None:
            episodes.append(cur); last_end = cur['end']; cur = None

    def close_query(token, t):
        nonlocal query, last_end
        query.update(token=token, end=t); episodes.append(query); last_end = t; query = None

    def start_display(t, origin, n_sugg=np.nan):
        nonlocal query
        close_burst()
        query = new_unit('Q', t); query.update(origin=origin, opened=True, n_sugg=n_sugg, latency=np.nan)

    def new_unit(token, t):
        if last_end is not None and (t - last_end) / 1000 >= pause:
            episodes.append(dict(token='P', start=last_end, end=t))
        return dict(token=token, start=t, end=t, u_ins=0, u_del=0, a_ins=0, a_del=0)

    for e in ev[1:]:
        name, src, t = e['eventName'], e['eventSource'], e['eventTimestamp']
        if name in TEXT and isinstance(e['textDelta'], dict):
            before = dict(counts)
            labels = apply_delta(labels, e['textDelta'].get('ops', []), 'u' if src == 'user' else 'a', counts)
            d = {k: counts[k] - before[k] for k in counts}
            if src == 'api':
                if query is not None:
                    query['a_ins'] += d['a_ins']
                    if query.get('selected'):
                        close_query('QA', t)
                elif episodes and episodes[-1]['token'] == 'QA':
                    episodes[-1]['a_ins'] += d['a_ins']
                continue
            # user text: resolves any pending query, then extends or starts a burst
            if query is not None:
                close_query('QA' if query.get('selected') else ('QR' if query.get('opened') else 'QN'), t)
            if cur is not None and (t - cur['end']) / 1000 >= pause:
                close_burst()
            if cur is None:
                cur = new_unit('W', t)
            cur['end'] = t
            cur['u_ins'] += d['u_ins']; cur['u_del'] += d['u_del']; cur['a_del'] += d['a_del_by_u']
        elif name == 'suggestion-get' and src == 'user':
            close_burst()
            if query is not None:   # re-request before resolution
                close_query('QR' if query.get('opened') else 'QN', t)
            query = new_unit('Q', t); query.update(get_t=t, origin='request')
        elif name == 'suggestion-open':
            if query is None:       # suggestions displayed after the writer had resumed typing
                last_q = next((x for x in reversed(episodes) if x['token'].startswith('Q')), None)
                if last_q is not None and last_q['token'] == 'QN':
                    last_q['answered_late'] = True
                start_display(t, 'late', len(e['currentSuggestions']))
            elif not query.get('opened'):
                query.update(opened=True, n_sugg=len(e['currentSuggestions']), latency=(t - query['get_t']) / 1000)
        elif name == 'suggestion-reopen' and src == 'user':
            if query is not None:
                close_query('QR' if query.get('opened') else 'QN', t)
            start_display(t, 'reopen')
        elif name == 'suggestion-select':
            if query is None:       # selection from a panel left open while typing
                start_display(t, 'late')
            query['selected'] = True
        elif name == 'suggestion-close' and query is not None and src == 'user' and not query.get('selected'):
            close_query('QR', t)
    close_burst()
    if query is not None:
        close_query('QA' if query.get('selected') else ('QR' if query.get('opened') else 'QN'), ev[-1]['eventTimestamp'])
    t_end = ev[-1]['eventTimestamp']
    return labels, counts, episodes, t0, t_end


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--logs', required=True, type=Path)
    ap.add_argument('--out', default='results/process', type=Path)
    ap.add_argument('--pause', type=float, default=10.0, help='Pause threshold in seconds (default 10)')
    a = ap.parse_args(); a.out.mkdir(parents=True, exist_ok=True)
    files = sorted(a.logs.glob('*.jsonl'))
    if not files:
        raise SystemExit(f'No .jsonl logs in {a.logs}')
    sess, eps = [], []
    for f in files:
        labels, c, episodes, t0, t_end = replay(f, a.pause)
        sid = f.stem
        nu, na = labels.count('u'), labels.count('a')
        toks = [x['token'] for x in episodes]
        q = [x for x in episodes if x['token'].startswith('Q')]
        req = [x for x in q if x.get('origin') == 'request']
        unans = [x for x in q if x['token'] == 'QN' and not x.get('answered_late')]
        first_q = (q[0]['start'] - t0) / 1000 if q else np.nan
        dur = (t_end - t0) / 1000
        shown = [x for x in q if x.get('opened')]
        sess.append(dict(
            session_id=sid, duration_s=dur, final_chars_user=nu, final_chars_api=na,
            replay_human_share=100 * nu / (nu + na) if nu + na else np.nan,
            user_chars_inserted=c['u_ins'], user_chars_deleted=c['u_del'],
            api_chars_inserted=c['a_ins'], api_chars_deleted_by_user=c['a_del_by_u'],
            ai_revision_rate=c['a_del_by_u'] / c['a_ins'] if c['a_ins'] else np.nan,
            n_query=len(req), n_display_episodes=len(q), n_accept=toks.count('QA'), n_reject=toks.count('QR'),
            n_unanswered=len(unans), n_answered_late=sum(1 for x in q if x.get('answered_late')),
            n_reopen=sum(1 for x in q if x.get('origin') == 'reopen'),
            unanswered_rate=len(unans) / len(req) if req else np.nan,
            accept_rate=toks.count('QA') / len(shown) if shown else np.nan,
            mean_n_suggestions=np.nanmean([x['n_sugg'] for x in shown]) if any(x.get('origin') == 'request' for x in shown) else np.nan,
            median_latency_s=np.nanmedian([x['latency'] for x in shown if x.get('origin') == 'request']) if any(x.get('origin') == 'request' for x in shown) else np.nan,
            time_to_first_query_s=first_q, first_query_frac=first_q / dur if q and dur > 0 else np.nan,
            n_pauses=toks.count('P'), n_bursts=toks.count('W')))
        for i, x in enumerate(episodes):
            eps.append(dict(session_id=sid, idx=i, token=x['token'], start_s=(x['start'] - t0) / 1000,
                            dur_s=(x['end'] - x['start']) / 1000, u_ins=x.get('u_ins', 0), u_del=x.get('u_del', 0),
                            a_ins=x.get('a_ins', 0), a_del=x.get('a_del', 0),
                            n_sugg=x.get('n_sugg', np.nan), latency_s=x.get('latency', np.nan),
                            origin=x.get('origin', ''), answered_late=bool(x.get('answered_late', False))))
    S, E = pd.DataFrame(sess), pd.DataFrame(eps)
    S.to_csv(a.out / 'session_process.csv', index=False)
    E.to_csv(a.out / 'episodes.csv', index=False)
    print(f'{len(S)} sessions, {len(E)} episodes -> {a.out}')
    print(E.token.value_counts().to_string())


if __name__ == '__main__':
    main()
