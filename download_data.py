"""Download the public CoAuthor workbook; never accepts credentials."""
from pathlib import Path
import argparse
import hashlib
import io
import urllib.request
import zipfile

URL = 'https://docs.google.com/spreadsheets/d/1O3EXJm52TQHfFSbzVGZmNIzzdu5ow6IjnOBrGTUY02o/export?format=xlsx'
EXPECTED = 'bb850549c91ca5d7b34f20b59833f61f0f362b817b91fe333d08b270c25647c4'


def validate_xlsx(blob):
    if not zipfile.is_zipfile(io.BytesIO(blob)):
        raise ValueError('The response is not XLSX. Open the source sheet and use File > Download > Microsoft Excel.')
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        if 'xl/workbook.xml' not in archive.namelist():
            raise ValueError('Downloaded ZIP is not an Excel workbook.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('data/raw/coauthor_metadata.xlsx'))
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output already exists. Reuse it or choose a different --output; no overwrite performed.')
    try:
        request = urllib.request.Request(URL, headers={'User-Agent': 'CoAuthor-reanalysis/0.2'})
        with urllib.request.urlopen(request, timeout=60) as response:
            blob = response.read(20 * 1024 * 1024 + 1)
        if len(blob) > 20 * 1024 * 1024:
            raise ValueError('Unexpected workbook size (over 20 MiB).')
        validate_xlsx(blob)
    except Exception as exc:
        parser.exit(1, f'Download failed: {exc}\nSource: {URL}\n')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('xb') as handle:
        handle.write(blob)
    digest = hashlib.sha256(blob).hexdigest()
    print(f'Saved {args.output}\nSHA-256: {digest}')
    if digest != EXPECTED:
        print('Workbook bytes differ from the reference export. Inspect cohort/model outputs; qualitative cases are checked by identity, ratings, and comment hashes.')


if __name__ == '__main__':
    main()
