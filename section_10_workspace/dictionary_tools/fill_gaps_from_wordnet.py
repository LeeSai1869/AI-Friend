"""Add WordNet glosses for words the dictionary index lacks, in a separate table with a source column."""
import argparse
import sqlite3

from nltk.corpus import wordnet

POS = {"n": "noun", "v": "verb", "a": "adjective", "s": "adjective", "r": "adverb"}
SOURCE = "wordnet via nltk"
BATCH = 5000


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", required=True, help="SQLite file built by build_dictionary_index.py")
    args = parser.parse_args()

    con = sqlite3.connect(args.index)
    known = {row[0].lower() for row in con.execute("select distinct word from records")}
    con.execute("DROP TABLE IF EXISTS gloss_fill")
    con.execute("CREATE TABLE gloss_fill (word TEXT, part_of_speech TEXT, definition TEXT, source TEXT)")

    sql = "INSERT INTO gloss_fill (word, part_of_speech, definition, source) VALUES (?, ?, ?, ?)"
    batch, words, rows = [], set(), 0
    for name in wordnet.all_lemma_names():
        word = name.replace("_", " ")
        if word.lower() in known:
            continue
        for synset in wordnet.synsets(name):
            batch.append((word, POS[synset.pos()], synset.definition(), SOURCE))
            words.add(word)
            if len(batch) >= BATCH:
                con.executemany(sql, batch)
                rows += len(batch)
                batch = []
    if batch:
        con.executemany(sql, batch)
        rows += len(batch)
    con.execute("CREATE INDEX idx_gloss_word ON gloss_fill(lower(word))")
    con.commit()
    con.close()
    print(f"gap words added: {len(words)} | gloss rows: {rows}")


if __name__ == "__main__":
    main()
