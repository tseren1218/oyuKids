import pytest

from app.services.scoring import align, normalize, score_poem, score_reading, score_words


def test_normalize_strips_punctuation_and_case():
    assert normalize("«Хавар,") == "хавар"
    assert normalize("—") == ""


def test_perfect_reading():
    text = "Тэмээ бол говийн хөлөг юм."
    result = score_reading(text, "тэмээ бол говийн хөлөг юм", duration_seconds=6)
    assert result.accuracy == 1.0
    assert result.wpm == 50.0
    assert result.stars == 3


def test_reading_marks_missed_wrong_and_close_words():
    alignment = align("Нар гэрэлтэж шувууд жиргэж байв", "нар гэрэлтэ нохой жиргэж")
    statuses = [t.status for t in alignment.tokens]
    assert statuses == ["correct", "close", "wrong", "correct", "missed"]
    assert alignment.correct == 3


def test_extra_words_do_not_count_against_accuracy():
    alignment = align("аав ээж", "аан аав ээж")
    assert alignment.accuracy == 1.0
    assert alignment.extra_words == 1


def test_poem_keeps_line_structure():
    result = score_poem("Өглөө нар мандлаа\nӨнгө бүхэн гэрэллээ", "өглөө нар мандлаа")
    (first, acc1), (second, acc2) = result.lines
    assert acc1 == 1.0 and acc2 == 0.0


def test_word_recall_statuses_and_order():
    result = score_words(["ном дэвтэр", "аав ээж", "уул ус"], "аав ээж ном дэвтэр ус")
    assert [i.status for i in result.items] == ["recalled", "recalled", "partial"]
    assert result.in_order == 1  # said in swapped order
    assert result.score == pytest.approx(2.5 / 3)


def test_word_recall_in_order():
    result = score_words(["ах дүү", "ой мод"], "ах дүү ой мод")
    assert result.perfect_order and result.stars == 3
