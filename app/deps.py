from functools import lru_cache

from app.config import get_settings
from app.db.base import Repository
from app.db.memory import MemoryRepository
from app.services.storage import AudioStore, build_audio_store
from app.services.stt import STTProvider, build_stt


@lru_cache
def get_repo() -> Repository:
    settings = get_settings()
    if settings.db_backend == "singlestore":
        from app.db.singlestore import SingleStoreRepository

        return SingleStoreRepository(settings.singlestore_url)
    return MemoryRepository()


@lru_cache
def get_stt() -> STTProvider:
    return build_stt(get_settings())


@lru_cache
def get_audio_store() -> AudioStore:
    return build_audio_store(get_settings())
