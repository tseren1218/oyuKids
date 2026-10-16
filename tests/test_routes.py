import re

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.mark.parametrize("path", ["/", "/reading", "/reading/1", "/words", "/poems", "/poems/3", "/progress", "/soon/math"])
def test_pages_render(path):
    res = client.get(path)
    assert res.status_code == 200
    assert "oyu<b>Kids</b>" in res.text


def test_reading_category_fragment():
    res = client.get("/reading?category=quote", headers={"HX-Request": "true", "HX-Target": "passage-list"})
    assert res.status_code == 200
    assert res.text.lstrip().startswith('<div id="passage-list">')
    assert "Ардын мэргэн үгс" in res.text and "Говийн хөлөг" not in res.text


def test_reading_attempt_with_mock_stt():
    res = client.post("/reading/1/attempts", data={"duration_ms": "30000"}, files={"audio": ("a.webm", b"", "audio/webm")})
    assert res.status_code == 200
    assert "үг/мин" in res.text and "tok--correct" in res.text


def test_words_round_flow():
    flash = client.post("/words/rounds", data={"level": "medium"})
    assert flash.status_code == 200
    round_id = re.search(r"/words/rounds/(\w+)/recall", flash.text).group(1)
    assert flash.text.count('class="word-card word-card--') == 5

    assert client.get(f"/words/rounds/{round_id}/recall").status_code == 200
    result = client.post(f"/words/rounds/{round_id}/attempts", data={"duration_ms": "8000"})
    assert result.status_code == 200 and "Санасан" in result.text


def test_poem_practice_and_recite():
    practice = client.get("/poems/1/practice?level=3")
    assert practice.text.count('class="mask"') == 12  # every word hidden at level 3
    assert client.get("/poems/1/recite").status_code == 200
    result = client.post("/poems/1/attempts", data={"duration_ms": "9000"})
    assert result.status_code == 200 and "line-score" in result.text


def test_unknown_items_404():
    assert client.get("/reading/999").status_code == 404
    assert client.get("/soon/nope").status_code == 404
