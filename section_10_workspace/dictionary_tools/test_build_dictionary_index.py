import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "build_dictionary_index.py"
FIXTURE = HERE / "fixtures" / "sample_dictionary.json"


def expected_definition_count():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return sum(
        len(meaning.get("definitions", []))
        for records in data.values()
        for record in records
        for meaning in record.get("meanings", [])
    )


class BuildDictionaryIndexTests(unittest.TestCase):
    def run_script(self, source, output):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--source", str(source), "--output", str(output)],
            capture_output=True,
            text=True,
            timeout=60,
        )

    def test_row_count_matches_fixture(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "out.sqlite"
            result = self.run_script(FIXTURE, output)
            self.assertEqual(result.returncode, 0, result.stderr)
            expected = expected_definition_count()
            self.assertEqual(result.stdout.strip(), str(expected))
            with sqlite3.connect(output) as con:
                rows = con.execute("select count(*) from records").fetchone()[0]
            self.assertEqual(rows, expected)

    def test_table_columns(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "out.sqlite"
            self.assertEqual(self.run_script(FIXTURE, output).returncode, 0)
            with sqlite3.connect(output) as con:
                columns = [row[1] for row in con.execute("pragma table_info(records)")]
            self.assertEqual(columns, ["word", "part_of_speech", "definition"])

    def test_known_row_is_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "out.sqlite"
            self.assertEqual(self.run_script(FIXTURE, output).returncode, 0)
            with sqlite3.connect(output) as con:
                row = con.execute(
                    "select part_of_speech from records where word = ?", ("'arf",)
                ).fetchone()
            self.assertEqual(row, ("noun",))

    def test_records_without_meanings_are_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "src.json"
            source.write_text(
                json.dumps({
                    "a": [{"word": "a"}],
                    "b": [{"word": "b", "meanings": [
                        {"partOfSpeech": "noun", "definitions": [{"definition": "d"}]}
                    ]}],
                }),
                encoding="utf-8",
            )
            output = Path(tmp) / "out.sqlite"
            result = self.run_script(source, output)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), "1")


if __name__ == "__main__":
    unittest.main()
