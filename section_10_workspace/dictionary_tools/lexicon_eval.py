"""Answer a WordNet sample from the dictionary index alone and report coverage."""
import argparse
import random
import sqlite3

from nltk.corpus import wordnet

POS = {"n": "noun", "v": "verb", "a": "adjective", "s": "adjective", "r": "adverb"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", required=True)
    parser.add_argument("--n", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    lemmas = sorted(name for name in wordnet.all_lemma_names()
                    if name.isalpha() and name.islower())
    sample = random.Random(args.seed).sample(lemmas, args.n)
    con = sqlite3.connect(args.index)

    found = pos_ok = 0
    misses = []
    for word in sample:
        wanted = {POS[s.pos()] for s in wordnet.synsets(word)}
        have = {row[0] for row in con.execute(
            "select distinct part_of_speech from records where word = ?", (word,))}
        if have:
            found += 1
            if wanted <= have:
                pos_ok += 1
            else:
                misses.append((word, "missing POS", sorted(wanted - have)))
        else:
            misses.append((word, "not in lexicon", sorted(wanted)))

    print(f"sample: {args.n} | found: {found} ({100 * found / args.n:.1f}%) "
          f"| all WordNet POS present: {pos_ok} ({100 * pos_ok / args.n:.1f}%)")
    for row in misses[:25]:
        print("  ", row)


if __name__ == "__main__":
    main()
