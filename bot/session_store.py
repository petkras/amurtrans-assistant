"""Session storage adapters for the Telegram request flow."""

from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from bot.logic import SESSION_TTL_SECONDS


class SessionStoreUnavailable(RuntimeError):
    """Raised when the configured durable session store cannot be reached."""


class UpstashSessionStore:
    """Small synchronous Redis REST adapter; no third-party package required."""

    def __init__(self, url: str, token: str, timeout: float = 4.0):
        self.url = url.rstrip("/")
        self.token = token
        self.timeout = timeout

    @classmethod
    def from_env(cls) -> UpstashSessionStore | None:
        url = os.getenv("KV_REST_API_URL") or os.getenv("UPSTASH_REDIS_REST_URL")
        token = os.getenv("KV_REST_API_TOKEN") or os.getenv("UPSTASH_REDIS_REST_TOKEN")
        if not url and not token:
            return None
        if not url or not token or not url.startswith("https://"):
            raise SessionStoreUnavailable("Redis REST configuration is incomplete or insecure")
        return cls(url, token)

    def _request(self, method: str, path: str, body: bytes | None = None) -> object:
        request = Request(
            self.url + path,
            data=body,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
            method=method,
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as error:
            raise SessionStoreUnavailable("Redis REST request failed") from error
        if "error" in payload:
            raise SessionStoreUnavailable("Redis REST returned an error")
        return payload.get("result")

    @staticmethod
    def _key(chat_id: int) -> str:
        return "amurtrans:session:" + quote(str(chat_id), safe="")

    def get(self, chat_id: int) -> dict | None:
        result = self._request("GET", "/get/" + self._key(chat_id))
        if result is None:
            return None
        try:
            value = json.loads(result) if isinstance(result, str) else result
        except (TypeError, ValueError) as error:
            raise SessionStoreUnavailable("Redis session contains invalid data") from error
        return value if isinstance(value, dict) else None

    def __setitem__(self, chat_id: int, session: dict) -> None:
        path = "/set/" + self._key(chat_id) + "?EX=" + str(SESSION_TTL_SECONDS)
        body = json.dumps(session, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self._request("POST", path, body)

    def pop(self, chat_id: int, default: object = None) -> dict | object:
        result = self._request("GET", "/del/" + self._key(chat_id))
        return default if result == 0 else None


def session_store_from_env(memory_store: dict[int, dict]):
    """Use durable Redis when configured, otherwise retain the local dev store."""
    return UpstashSessionStore.from_env() or memory_store
