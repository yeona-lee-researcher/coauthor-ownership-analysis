"""Compare a rerun to the frozen reference outputs; not a test of scientific validity."""
from pathlib import Path
import argparse
import json
import numpy as np
import pandas as pd


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=Path('results'))
    parser.add_argument('--reference', type=Path, default=Path(__file__).resolve().parent / 'reference_results')
    args = parser.parse_args()
    actual = json.loads((args.out / 'audit.json').read_text())
    expected = json.loads((args.reference / 'audit.json').read_text())
    for key in ['joined_sessions','joined_workers','primary_sessions','primary_workers','primary_genres']:
        if actual[key] != expected[key]:
            raise ValueError(f'Cohort differs: {key}: {actual[key]} != {expected[key]}')
    keycols = ['model','term']
    got = pd.read_csv(args.out / 'model_results.csv').set_index(keycols).sort_index()
    ref = pd.read_csv(args.reference / 'model_results.csv').set_index(keycols).sort_index()
    if not got.index.equals(ref.index):
        raise ValueError('Model/parameter set differs from reference.')
    cols = ['beta','se','ci_low','ci_high','p','OR','OR_low','OR_high','p_holm_secondary']
    # |beta| > 10 on a logit scale signals (quasi-)separation, e.g. a prompt with no
    # ownership <= 3 in the O>3 model. Such nuisance coefficients are not identified and
    # drift across optimizer versions, so they are reported rather than compared.
    separated = (ref['beta'].abs() > 10) & ~ref.index.get_level_values('term').str.startswith('threshold_')
    if separated.any():
        print('Not identified (quasi-separation), excluded from comparison:')
        print(ref.loc[separated, ['beta']].to_string())
    got, ref = got[~separated], ref[~separated]
    if not np.allclose(got[cols], ref[cols], rtol=1e-5, atol=1e-6, equal_nan=True):
        raise ValueError('Model results differ. Inspect source version, software versions, and outputs before reusing the manuscript.')
    if actual['FE_cluster_bootstrap']['B'] != expected['FE_cluster_bootstrap']['B'] or actual['FE_cluster_bootstrap']['seed'] != expected['FE_cluster_bootstrap']['seed']:
        raise ValueError('Use the reference bootstrap count and seed for exact reproduction.')
    if not np.allclose(actual['FE_cluster_bootstrap']['percentile_CI'],expected['FE_cluster_bootstrap']['percentile_CI'],atol=1e-5,rtol=1e-5):
        raise ValueError('Bootstrap interval differs from reference.')
    print(f'PASS: cohort, all {len(got)} parameter rows, and bootstrap interval match numerical tolerances.')
    if actual['sha256'] != expected['sha256']:
        print('NOTE: workbook bytes differ; matching numerical outputs do not establish complete source identity.')
    print('This verifies reproduction, not causality, construct validity, or human validation of qualitative codes.')


if __name__ == '__main__':
    main()
