from __future__ import annotations

import datetime
import typing as t

import cachetools

T = t.TypeVar("T")


class TypedTTLCache(t.Generic[T]):
    """
    A tiny wrapper class which provides a type-checked layer on top of TTLCache.
    This allows us to know and enforce the types of cached objects.
    """

    def __init__(self, *, maxsize: int, ttl: int) -> None:
        self._cache: cachetools.TTLCache = cachetools.TTLCache(maxsize=maxsize, ttl=ttl)

    def get(self, key: str) -> T | None:
        return self._cache.get(key)

    def __setitem__(self, key: str, value: T) -> None:
        self._cache[key] = value

    def __delitem__(self, key: str) -> None:
        del self._cache[key]

    def __getitem__(self, key: str) -> T:
        return self._cache[key]  # type: ignore[no-any-return]

    def __contains__(self, key: str) -> bool:
        return key in self._cache

    def clear(self) -> None:
        self._cache.clear()


def now_isoformat():
    return str(datetime.datetime.now(datetime.timezone.utc).isoformat())


uuid_regex = (
    "([a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12})"
)
principal_urn_regex = f"^urn:globus:(auth:identity|groups:id):{uuid_regex}$"
