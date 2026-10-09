"""Exploratory models linking replayed log process features to survey ratings and to local behavior.

Usage: python process_models.py --input data/raw/coauthor_metadata.xlsx --results results
Requires results/analysis_data.csv (analyze.py) and results/process/*.csv (process_logs.py).
All analyses were specified AFTER the primary survey results and qualitative coding (post hoc);
they are reported in full and are not confirmatory.

  E0  replay validation against metadata (human share of inserted characters, query counts)
  E1  within-writer unanswered-request rate / latency / suggestions shown  -> perceived understanding
  E2  within-writer revision of AI-inserted text                           -> ownership
  E3  idle time before requests; share of pauses (10/20/30 s) after writing that end in a request
  E4  human characters typed in the 30/60 s after a query, by query outcome (writer FE)
"""
from pathlib import Path
import argparse, json
import numpy as np
import pandas as pd
from stats_core import design, ordinal_gee, logistic_cluster, cluster_ols, tidy

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument('--input', required=True, help='CoAuthor XLSX workbook')
ap.add_argument('--results', default='results', type=Path)
A = ap.parse_args(); P = A.results / 'process'
raw = pd.read_excel(A.input, sheet_name=['Metadata (creative)', 'Metadata (argumentative)'])
meta = pd.concat([raw['Metadata (creative)'].assign(genre='creative'),
                  raw['Metadata (argumentative)'].assign(genre='argumentative')], ignore_index=True)
meta['session_id'] = meta.session_id.astype(str).str.strip(); meta['worker_id'] = meta.worker_id.astype(str).str.strip()
proc = pd.read_csv(P / 'session_process.csv'); eps = pd.read_csv(P / 'episodes.csv')
rows, audit = [], {}

# E0. Replay validation -------------------------------------------------------------
v = meta.merge(proc, on='session_id', how='inner')
ins_share = 100 * v.user_chars_inserted / (v.user_chars_inserted + v.api_chars_inserted)
audit['E0_replay_validation'] = {
    'logs': len(proc), 'matched_to_metadata': len(v), 'logs_without_metadata': int((~proc.session_id.isin(meta.session_id)).sum()),
    'duration_ratio_log_to_metadata_time': v.duration_s.div(60).div(v.time).describe()[['mean', 'min', 'max']].to_dict(),
    'inserted_char_human_share_within_1pp': float(((ins_share - v.written_by_human).abs() <= 1).mean()),
    'final_text_human_share_within_1pp': float(((v.replay_human_share - v.written_by_human).abs() <= 1).mean()),
    'final_vs_inserted_definition_note': 'metadata written_by_human matches the human share of INSERTED characters, not of the final text',
    'num_query_equals_answered_queries': float(((v.n_accept + v.n_reject) == v.num_query).mean()),
    'num_query_equals_all_requests': float((v.n_query == v.num_query).mean()),
    'num_selected_equals_replayed_accepts': float((v.n_accept == v.num_selected).mean()),
    'requests_total': int(v.n_query.sum()), 'requests_unanswered': int(v.n_unanswered.sum()),
    'sessions_with_unanswered_request': int((v.n_unanswered > 0).sum()),
}

# Survey-linked session data (primary analysis sample from analyze.py) ----------------
d = pd.read_csv(A.results / 'analysis_data.csv').merge(proc, on='session_id', how='inner', validate='one_to_one')
d['unanswered10'] = 10 * d.unanswered_rate          # per 10 percentage points
d['log_latency'] = np.log(d.median_latency_s)
d['revision10'] = 10 * d.ai_revision_rate
def split(df, cols):
    df = df.copy()
    for c in cols:
        df[c + '_b'] = df.groupby('worker_id')[c].transform('mean'); df[c + '_w'] = df[c] - df[c + '_b']
    return df
CTRL = 'human10_w + human10_b + C(prompt_code) + high_creative + high_argumentative'

# E1. Availability -> perceived understanding
e1 = split(d.dropna(subset=['unanswered10', 'log_latency', 'mean_n_suggestions']), ['unanswered10', 'log_latency', 'mean_n_suggestions', 'human10'])
cols, f = ordinal_gee(e1, 'unanswered10_w + unanswered10_b + log_latency_w + log_latency_b + mean_n_suggestions_w + mean_n_suggestions_b + ' + CTRL, 'understanding')
rows += tidy('E1_understanding_availability', cols, f)
audit['E1_n'] = {'sessions': len(e1), 'writers': e1.worker_id.nunique()}

# E2. Revising AI text -> ownership (sessions with at least one accepted AI insertion)
e2 = split(d.dropna(subset=['revision10']), ['revision10', 'human10', 'understanding'])
cols, f = ordinal_gee(e2, 'revision10_w + revision10_b + understanding_w + understanding_b + ' + CTRL, 'ownership')
rows += tidy('E2_ownership_ai_revision', cols, f)
audit['E2_n'] = {'sessions': len(e2), 'writers': e2.worker_id.nunique(),
                 'ai_revision_rate': e2.ai_revision_rate.describe()[['mean', '50%', '75%']].to_dict()}

# E3. Pauses and requests (all logged sessions with metadata) ---------------------------
ep = eps.merge(meta[['session_id', 'worker_id', 'genre']], on='session_id', how='inner')
ep = ep.sort_values(['session_id', 'idx'])
ep['prev_tok'] = ep.groupby('session_id').token.shift(1)
# Descriptive by design: bursts are split only by pauses, so "pause -> more writing" is
# structural and a regression of next-unit type on the pause would be tautological.
# Instead: (a) idle time between the last writing event and each request;
# (b) among pauses >= tau after writing, the share that end in a request.
nonp = ep[ep.token != 'P'].copy()
nonp['prev_unit'] = nonp.groupby('session_id').token.shift(1)
nonp['prev_unit_end'] = nonp.groupby('session_id').apply(lambda g: (g.start_s + g.dur_s).shift(1), include_groups=False).reset_index(level=0, drop=True)
reqs = nonp[nonp.token.str.startswith('Q') & (nonp.prev_unit == 'W')].copy()
reqs['idle_s'] = reqs.start_s - reqs.prev_unit_end
rng = np.random.default_rng(20261009); writers = reqs.worker_id.unique()
def boot_share(df, col, B=1000):
    by = df.groupby('worker_id')[col].agg(['sum', 'count']).reindex(writers).fillna(0).to_numpy()
    idx = rng.integers(0, len(by), (B, len(by))); s = by[idx].sum(axis=1)
    return np.quantile(s[:, 0] / s[:, 1], [.025, .975]).tolist()
e3 = {'requests_after_writing': len(reqs), 'writers': int(len(writers)),
      'idle_before_request_s_quantiles': dict(zip(['10%', '25%', '50%', '75%', '90%'], np.quantile(reqs.idle_s, [.1, .25, .5, .75, .9]).round(2).tolist()))}
pz = ep[(ep.token == 'P') & (ep.prev_tok == 'W')].copy()
pz['next_tok'] = ep.groupby('session_id').token.shift(-1).loc[pz.index]
pz = pz.dropna(subset=['next_tok']); pz['to_query'] = pz.next_tok.str.startswith('Q').astype(int)
for tau in (10, 20, 30):
    reqs[f'ge{tau}'] = (reqs.idle_s >= tau).astype(int)
    z = pz[pz.dur_s >= tau]
    e3[f'tau_{tau}s'] = {'share_requests_preceded_by_idle_ge_tau': float(reqs[f'ge{tau}'].mean()),
                         'ci95_writer_bootstrap': boot_share(reqs, f'ge{tau}'),
                         'pauses_after_writing_ge_tau': len(z), 'share_of_those_pauses_ending_in_request': float(z.to_query.mean()),
                         'ci95_writer_bootstrap_pause_to_request': boot_share(z, 'to_query')}
audit['E3_pause_and_request'] = e3
dur = ep.groupby('session_id').apply(lambda g: (g.start_s + g.dur_s).max(), include_groups=False).rename('sess_end')

# E4. Human writing after a query, by outcome -----------------------------------------
W = ep[ep.token == 'W'][['session_id', 'start_s', 'dur_s', 'u_ins']]
Wg = {s: g.to_numpy() for s, g in W.groupby('session_id')[['start_s', 'dur_s', 'u_ins']]}
Q = ep[ep.token.str.startswith('Q')].merge(dur, on='session_id').copy()
Q['q_end'] = Q.start_s + Q.dur_s
def typed_after(row, win):
    g = Wg.get(row.session_id)
    if g is None: return 0.0
    s, du, n = g[:, 0], np.maximum(g[:, 1], 1e-3), g[:, 2]
    lo, hi = row.q_end, row.q_end + win
    overlap = np.clip(np.minimum(s + du, hi) - np.maximum(s, lo), 0, None) / du   # proportional allocation
    return float((n * np.clip(overlap, 0, 1)).sum())
for win in (30, 60):
    q = Q[Q.q_end + win <= Q.sess_end].copy()        # drop windows censored by session end
    q['chars'] = [typed_after(r, win) for r in q.itertuples()]
    q['outcome'] = pd.Categorical(q.token, ['QA', 'QR', 'QN'])
    X = design(q, 'C(outcome) + C(worker_id)', intercept=True)
    f = cluster_ols(X, q.chars, q.worker_id)
    rows += [r for r in tidy(f'E4_human_chars_after_query_{win}s', X.columns, f, odds=False) if not r['term'].startswith('worker_id')]
    audit[f'E4_{win}s'] = {'queries': len(q), 'mean_chars_by_outcome': q.groupby('outcome', observed=True).chars.mean().round(2).to_dict()}

# Descriptives of process features in the survey-linked sample ----------------------
feat = ['n_query', 'n_unanswered', 'unanswered_rate', 'accept_rate', 'mean_n_suggestions', 'median_latency_s',
        'ai_revision_rate', 'time_to_first_query_s', 'first_query_frac', 'n_pauses']
d.groupby('genre')[feat].agg(['mean', 'std', 'median']).to_csv(P / 'process_descriptives.csv')
res = pd.DataFrame(rows); res.to_csv(P / 'process_models.csv', index=False)
(P / 'process_audit.json').write_text(json.dumps(audit, indent=2, default=float))
focal = res[~res.term.str.startswith(('threshold_', 'prompt_code', 'Intercept', 'elapsed_bin', 'high_'))]
print(json.dumps(audit, indent=2, default=float))
print(focal[['model', 'term', 'beta', 'ci_low', 'ci_high', 'p'] + (['OR', 'OR_low', 'OR_high'] if 'OR' in focal else [])].round(4).to_string(index=False))
