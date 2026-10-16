from functools import lru_cache

from app.config import get_settings
from app.db.base import Repository
from app.db.memory import MemoryRepository
from app.services.stt import STTProvider, build_stt

# No auth yet: every request acts as this kid.
DEMO_KID_ID = 1


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
