"""Run analysis, verified pilot-code join, and report-table generation."""
from pathlib import Path
import argparse
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--out', type=Path, default=Path('results'))
    parser.add_argument('--bootstrap', type=int, default=500)
    parser.add_argument('--seed', type=int, default=20261009)
    parser.add_argument('--skip-pilot-codes', action='store_true', help='For a changed source: do not reuse original qualitative codes')
    args = parser.parse_args()
    source, out = args.input.resolve(), args.out.resolve()
    if not source.is_file():
        parser.error(f'Workbook not found: {source}. See README.md for download instructions.')
    if args.bootstrap < 20:
        parser.error('--bootstrap must be at least 20')
    out.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    for key in ['OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS']:
        env[key] = '1'
    steps = [('quantitative', [sys.executable, str(ROOT / 'analyze.py'), '--input', str(source), '--out', str(out), '--bootstrap', str(args.bootstrap), '--seed', str(args.seed)])]
    if not args.skip_pilot_codes:
        steps.append(('qualitative', [sys.executable, str(ROOT / 'join_qualitative.py'), '--out', str(out)]))
    else:
        old = out / 'qualitative_audit.csv'
        if old.exists():
            old.unlink()
    steps.append(('tables', [sys.executable, str(ROOT / 'make_tables.py'), '--out', str(out)]))
    for name, command in steps:
        print(f'Running {name} ...', flush=True)
        with (out / f'{name}.log').open('w', encoding='utf-8') as log:
            done = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, env=env)
        if done.returncode:
            print(f'Failed: see {out / (name + ".log")}. No completed-run claim is made.', file=sys.stderr)
            return done.returncode
    print(f'Complete. Read {out / "tables.md"} and {out / "audit.json"}.')
    print('Generated raw comments and intermediate data are local-only and excluded by .gitignore.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
