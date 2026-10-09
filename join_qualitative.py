"""Attach fixed pilot interpretations only to verified source cases.

This does not generate interpretations. Human review remains pending.
"""
from pathlib import Path
import argparse
import hashlib
import json
import pandas as pd

ROOT = Path(__file__).resolve().parent
FIELDS = ['session_id', 'genre', 'understanding', 'ownership', 'written_by_human', 'ideation']


def text_digest(row):
    values = [str(row.get(c, '')) if pd.notna(row.get(c, '')) else '' for c in ['improve', 'comment']]
    return hashlib.sha256(json.dumps(values, ensure_ascii=False).encode('utf-8')).hexdigest()


def validate_cases(sample, manifest):
    if sample.case_id.duplicated().any() or manifest.case_id.duplicated().any():
        raise ValueError('Duplicate case IDs; inspect the selection before attaching codes.')
    if set(sample.case_id) != set(manifest.case_id):
        raise ValueError('Case selection changed. Re-read and recode the new cases.')
    got = sample.set_index('case_id').sort_index()
    expected = manifest.set_index('case_id').sort_index()
    for field in FIELDS:
        if field in ['session_id', 'genre']:
            equal = got[field].astype(str).equals(expected[field].astype(str))
        else:
            equal = (pd.to_numeric(got[field]) == pd.to_numeric(expected[field])).all()
        if not equal:
            raise ValueError(f'Case identity/ratings changed ({field}); old pilot codes cannot be attached.')
    if not got.apply(text_digest, axis=1).equals(expected['text_sha256']):
        raise ValueError('Source comments changed. Re-read and recode before attaching interpretations.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT / 'results')
    parser.add_argument('--codes', type=Path, default=ROOT / 'qualitative_codes.tsv')
    parser.add_argument('--manifest', type=Path, default=ROOT / 'qualitative_manifest.csv')
    args = parser.parse_args()
    sample = pd.read_csv(args.out / 'qualitative_sample.csv')
    manifest = pd.read_csv(args.manifest)
    codes = pd.read_csv(args.codes, sep='\t')
    validate_cases(sample, manifest)
    if set(sample.case_id) != set(codes.case_id):
        raise ValueError('Codebook cases differ from selected cases.')
    result = sample.drop(columns=['improve', 'comment']).merge(codes, on='case_id', validate='one_to_one')
    result.to_csv(args.out / 'qualitative_audit.csv', index=False)
    print(f'Validated and attached pilot codes to {len(result)} cases; human review remains pending.')


if __name__ == '__main__':
    main()
