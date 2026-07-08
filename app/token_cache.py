import asyncio
import time
from dataclasses import dataclass

from app.config import settings


@dataclass
class CachedToken:
    token: str
    expires_at: float


class TokenCache:
    def __init__(self) -> None:
        self._tokens: dict[str, CachedToken] = {}
        self._lock = asyncio.Lock()

    @staticmethod
    def _key(host: str, database: str, username: str) -> str:
        return f"{host}|{database}|{username}"

    async def get(self, host: str, database: str, username: str) -> str | None:
        key = self._key(host, database, username)
        async with self._lock:
            entry = self._tokens.get(key)
            if entry is None or entry.expires_at <= time.monotonic():
                if entry is not None:
                    del self._tokens[key]
                return None
            return entry.token

    async def set(self, host: str, database: str, username: str, token: str) -> None:
        key = self._key(host, database, username)
        async with self._lock:
            self._tokens[key] = CachedToken(
                token=token,
                expires_at=time.monotonic() + settings.token_ttl_seconds,
            )

    async def invalidate(self, host: str, database: str, username: str) -> None:
        key = self._key(host, database, username)
        async with self._lock:
            self._tokens.pop(key, None)


token_cache = TokenCache()
