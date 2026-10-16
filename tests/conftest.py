import os

# Tests never touch real services, whatever .env says.
os.environ["OYU_STT_PROVIDER"] = "mock"
os.environ["OYU_DB_BACKEND"] = "memory"
os.environ["S3_BUCKET_NAME"] = ""  # → NullAudioStore; tests never upload

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.deps import get_audio_store, get_repo, get_stt  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_state():
    for cached in (get_settings, get_repo, get_stt, get_audio_store):
        cached.cache_clear()
    yield


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _login(client: TestClient, username: str, role: str) -> TestClient:
    client.cookies.clear()
    res = client.post("/login", data={"username": username, "role": role}, follow_redirects=False)
    assert res.status_code == 303, res.text
    return client


@pytest.fixture
def student(client) -> TestClient:
    return _login(client, "nomin", "student")


@pytest.fixture
def teacher(client) -> TestClient:
    return _login(client, "sarnai", "teacher")


@pytest.fixture
def login(client):
    return lambda username, role: _login(client, username, role)
