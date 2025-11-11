from __future__ import annotations

import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Generic, Optional, TypeVar

T = TypeVar("T")


@dataclass
class CacheEntry(Generic[T]):
    value: T
    expires_at: float


class IdempotencyCache(Generic[T]):
    """A simple thread-safe TTL-based LRU cache for idempotent responses."""

    def __init__(self, ttl_seconds: int, max_size: int):
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        if max_size <= 0:
            raise ValueError("max_size must be positive")
        self._ttl = ttl_seconds
        self._max_size = max_size
        self._lock = threading.Lock()
        self._entries: OrderedDict[str, CacheEntry[T]] = OrderedDict()

    def _purge_expired(self) -> None:
        now = time.monotonic()
        keys_to_delete = [key for key, entry in self._entries.items() if entry.expires_at <= now]
        for key in keys_to_delete:
            del self._entries[key]

    def get(self, key: str) -> Optional[T]:
        with self._lock:
            self._purge_expired()
            entry = self._entries.get(key)
            if not entry:
                return None
            # Move to end to mark as recently used
            self._entries.move_to_end(key)
            return entry.value

    def set(self, key: str, value: T) -> None:
        with self._lock:
            self._purge_expired()
            if key in self._entries:
                self._entries.move_to_end(key)
            self._entries[key] = CacheEntry(value=value, expires_at=time.monotonic() + self._ttl)
            while len(self._entries) > self._max_size:
                self._entries.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def __len__(self) -> int:  # pragma: no cover - simple passthrough
        with self._lock:
            self._purge_expired()
            return len(self._entries)


__all__ = ["IdempotencyCache"]


