"""Figures for the process model and microsimulation (paper Figure 2).

Usage: python make_figures.py --results results --out paper
Palette: first three reference categorical slots (validated: CVD dE 9.2, normal dE 27.6);
the aqua slot is below 3:1 contrast, so every series also carries a marker shape / direct label.
"""
from pathlib import Path
import argparse, json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

BLUE, ORANGE, AQUA = '#2a78d6', '#eb6834', '#1baf7a'
INK, INK2, GRID = '#0b0b0b', '#52514e', '#e4e3df'
plt.rcParams.update({'font.size': 8.5, 'axes.edgecolor': INK2, 'axes.labelcolor': INK, 'xtick.color': INK2,
                     'ytick.color': INK2, 'axes.spines.top': False, 'axes.spines.right': False,
                     'figure.facecolor': '#fcfcfb', 'axes.facecolor': '#fcfcfb', 'savefig.facecolor': '#fcfcfb'})

ap = argparse.ArgumentParser(description=__doc__); ap.add_argument('--results', default='results', type=Path)
ap.add_argument('--out', default='paper', type=Path); A = ap.parse_args()
S = A.results / 'simulation'
obs = pd.read_csv(S / 'observed_sessions.csv', index_col=0)
sim = pd.read_csv(S / 'simulated_heldout_writers.csv')
rep = json.loads((S / 'simulation_report.json').read_text())

fig, (a, b) = plt.subplots(1, 2, figsize=(7.4, 3.0), gridspec_kw={'width_ratios': [1, 1.15]})

# (a) held-out writers: distribution of human share of inserted characters
bins = np.linspace(0, 100, 26)
a.hist(obs.human_share.dropna(), bins=bins, density=True, color=GRID, edgecolor='#fcfcfb', linewidth=1, label='Observed')
for m, c, lab in (('M1', BLUE, 'Population M1'), ('M1+S', ORANGE, 'M1 + session heterogeneity')):
    h, e = np.histogram(sim.loc[sim.model == m, 'human_share'].dropna(), bins=bins, density=True)
    a.step(e[:-1], h, where='post', color=c, linewidth=2, label=lab)
a.set_xlabel('Human share of inserted characters (%)'); a.set_ylabel('Density')
a.set_title('(a) Held-out writers (5-fold, by writer)', loc='left', fontsize=9, color=INK)
a.set_ylim(0, .058); a.legend(frameon=False, fontsize=7.5, loc='upper left', ncol=1); a.yaxis.grid(True, color=GRID, linewidth=.6); a.set_axisbelow(True)

# (b) later sessions of known writers: 90% predictive-interval coverage
labels = {'n_query': 'Request episodes', 'n_accept': 'Accepted', 'human_share': 'Human share', 'duration_min': 'Duration', 'first_query_min': 'First request'}
models = (('population', BLUE, 'o', 'Population'), ('writer', ORANGE, 's', 'Writer'), ('writer+stop+S', AQUA, '^', 'Writer + stopping + session'))
y = np.arange(len(labels))
for j, (m, c, mk, lab) in enumerate(models):
    cov = [rep['B_later_sessions']['checks'][m][k]['coverage90'] for k in labels]
    b.plot(cov, y + (j - 1) * .22, mk, color=c, markersize=6.5, markeredgecolor='#fcfcfb', markeredgewidth=1, label=lab)
b.axvline(.9, color=INK2, linestyle='--', linewidth=1); b.text(.9, -.62, ' nominal 0.90', color=INK2, fontsize=7.5, va='bottom')
b.set_yticks(y, list(labels.values())); b.set_ylim(len(labels) - .5, -.75); b.set_xlim(.45, 1.0)
b.set_xlabel('Observed sessions inside simulated 90% interval')
b.set_title('(b) Later sessions of known writers', loc='left', fontsize=9, color=INK)
b.legend(frameon=False, fontsize=7.5, loc='lower left'); b.xaxis.grid(True, color=GRID, linewidth=.6); b.set_axisbelow(True)
fig.tight_layout()
A.out.mkdir(exist_ok=True)
fig.savefig(A.out / 'fig_simulation.pdf'); fig.savefig(A.out / 'fig_simulation.png', dpi=200)
print('wrote', A.out / 'fig_simulation.pdf')
