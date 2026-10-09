"""Checks for errors that would attach interpretations to the wrong observations."""
from pathlib import Path
import io
import sys
import unittest
import zipfile
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from join_qualitative import FIELDS, text_digest, validate_cases
from download_data import validate_xlsx


class SourceGuards(unittest.TestCase):
    def setUp(self):
        self.sample = pd.DataFrame([dict(case_id='Q01', session_id='session-a', genre='creative', understanding=7, ownership=2, written_by_human=39, ideation=7, improve='suggestion', comment='comment')])
        self.manifest = self.sample[['case_id'] + FIELDS].copy()
        self.manifest['text_sha256'] = self.sample.apply(text_digest, axis=1)

    def test_unchanged_case_is_accepted(self):
        validate_cases(self.sample, self.manifest)

    def test_reassigned_case_id_is_rejected(self):
        self.sample.loc[0, 'session_id'] = 'different-session'
        with self.assertRaises(ValueError):
            validate_cases(self.sample, self.manifest)

    def test_edited_comment_is_rejected(self):
        self.sample.loc[0, 'comment'] = 'changed meaning'
        with self.assertRaises(ValueError):
            validate_cases(self.sample, self.manifest)

    def test_changed_rating_is_rejected(self):
        self.sample.loc[0, 'ownership'] = 7
        with self.assertRaises(ValueError):
            validate_cases(self.sample, self.manifest)

    def test_signin_html_is_not_saved_as_workbook(self):
        with self.assertRaises(ValueError):
            validate_xlsx(b'<html>Please sign in</html>')

    def test_unrelated_zip_is_not_a_workbook(self):
        data = io.BytesIO()
        with zipfile.ZipFile(data, 'w') as archive:
            archive.writestr('unrelated.txt', 'hello')
        with self.assertRaises(ValueError):
            validate_xlsx(data.getvalue())


if __name__ == '__main__':
    unittest.main()
