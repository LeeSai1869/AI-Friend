import sqlite3

from section_5_domains.languages.lexicon import candidate_words, lookup


def make_db(path):
    con = sqlite3.connect(path)
    con.execute("create table records (word text, part_of_speech text, definition text)")
    con.execute("create table gloss_fill (word text, part_of_speech text, definition text, source text)")
    con.execute("create table function_words (word text, class text, grp text)")
    con.executemany("insert into records values (?, ?, ?)", [
        ("Hello", "interjection", "A greeting."), ("hello", "noun", "An act of greeting."),
        ("run", "verb", "To move quickly on foot."),
    ])
    con.execute("insert into gloss_fill values ('touch', 'noun', 'the event of contact', 'wordnet via nltk')")
    con.execute("insert into function_words values ('is', 'verb', 'be')")
    con.commit()
    con.close()


def test_lookup_orders_sources_and_names_them(tmp_path):
    db = tmp_path / "lexicon.sqlite"
    make_db(db)
    result = lookup(["hello", "touch", "is", "zzzz"], db)
    assert {s["source"] for s in result["hello"]["senses"]} == {"wiktionary-based dictionary file"}
    assert len(result["hello"]["senses"]) == 2
    assert result["touch"]["senses"][0]["source"] == "wordnet via nltk"
    assert result["is"]["found"] and result["is"]["function_word"][0]["group"] == "be"
    assert result["zzzz"] == {"found": False, "function_word": [], "senses": []}


def test_lookup_is_read_only(tmp_path):
    db = tmp_path / "lexicon.sqlite"
    make_db(db)
    lookup(["hello"], db)
    con = sqlite3.connect(db)
    assert con.execute("select count(*) from records").fetchone()[0] == 3


def test_candidate_words_prefer_quotes_and_drop_noise():
    assert candidate_words('What does "serendipity" mean?') == ["serendipity"]
    assert candidate_words("What does serendipity mean?") == ["serendipity"]
    assert candidate_words("Provide your evidence for this request: define look") == ["look"]
    assert candidate_words("") == []


def test_single_word_subject_is_used_even_when_it_is_a_stop_word():
    assert candidate_words("is", "what does is mean") == ["is"]
    assert candidate_words("look", "Provide your evidence for this request: what does look mean?") == ["look"]
    assert candidate_words("lookup_word", "what does serendipity mean") == ["serendipity"]
