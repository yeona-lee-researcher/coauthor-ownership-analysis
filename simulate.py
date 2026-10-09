"""Descriptive semi-Markov process model and microsimulation of CoAuthor writing sessions.

Usage: python simulate.py --input data/raw/coauthor_metadata.xlsx --results results [--reps 100]
Requires results/process/episodes.csv (process_logs.py).

Model (fit separately per genre; writer-specific variants shrink toward the genre population)
  tokens       W (writing burst), P (pause >= 10 s), QA / QR / QN (request accepted / rejected / unanswered)
  transitions  first-order Markov; writer rows p_w = (n_w + kappa * p_pop) / (N_w + kappa)
  emissions    joint (span seconds, human chars inserted, AI chars inserted) resampled from the
               writer's own episodes with prob N_wk / (N_wk + kappa_e), else from the genre pool
  stopping     empirical discrete hazard of ending after a unit, by 30-s bins of elapsed time;
               writer hazards shrink toward the genre hazard with weight kappa_h
  sessions     optional session-level heterogeneity: each simulated session draws its transition
               rows from Dirichlet(alpha * p); alpha scored by sequential Polya-urn likelihood

Validation
  A  writer-grouped 5-fold CV on held-out writers: zero-order (M0), first-order (M1), and M1 with
     session heterogeneity (M1+S); alpha tuned on an inner writer split of each training fold
  B  within-writer temporal holdout (writers with >= 6 sessions): population M1 vs writer-shrunk M1
     vs writer-shrunk M1 with writer stopping and session heterogeneity; kappa, kappa_h, alpha tuned
     on an inner (earlier vs later) split of the training sessions only
Uses
  C  variance decomposition: share of session-to-session variance attributable to writer parameters
  D  model-implied scenario (NOT a causal effect): unanswered requests answered instead

The model describes observed behavior; latent states, personality, or motivation are not inferred.
"""
from pathlib import Path
import argparse, json
import numpy as np
import pandas as pd

TOK = ['W', 'P', 'QA', 'QR', 'QN']; K = len(TOK); TI = {t: i for i, t in enumerate(TOK)}
BIN = 30.0; NBIN = 80                       # stopping-hazard bins: 30 s up to 40 min
EPS = 1e-9

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument('--input', required=True)
ap.add_argument('--results', default='results', type=Path)
ap.add_argument('--reps', type=int, default=100, help='Simulated replicates per observed session')
ap.add_argument('--seed', type=int, default=20261009)
A = ap.parse_args(); OUT = A.results / 'simulation'; OUT.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(A.seed)

# ---------------------------------------------------------------- data
raw = pd.read_excel(A.input, sheet_name=['Metadata (creative)', 'Metadata (argumentative)'])
meta = pd.concat([raw['Metadata (creative)'].assign(genre='creative'),
                  raw['Metadata (argumentative)'].assign(genre='argumentative')], ignore_index=True)
meta['session_id'] = meta.session_id.astype(str).str.strip(); meta['worker_id'] = meta.worker_id.astype(str).str.strip()
ep = pd.read_csv(A.results / 'process' / 'episodes.csv').merge(
    meta[['session_id', 'worker_id', 'genre', 'timestamp']], on='session_id', how='inner').sort_values(['session_id', 'idx'])
ep['end_s'] = ep.start_s + ep.dur_s
ep['span_s'] = ep.end_s - ep.groupby('session_id').end_s.shift(1).fillna(0.0)   # unit + preceding short gap
ep['k'] = ep.token.map(TI)
assert (ep.span_s >= -1e-6).all()
GENRES = ['creative', 'argumentative']


def summarize_observed(e):
    g = e.groupby('session_id')
    s = pd.DataFrame({
        'worker_id': g.worker_id.first(), 'genre': g.genre.first(), 'timestamp': g.timestamp.first(),
        'duration_min': g.end_s.max() / 60,
        'n_query': g.token.apply(lambda x: x.str.startswith('Q').sum()),
        'n_accept': g.token.apply(lambda x: (x == 'QA').sum()),
        'human_share': 100 * g.u_ins.sum() / (g.u_ins.sum() + g.a_ins.sum()),
        'first_query_min': g.apply(lambda x: x.loc[x.token.str.startswith('Q'), 'start_s'].min() / 60, include_groups=False),
    })
    return s


obs = summarize_observed(ep)
proc = pd.read_csv(A.results / 'process' / 'session_process.csv').set_index('session_id')
chk = proc.loc[obs.index]
assert np.allclose(obs.human_share, 100 * chk.user_chars_inserted / (chk.user_chars_inserted + chk.api_chars_inserted), equal_nan=True)
SUMM = ['duration_min', 'n_query', 'n_accept', 'human_share', 'first_query_min']


# ---------------------------------------------------------------- fitting
def counts(e):
    """Start counts (K) and transition counts (K x K) from an episode frame."""
    st = np.bincount(e.groupby('session_id').k.first(), minlength=K).astype(float)
    nxt = e.groupby('session_id').k.shift(-1)
    m = nxt.notna()
    tr = np.zeros((K, K)); np.add.at(tr, (e.k[m].to_numpy(), nxt[m].astype(int).to_numpy()), 1)
    return st, tr


def hazard_counts(e):
    last = (e.groupby('session_id').idx.transform('max') == e.idx).to_numpy()
    b = np.minimum((e.end_s // BIN).astype(int), NBIN - 1).to_numpy()
    return np.bincount(b[last], minlength=NBIN), np.bincount(b, minlength=NBIN)


def fit(train, kappa=None, kappa_e=None, kappa_h=None, alpha=None, order=1):
    """Return a model dict. kappa=None -> population only; order=0 -> iid tokens;
    kappa_h -> writer stopping hazards; alpha -> session-level Dirichlet heterogeneity."""
    M = {'pop_start': {}, 'pop_tr': {}, 'hazard': {}, 'pool': {}, 'w_start': {}, 'w_tr': {}, 'w_pool': {},
         'w_hazard': {}, 'kappa': kappa, 'kappa_e': kappa_e, 'kappa_h': kappa_h, 'alpha': alpha, 'order': order}
    for g in GENRES:
        eg = train[train.genre == g]
        st, tr = counts(eg)
        ps = (st + .5) / (st + .5).sum()
        if order == 0:
            marg = np.bincount(eg.k, minlength=K).astype(float); marg = marg / marg.sum()
            pt = np.tile(marg, (K, 1))
        else:
            pt = np.where(tr.sum(1, keepdims=True) > 0, tr / np.maximum(tr.sum(1, keepdims=True), 1), 1 / K)
        M['pop_start'][g], M['pop_tr'][g] = ps, pt
        ends, units = hazard_counts(eg)
        M['hazard'][g] = (ends + .05) / (units + 1.0)
        M['pool'][g] = {k: eg.loc[eg.k == k, ['span_s', 'u_ins', 'a_ins']].to_numpy() for k in range(K)}
        if kappa is not None:
            for w, ew in eg.groupby('worker_id'):
                sw, tw = counts(ew)
                M['w_start'][(w, g)] = (sw + kappa * ps) / (sw.sum() + kappa)
                M['w_tr'][(w, g)] = (tw + kappa * pt) / (tw.sum(1, keepdims=True) + kappa)
                if kappa_e is not None:
                    M['w_pool'][(w, g)] = {k: ew.loc[ew.k == k, ['span_s', 'u_ins', 'a_ins']].to_numpy() for k in range(K)}
                if kappa_h is not None:
                    ew_e, ew_u = hazard_counts(ew)
                    M['w_hazard'][(w, g)] = (ew_e + kappa_h * M['hazard'][g]) / (ew_u + kappa_h)
    return M


def loglik(M, test):
    """Held-out log-likelihood of start tokens and transitions (stopping scored separately).
    With alpha, each session's transitions are scored sequentially under a Polya urn
    (Dirichlet(alpha * p) rows integrated out), i.e. the session-heterogeneity model."""
    ll, n = 0.0, 0
    alpha = M['alpha']
    for (w, g), e in test.groupby(['worker_id', 'genre']):
        ps = M['w_start'].get((w, g), M['pop_start'][g]); pt = M['w_tr'].get((w, g), M['pop_tr'][g])
        st, tr = counts(e)
        ll += (st * np.log(ps + EPS)).sum(); n += st.sum()
        if alpha is None:
            ll += (tr * np.log(pt + EPS)).sum(); n += tr.sum()
            continue
        for _, ks in e.groupby('session_id').k:
            ks = ks.to_numpy(); c = np.zeros((K, K))
            for a, b in zip(ks[:-1], ks[1:]):
                ll += np.log((alpha * pt[a, b] + c[a, b]) / (alpha + c[a].sum()) + EPS); c[a, b] += 1; n += 1
    return ll, n


def hazard_loglik(M, test):
    ll, n = 0.0, 0
    for (w, g), e in test.groupby(['worker_id', 'genre']):
        h = M['w_hazard'].get((w, g), M['hazard'][g]); ends, units = hazard_counts(e)
        ll += (ends * np.log(h + EPS) + (units - ends) * np.log(1 - h + EPS)).sum(); n += units.sum()
    return ll / n


# ---------------------------------------------------------------- simulation
def simulate(M, sessions, reps, rng, scenario=None, max_steps=3000):
    """Vectorised simulation of `reps` replicates for every row of `sessions` (worker_id, genre)."""
    rows = sessions.loc[sessions.index.repeat(reps)].reset_index()
    n = len(rows)
    S0 = np.zeros((n, K)); T = np.zeros((n, K, K)); lam = np.zeros((n, K)); hz = np.zeros(n, int); Hrows = []
    big, gstart, glen, wstart, wlen = [], np.zeros((n, K), int), np.zeros((n, K), int), np.zeros((n, K), int), np.zeros((n, K), int)
    off = 0; seg = {}
    def add(key, arr):
        nonlocal off
        if key not in seg:
            seg[key] = (off, len(arr)); big.append(arr); off += len(arr)
        return seg[key]
    for (w, g), ix in rows.groupby(['worker_id', 'genre']).groups.items():
        ix = np.asarray(ix)
        S0[ix] = M['w_start'].get((w, g), M['pop_start'][g]); T[ix] = M['w_tr'].get((w, g), M['pop_tr'][g])
        hz[ix] = len(Hrows); Hrows.append(M['w_hazard'].get((w, g), M['hazard'][g]))
        for k in range(K):
            gs = add(('g', g, k), M['pool'][g][k]); gstart[ix, k], glen[ix, k] = gs
            wp = M['w_pool'].get((w, g))
            if wp is not None and len(wp[k]):
                ws = add(('w', w, g, k), wp[k]); wstart[ix, k], wlen[ix, k] = ws
                lam[ix, k] = len(wp[k]) / (len(wp[k]) + M['kappa_e'])
    if scenario == 'answer_unanswered':          # move QN mass to QA/QR in proportion, row-wise
        qa, qr, qn = TI['QA'], TI['QR'], TI['QN']
        for P in (T, S0[:, None, :]):
            share = P[..., qa] / np.maximum(P[..., qa] + P[..., qr], EPS)
            P[..., qa] += P[..., qn] * share; P[..., qr] += P[..., qn] * (1 - share); P[..., qn] = 0
    if M['alpha'] is not None:               # session-level heterogeneity in transition rows
        G = rng.gamma(np.maximum(M['alpha'] * T, 1e-8)); T = G / G.sum(2, keepdims=True)
    EM = np.vstack(big); H = np.stack(Hrows)
    cS0, cT = S0.cumsum(1), T.cumsum(2)
    state = (rng.random(n)[:, None] > cS0).sum(1).clip(0, K - 1)
    el = np.zeros(n); U = np.zeros(n); AI = np.zeros(n); nq = np.zeros(n); na = np.zeros(n); fq = np.full(n, np.nan)
    alive = np.ones(n, bool)
    for _ in range(max_steps):
        ids = np.flatnonzero(alive)
        if not len(ids): break
        k = state[ids]
        usew = rng.random(len(ids)) < lam[ids, k]
        st = np.where(usew, wstart[ids, k], gstart[ids, k]); ln = np.where(usew, wlen[ids, k], glen[ids, k])
        e = EM[st + (rng.random(len(ids)) * ln).astype(int)]
        isq = k >= TI['QA']
        first = isq & np.isnan(fq[ids]); fq[ids[first]] = el[ids[first]]
        el[ids] += e[:, 0]; U[ids] += e[:, 1]; AI[ids] += e[:, 2]; nq[ids] += isq; na[ids] += k == TI['QA']
        b = np.minimum((el[ids] // BIN).astype(int), NBIN - 1)
        stop = rng.random(len(ids)) < H[hz[ids], b]
        alive[ids[stop]] = False
        go = ids[~stop]
        state[go] = (rng.random(len(go))[:, None] > cT[go, state[go]]).sum(1).clip(0, K - 1)
    rows = rows.assign(duration_min=el / 60, n_query=nq, n_accept=na,
                       human_share=np.where(U + AI > 0, 100 * U / np.maximum(U + AI, EPS), np.nan), first_query_min=fq / 60)
    return rows


def compare(obs_s, sim):
    """Per-session predictive checks: 90% interval coverage, abs error of simulated median, KS distance."""
    out = {}
    q = sim.groupby('session_id')[SUMM].quantile([.05, .5, .95]).unstack()
    for c in SUMM:
        o = obs_s[c]; lo, med, hi = q[(c, .05)].reindex(o.index), q[(c, .5)].reindex(o.index), q[(c, .95)].reindex(o.index)
        ok = o.notna() & med.notna()
        a, b = np.sort(o.dropna().to_numpy()), np.sort(sim[c].dropna().to_numpy())
        grid = np.union1d(a, b)
        ks = float(np.max(np.abs(np.searchsorted(a, grid, 'right') / len(a) - np.searchsorted(b, grid, 'right') / len(b))))
        out[c] = {'coverage90': float(((o >= lo) & (o <= hi))[ok].mean()), 'abs_err_median': float((o - med).abs()[ok].mean()),
                  'obs_mean': float(o.mean()), 'sim_mean': float(sim[c].mean()), 'obs_sd': float(o.std()), 'sim_sd': float(sim[c].std()), 'ks': ks}
    return out


def boot_writer_mean(df, col, B=2000):
    by = df.groupby('worker_id')[col].agg(['sum', 'count']).to_numpy()
    idx = rng.integers(0, len(by), (B, len(by))); s = by[idx].sum(1)
    return np.quantile(s[:, 0] / s[:, 1], [.025, .975]).tolist()


report = {'sessions': int(obs.shape[0]), 'writers': int(obs.worker_id.nunique()), 'episodes': int(len(ep)),
          'reps_per_session': A.reps, 'seed': A.seed}

ALPHA = [2, 5, 10, 20, 50, 100, 200, 500, 1000]
KAPPA = [1, 2, 5, 10, 20, 50, 100, 200, 500]
KAPPA_H = [1, 5, 20, 50, 100, 200, 500, 2000]


def best(scores):
    return max(scores, key=scores.get)


# ---------------------------------------------------------------- A. held-out writers
writers = np.array(sorted(obs.worker_id.unique())); perm = rng.permutation(writers); folds = np.array_split(perm, 5)
names = ('M0', 'M1', 'M1+S'); llA = {m: [0., 0] for m in names}; simsA = {m: [] for m in names}; alphasA = []
for f in folds:
    te = ep.worker_id.isin(f); tr = ep[~te]
    tw = np.array(sorted(tr.worker_id.unique())); inner = rng.permutation(tw)[: len(tw) // 2]
    itr, iva = tr[~tr.worker_id.isin(inner)], tr[tr.worker_id.isin(inner)]
    sc = {}
    for al in ALPHA:
        l, n = loglik(fit(itr, alpha=al), iva); sc[al] = l / n
    alphasA.append(best(sc))
    for name, kw in (('M0', dict(order=0)), ('M1', {}), ('M1+S', dict(alpha=best(sc)))):
        M = fit(tr, **kw)
        l, n = loglik(M, ep[te]); llA[name][0] += l; llA[name][1] += n
        simsA[name].append(simulate(M, obs.loc[obs.worker_id.isin(f), ['worker_id', 'genre']], A.reps, rng))
report['A_heldout_writers'] = {'alpha_selected_per_fold': alphasA,
                               **{name: {'loglik_per_event': llA[name][0] / llA[name][1],
                                         'checks': compare(obs, pd.concat(simsA[name]))} for name in names}}
simA = pd.concat([pd.concat(v).assign(model=k) for k, v in simsA.items()])

# ---------------------------------------------------------------- B. later sessions of known writers
obs['order'] = obs.groupby('worker_id').timestamp.rank(method='first')
obs['n_w'] = obs.groupby('worker_id').timestamp.transform('size')
elig = obs[obs.n_w >= 6]
test_ids = elig.index[elig.order > elig.n_w / 2]
train_e = ep[~ep.session_id.isin(test_ids)]; test_e = ep[ep.session_id.isin(test_ids)]
# inner split: later half of eligible writers' TRAINING sessions; all tuning uses training data only
tr_obs = obs.loc[~obs.index.isin(test_ids)]
inner_n = tr_obs.groupby('worker_id').timestamp.transform('size')
inner_ord = tr_obs.groupby('worker_id').timestamp.rank(method='first')
inner_test = tr_obs.index[(tr_obs.worker_id.isin(elig.worker_id)) & (inner_ord > inner_n / 2)]
itr, iva = train_e[~train_e.session_id.isin(inner_test)], train_e[train_e.session_id.isin(inner_test)]
tune_k, tune_h, tune_a = {}, {}, {}
for kap in KAPPA:
    l, n = loglik(fit(itr, kappa=kap), iva); tune_k[kap] = l / n
kappa = best(tune_k)
for kh in KAPPA_H:
    tune_h[kh] = hazard_loglik(fit(itr, kappa=kappa, kappa_h=kh), iva)
kappa_h = best(tune_h)
for al in ALPHA:
    l, n = loglik(fit(itr, kappa=kappa, alpha=al), iva); tune_a[al] = l / n
alpha = best(tune_a)
models = {'population': fit(train_e),
          'writer': fit(train_e, kappa=kappa, kappa_e=kappa),
          'writer+stop+S': fit(train_e, kappa=kappa, kappa_e=kappa, kappa_h=kappa_h, alpha=alpha)}


def paired_gain(Ma, Mb, score):
    """Per-writer gain of Mb over Ma on held-out later sessions, with writer-bootstrap CI."""
    r = []
    for w, e in test_e.groupby('worker_id'):
        la, n = score(Ma, e); lb, _ = score(Mb, e); r.append((lb - la, n))
    r = np.array(r); bs = rng.integers(0, len(r), (2000, len(r)))
    return {'per_event': float(r[:, 0].sum() / r[:, 1].sum()),
            'ci95_writer_bootstrap': np.quantile(r[bs, 0].sum(1) / r[bs, 1].sum(1), [.025, .975]).tolist(),
            'writers_with_positive_gain': int((r[:, 0] > 0).sum()), 'writers': len(r)}


def haz_score(M, e):
    return hazard_loglik(M, e) * len(e), len(e)


obsB = obs.loc[test_ids]
simsB = {k: simulate(M, obsB[['worker_id', 'genre']], A.reps, rng) for k, M in models.items()}
errs = {k: (obsB[SUMM] - sim.groupby('session_id')[SUMM].median().reindex(obsB.index)).abs() for k, sim in simsB.items()}
gain = (errs['population'] - errs['writer+stop+S']).assign(worker_id=obsB.worker_id)
report['B_later_sessions'] = {
    'eligible_writers': int(elig.worker_id.nunique()), 'test_sessions': int(len(test_ids)),
    'tuning_inner_loglik': {'kappa': tune_k, 'kappa_h': tune_h, 'alpha': tune_a},
    'selected': {'kappa': kappa, 'kappa_e': kappa, 'kappa_h': kappa_h, 'alpha': alpha},
    'transition_loglik_gain_writer_vs_population': paired_gain(models['population'], models['writer'], loglik),
    'transition_loglik_gain_session_heterogeneity': paired_gain(models['writer'], models['writer+stop+S'], loglik),
    'stopping_loglik_gain_writer_vs_population': paired_gain(models['population'], models['writer+stop+S'], haz_score),
    'checks': {k: compare(obsB, sim) for k, sim in simsB.items()},
    'abs_error_reduction_full_vs_population': {c: {'mean': float(gain[c].mean()), 'ci95_writer_bootstrap': boot_writer_mean(gain.dropna(subset=[c]), c)} for c in SUMM}}

# ---------------------------------------------------------------- C. variance decomposition
Mall = fit(ep, kappa=kappa, kappa_e=kappa, kappa_h=kappa_h, alpha=alpha)
cells = obs.groupby(['worker_id', 'genre']).size().rename('n').reset_index()
cells.index = [f'{w}|{g}' for w, g in zip(cells.worker_id, cells.genre)]; cells.index.name = 'session_id'
simC = simulate(Mall, cells[['worker_id', 'genre']], 200, rng)
def icc(df, col, group):
    d = df.dropna(subset=[col]); gm = d.groupby(group)[col]
    k = gm.size(); n0 = (len(d) - (k ** 2).sum() / len(d)) / (len(k) - 1)
    msb = (k * (gm.mean() - d[col].mean()) ** 2).sum() / (len(k) - 1)
    msw = ((d[col] - gm.transform('mean')) ** 2).sum() / (len(d) - len(k))
    return float(max(0, (msb - msw) / (msb + (n0 - 1) * msw)))
report['C_variance_share_writer'] = {}
for g in GENRES:
    og, sg = obs[obs.genre == g], simC[simC.genre == g]
    report['C_variance_share_writer'][g] = {c: {'observed_icc': icc(og, c, 'worker_id'), 'simulated_icc': icc(sg, c, 'worker_id')}
                                            for c in ['human_share', 'n_query', 'n_accept', 'duration_min']}

# ---------------------------------------------------------------- D. model-implied scenario
seedD = rng.integers(1 << 31)
base = simulate(Mall, obs[['worker_id', 'genre']], A.reps, np.random.default_rng(seedD))
scen = simulate(Mall, obs[['worker_id', 'genre']], A.reps, np.random.default_rng(seedD), scenario='answer_unanswered')
dd = pd.DataFrame({'worker_id': base.worker_id, 'd_accept': scen.n_accept - base.n_accept,
                   'd_human_share': scen.human_share - base.human_share, 'd_query': scen.n_query - base.n_query})
report['D_scenario_answer_unanswered'] = {
    'note': 'Model-implied under the fitted descriptive model; not a causal or intervention effect.',
    **{c: {'mean': float(dd[c].mean()), 'ci95_writer_bootstrap': boot_writer_mean(dd.dropna(subset=[c]), c)} for c in ['d_accept', 'd_human_share', 'd_query']}}

# ---------------------------------------------------------------- outputs
pd.DataFrame(Mall['pop_tr']['creative'], index=TOK, columns=TOK).to_csv(OUT / 'transitions_creative.csv')
pd.DataFrame(Mall['pop_tr']['argumentative'], index=TOK, columns=TOK).to_csv(OUT / 'transitions_argumentative.csv')
obs.to_csv(OUT / 'observed_sessions.csv')
simA[['model', 'session_id', 'genre'] + SUMM].to_csv(OUT / 'simulated_heldout_writers.csv', index=False)
gain.to_csv(OUT / 'later_sessions_error_reduction.csv')
(OUT / 'simulation_report.json').write_text(json.dumps(report, indent=2, default=float))
print(json.dumps(report, indent=1, default=lambda x: round(float(x), 4)))
