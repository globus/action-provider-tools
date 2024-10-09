import datetime
import typing as t

import cachetools

T = t.TypeVar("T")


class TypedTTLCache(t.Generic[T]):
    def __init__(self, *, maxsize: int, ttl: int) -> None:
        self._cache: cachetools.TTLCache = cachetools.TTLCache(maxsize=maxsize, ttl=ttl)

    def get(self, key: str) -> T | None:
        return self._cache.get(key)

    def __setitem__(self, key: str, value: T) -> None:
        self._cache[key] = value


def now_isoformat():
    return str(datetime.datetime.now(datetime.timezone.utc).isoformat())


uuid_regex = (
    "([a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12})"
)
principal_urn_regex = f"^urn:globus:(auth:identity|groups:id):{uuid_regex}$"
