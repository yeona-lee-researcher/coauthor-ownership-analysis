"""Shared estimators: design matrices, cluster-robust logistic GEE, ordinal GEE, cluster OLS.

Working-independence GEE with a cluster sandwich, G/(G-1) correction, and t(G-1) intervals.
Used by analyze.py (survey models) and process_models.py (log-derived models).
"""
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit
from scipy.stats import t


def design(d, rhs, intercept=False):
    parts = []
    if intercept: parts.append(pd.DataFrame({'Intercept': np.ones(len(d))}, index=d.index))
    for term in rhs.split(' + '):
        if term.startswith('C('):
            c = term[2:-1]; parts.append(pd.get_dummies(d[c], prefix=c, drop_first=True, dtype=float))
        elif ':' in term:
            a, b = term.split(':'); parts.append(pd.DataFrame({term: d[a] * d[b]}, index=d.index))
        else: parts.append(d[[term]].astype(float))
    return pd.concat(parts, axis=1)


def logistic_cluster(X, y, groups, equal_person=False):
    Z = X.to_numpy(dtype=float); y = np.asarray(y, dtype=float); n = len(y)
    gc = pd.Categorical(groups); G = len(gc.categories)
    weights = np.ones(n)
    if equal_person: weights = n / (G * np.bincount(gc.codes)[gc.codes])
    def obj(b):
        eta = Z @ b
        return np.sum(weights * (np.logaddexp(0, eta) - y * eta)) / n, Z.T @ (weights * (expit(eta) - y)) / n
    opt = minimize(obj, np.zeros(Z.shape[1]), jac=True, method='BFGS', options={'gtol': 1e-9, 'maxiter': 1000})
    b = opt.x; p = expit(Z @ b); H = Z.T @ ((weights * p * (1 - p))[:, None] * Z)
    inv = np.linalg.inv(H)
    S = np.zeros((G, Z.shape[1])); np.add.at(S, gc.codes, Z * (weights * (y - p))[:, None])
    V = inv @ (S.T @ S) @ inv * (G / (G - 1)); se = np.sqrt(np.maximum(0, np.diag(V)))
    crit = t.ppf(.975, G - 1); pv = 2 * t.sf(np.abs(b / se), G - 1)
    maxscore = float(np.max(np.abs(obj(b)[1])))
    assert maxscore < 1e-6, (opt.message, maxscore)
    return {'b': b, 'se': se, 'lo': b - crit * se, 'hi': b + crit * se, 'p': pv, 'V': V, 'maxscore': maxscore,
            'condition_number': float(np.linalg.cond(H)), 'optimizer_message': str(opt.message)}


def ordinal_stack(d, X, outcome, cuts=range(1, 7)):
    """Stack cumulative indicators 1(Y>k) with one intercept per threshold."""
    cuts = np.asarray(list(cuts)); n = len(d); K = len(cuts)
    Z = pd.DataFrame(np.column_stack([np.tile(np.eye(K), (n, 1)), np.repeat(X.to_numpy(), K, axis=0)]),
                     columns=[f'threshold_{k}' for k in cuts] + list(X.columns))
    y = (d[outcome].to_numpy()[:, None] > cuts).ravel()
    return Z, y


def ordinal_gee(d, rhs, outcome, cluster='worker_id', equal_person=False):
    X = design(d, rhs); Z, y = ordinal_stack(d, X, outcome)
    assert np.linalg.matrix_rank(Z) == Z.shape[1], 'Rank-deficient design'
    f = logistic_cluster(Z, y, np.repeat(d[cluster].to_numpy(), 6), equal_person)
    assert np.all(np.diff(f['b'][:6]) < 0), 'Nonmonotonic cumulative probabilities'
    return Z.columns, f


def cluster_ols(X, y, groups):
    xx = X.to_numpy(dtype=float); yy = np.asarray(y, dtype=float)
    b = np.linalg.lstsq(xx, yy, rcond=None)[0]
    gc = pd.Categorical(groups); G = len(gc.categories); n, p = xx.shape
    S = np.zeros((G, p)); np.add.at(S, gc.codes, xx * (yy - xx @ b)[:, None]); inv = np.linalg.pinv(xx.T @ xx)
    V = inv @ (S.T @ S) @ inv * (G / (G - 1)) * ((n - 1) / (n - p)); se = np.sqrt(np.maximum(0, np.diag(V)))
    crit = t.ppf(.975, G - 1)
    return {'b': b, 'se': se, 'lo': b - crit * se, 'hi': b + crit * se, 'p': 2 * t.sf(np.abs(b / se), G - 1)}


def tidy(name, columns, f, odds=True):
    rows = []
    for i, term in enumerate(columns):
        r = {'model': name, 'term': term, 'beta': float(f['b'][i]), 'se': float(f['se'][i]),
             'ci_low': float(f['lo'][i]), 'ci_high': float(f['hi'][i]), 'p': float(f['p'][i])}
        if odds: r.update(OR=float(np.exp(f['b'][i])), OR_low=float(np.exp(f['lo'][i])), OR_high=float(np.exp(f['hi'][i])))
        rows.append(r)
    return rows
