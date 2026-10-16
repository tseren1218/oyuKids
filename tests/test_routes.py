import re

import pytest


@pytest.mark.parametrize("path", ["/", "/reading", "/reading/1", "/words", "/poems", "/poems/3", "/progress", "/classes", "/soon/math"])
def test_student_pages_render(student, path):
    res = student.get(path)
    assert res.status_code == 200
    assert "oyu<b>Kids</b>" in res.text


def test_reading_category_fragment(student):
    res = student.get("/reading?category=quote", headers={"HX-Request": "true", "HX-Target": "passage-list"})
    assert res.status_code == 200
    assert res.text.lstrip().startswith('<div id="passage-list">')
    assert "Ардын мэргэн үгс" in res.text and "Говийн хөлөг" not in res.text


def test_reading_attempt_with_mock_stt(student):
    res = student.post("/reading/1/attempts", data={"duration_ms": "30000"}, files={"audio": ("a.webm", b"", "audio/webm")})
    assert res.status_code == 200
    assert "үг/мин" in res.text and "tok--correct" in res.text


def test_words_round_flow(student):
    flash = student.post("/words/rounds", data={"level": "medium"})
    assert flash.status_code == 200
    round_id = re.search(r"/words/rounds/(\w+)/recall", flash.text).group(1)
    assert flash.text.count('class="word-card word-card--') == 5

    assert student.get(f"/words/rounds/{round_id}/recall").status_code == 200
    result = student.post(f"/words/rounds/{round_id}/attempts", data={"duration_ms": "8000"})
    assert result.status_code == 200 and "Санасан" in result.text


def test_word_rounds_are_private(student, login):
    flash = student.post("/words/rounds", data={"level": "easy"})
    round_id = re.search(r"/words/rounds/(\w+)/recall", flash.text).group(1)
    other = login("anujin", "student")
    assert other.get(f"/words/rounds/{round_id}/recall").status_code == 404


def test_poem_practice_and_recite(student):
    practice = student.get("/poems/1/practice?level=3")
    assert practice.text.count('class="mask"') == 12  # every word hidden at level 3
    assert student.get("/poems/1/recite").status_code == 200
    result = student.post("/poems/1/attempts", data={"duration_ms": "9000"})
    assert result.status_code == 200 and "line-score" in result.text


def test_unknown_items_404(student):
    assert student.get("/reading/999").status_code == 404
    assert student.get("/soon/nope").status_code == 404
