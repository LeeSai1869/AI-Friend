import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "build_lexicon.py"
FIXTURE = HERE / "fixtures" / "sample_dictionary.json"

try:
    from nltk.corpus import wordnet
    wordnet.synsets("dog")
    HAVE_WORDNET = True
except Exception:
    HAVE_WORDNET = False


@unittest.skipUnless(HAVE_WORDNET, "WordNet data is not installed")
class BuildLexiconTests(unittest.TestCase):
    def build(self, state):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--source", str(FIXTURE), "--state-dir", str(state)],
            capture_output=True, text=True, timeout=900,
        )

    def test_builds_all_tables_with_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.build(tmp)
            self.assertEqual(result.returncode, 0, result.stderr)
            db = Path(tmp) / "lexicon" / "english.sqlite"
            con = sqlite3.connect(db)
            tables = {row[0] for row in con.execute("select name from sqlite_master where type = 'table'")}
            self.assertTrue({"records", "gloss_fill", "function_words", "meta"} <= tables)
            meta = dict(con.execute("select key, value from meta"))
            self.assertEqual(len(meta["source_sha256"]), 64)
            self.assertEqual(int(meta["records"]), 28)
            self.assertGreater(int(meta["gloss_rows"]), 1000)
            self.assertEqual(con.execute("select count(*) from function_words where word = 'is'").fetchone()[0], 1)
            self.assertTrue((Path(tmp) / "lexicon" / "NOTICE.txt").exists())

    def test_second_run_is_up_to_date(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(self.build(tmp).returncode, 0)
            again = self.build(tmp)
            self.assertEqual(again.returncode, 0, again.stderr)
            self.assertIn("up to date", again.stdout)


if __name__ == "__main__":
    unittest.main()
