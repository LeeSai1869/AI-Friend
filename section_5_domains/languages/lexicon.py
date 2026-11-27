"""Read-only word lookup in the English lexicon built by build_lexicon.py.

Order of sources: Wiktionary-based records, then the closed-class word table,
then WordNet glosses, used only where the records have nothing. Every sense names its source.
"""
import os
import re
import sqlite3
from pathlib import Path

MAX_WORDS = 6
MAX_SENSES = 4
MAX_CHARS = 300
STOP = frozenset(
    "a an the of in on to for and or is are was were be been it its this that these those "
    "what does do did mean means meaning meant define definition word words please tell me "
    "you your can could would about with from as at by how why when where which who whom "
    "provide evidence request objective relevant trusted capability lookup unresolved "
    "information user users".split()
)


def lexicon_path():
    state = os.environ.get("AI_FRIEND_STATE_DIR")
    return Path(state).expanduser() / "lexicon" / "english.sqlite" if state else None


def candidate_words(*texts):
    """Quoted terms first, then a single-word subject, then content words without stop-words."""
    joined = " ".join(str(t or "") for t in texts)
    quoted = [q.strip().lower() for q in re.findall(r"[\"\u201c`]([A-Za-z][A-Za-z' -]{0,40})[\"\u201d`]", joined)]
    subject = str(texts[0] or "").strip() if texts else ""
    if quoted:
        words = quoted
    elif re.fullmatch(r"[A-Za-z][A-Za-z'-]*", subject):
        words = [subject.lower()]
    else:
        words = [w.lower().strip("'-") for w in re.findall(r"[A-Za-z][A-Za-z'-]*", joined)
                 if w.lower().strip("'-") not in STOP]
    seen, out = set(), []
    for word in words:
        if word and word not in seen:
            seen.add(word)
            out.append(word)
    return out[:MAX_WORDS]


def _clip(text):
    text = " ".join(str(text or "").split())
    return text if len(text) <= MAX_CHARS else text[: MAX_CHARS - 1] + "\u2026"


def lookup(words, db_path):
    con = sqlite3.connect(Path(db_path).as_uri() + "?mode=ro", uri=True)
    try:
        result = {}
        for word in words:
            senses = [
                {"part_of_speech": pos, "definition": _clip(definition), "source": "wiktionary-based dictionary file"}
                for pos, definition in con.execute(
                    "select part_of_speech, definition from records where lower(word) = ? limit ?", (word, MAX_SENSES))
            ]
            if not senses:
                senses = [
                    {"part_of_speech": pos, "definition": _clip(definition), "source": source}
                    for pos, definition, source in con.execute(
                        "select part_of_speech, definition, source from gloss_fill where lower(word) = ? limit ?",
                        (word, MAX_SENSES))
                ]
            function = [
                {"class": cls, "group": grp}
                for cls, grp in con.execute("select class, grp from function_words where word = ?", (word,))
            ]
            result[word] = {"found": bool(senses or function), "function_word": function, "senses": senses}
        return result
    finally:
        con.close()
