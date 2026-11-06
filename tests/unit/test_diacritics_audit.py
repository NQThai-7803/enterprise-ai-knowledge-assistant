from __future__ import annotations

from scripts.diagnostics import diacritics_audit as audit

SOURCE = """
def fold_text(value):
    return value

def is_money(value):
    \"\"\"dong in a docstring is not a cue.\"\"\"
    return "dong" in fold_text(value) or "http" in value
"""


def test_common_forms_all_fold_to_their_key() -> None:
    for folded, words in audit.COMMON_FORMS.items():
        assert {audit.fold(word) for word in words} == {folded}


def test_a_folded_word_with_two_readings_is_a_collision() -> None:
    cues = audit.cues_in(SOURCE, "x.py", audit.vocabulary(()))
    assert [(cue.text, cue.single_word) for cue in cues] == [("dong", True)]
    assert "đồng" in dict(cues[0].collisions)["dong"]


def test_a_module_that_does_not_fold_has_no_cues() -> None:
    assert audit.cues_in('x = "dong"\n', "x.py", audit.vocabulary(())) == []


def test_regex_escapes_do_not_glue_to_words() -> None:
    assert audit.cue_words(r"\bbao nhieu\b") == ["bao", "nhieu"]


def test_vocabulary_learns_forms_from_text() -> None:
    assert "xoài" in audit.vocabulary(["Quả Xoài"])["xoai"]
