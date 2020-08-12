from hashlib import sha256

from dogpile.cache import make_region

# How long can we keep the result of lookups without re-loading
DEFAULT_CACHE_TIMEOUT = 30  # seconds
DEFAULT_CACHE_BACKEND = "dogpile.cache.memory"


def key_generator(namespace, fn):
    """
    Based directly on dogpile.cache.util.function_key_generator, but modified
    to not omit 'self' so that different instances of AuthState will get cached
    separately -- this is important so that each bearer_token gets its own
    cache entry!
    """
    if namespace is None:
        namespace = "%s:%s" % (fn.__module__, fn.__name__)
    else:
        namespace = "%s:%s|%s" % (fn.__module__, fn.__name__, namespace)

    def generate_key(*args, **kw):
        if kw:
            raise ValueError(
                "dogpile.cache's default key creation "
                "function does not accept keyword arguments."
            )
        key = namespace + "|" + " ".join(map(str, args))
        return key

    return generate_key


dogpile_cache = make_region(
    # sha256 mangler so we don't keep any cleartext tokens in cache key
    key_mangler=lambda key: sha256(key.encode("utf-8")).hexdigest(),
    function_key_generator=key_generator,
)

dogpile_cache.configure(
    backend=DEFAULT_CACHE_BACKEND,
    expiration_time=DEFAULT_CACHE_TIMEOUT,
    replace_existing_backend=False,
)
