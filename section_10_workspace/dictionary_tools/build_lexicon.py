"""Build the single-file English lexicon: Wiktionary index, WordNet gap fill, closed-class table, provenance."""
import argparse
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUILDER_VERSION = "1"
NOTICE = """English lexicon notice

This file combines:
- Entries derived from a Wiktionary-based English dictionary file supplied by the Trainer.
  The source file states a CC BY-SA license. Keep this notice and the share-alike terms if you redistribute the index.
- Glosses from Princeton WordNet, accessed through nltk, stored in table gloss_fill with a source column.
  Keep Princeton's WordNet copyright notice and license if you redistribute.
- A closed-class word table written for AI Friend.

This notice is a reminder, not legal advice. Check each license before sharing.
"""


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def existing_meta(db):
    if not db.exists():
        return {}
    try:
        con = sqlite3.connect(db)
        try:
            return dict(con.execute("select key, value from meta"))
        finally:
            con.close()
    except sqlite3.Error:
        return {}


def run_step(args):
    result = subprocess.run([sys.executable, *args], capture_output=True, text=True)
    if result.returncode != 0:
        sys.stderr.write(result.stdout + result.stderr)
        raise SystemExit(f"build step failed: {args[0]}")
    return result.stdout.strip()


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, help="Wiktionary-based dictionary JSON")
    parser.add_argument("--state-dir", required=True, help="AI Friend state folder")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    source = Path(args.source)
    words_file = HERE / "function_words.json"
    out_dir = Path(args.state_dir) / "lexicon"
    final = out_dir / "english.sqlite"
    source_hash, words_hash = sha256_of(source), sha256_of(words_file)

    meta = existing_meta(final)
    if (not args.force and meta.get("source_sha256") == source_hash
            and meta.get("function_words_sha256") == words_hash
            and meta.get("builder_version") == BUILDER_VERSION):
        print("up to date", final)
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(suffix=".sqlite", dir=out_dir)
    os.close(fd)
    tmp = Path(tmp_name)
    done = False
    try:
        records = int(run_step([str(HERE / "build_dictionary_index.py"), "--source", str(source), "--output", str(tmp)]).splitlines()[-1])
        gloss_line = run_step([str(HERE / "fill_gaps_from_wordnet.py"), "--index", str(tmp)])

        entries = json.load(open(words_file, encoding="utf-8"))["entries"]
        con = sqlite3.connect(tmp)
        con.execute("CREATE INDEX idx_records_word ON records(lower(word))")
        con.execute("CREATE TABLE function_words (word TEXT, class TEXT, grp TEXT)")
        con.executemany("INSERT INTO function_words VALUES (?, ?, ?)", [(e["word"], e["class"], e["group"]) for e in entries])
        con.execute("CREATE INDEX idx_function_word ON function_words(word)")
        gloss_rows = con.execute("select count(*) from gloss_fill").fetchone()[0]
        try:
            from nltk.corpus import wordnet
            wordnet_version = wordnet.get_version()
        except Exception:
            wordnet_version = "unknown"
        con.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
        con.executemany("INSERT INTO meta VALUES (?, ?)", [
            ("source_sha256", source_hash), ("source_name", source.name),
            ("function_words_sha256", words_hash), ("builder_version", BUILDER_VERSION),
            ("built_at", datetime.now(timezone.utc).isoformat(timespec="seconds")),
            ("records", str(records)), ("gloss_rows", str(gloss_rows)),
            ("function_words", str(len(entries))), ("wordnet_version", str(wordnet_version)),
        ])
        con.commit()
        con.close()
        os.replace(tmp, final)
        done = True
    finally:
        if not done:
            tmp.unlink(missing_ok=True)
    (out_dir / "NOTICE.txt").write_text(NOTICE, encoding="utf-8")
    print(f"built {final} | records {records} | {gloss_line}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
