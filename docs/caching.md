# Caching in Action Provider Tools

Probably you won't have to think about this, but just in case you do, here it is.

To avoid hitting Globus Auth with zillions of requests, the authentication bits of the Action Provider Tools include caching based on the [dogpile.cache library](https://dogpilecache.sqlalchemy.org/en/latest/). This is a fairly mature library from the author of SQLAlchemy that offers a standardized interface that can be used with a variety of different caching backends.

By default, the Action Provider Tools `authentication.TokenChecker()` will use a basic in-memory cache backend. However, if you are deploying your Action Provider service in an environment where something like Redis or Memcached is available, you might want to configure one of those services to act as the backend for your cache.

To do this, pass a dictionary containing configuration values as the `cache_config` argument when instantiating your `TokenChecker`. For example, to use the memcached backend, you could do:

```python
from globus_action_provider_tools.authentication import TokenChecker
checker = TokenChecker(
    'client_id', 'secret', ['https://auth.globus.org/scopes/example'], 'audience',
    cache_config={
        'backend': 'dogpile.cache.memcached',
        'timeout': 60,  # seconds, default: 30
        'url': "127.0.0.1:11211"
    }
)
```

The `timeout` value sets how long (in seconds) identity and group membership results are cached, and `backend` is a string that determines which caching backend is used. The rest of the `cache_config` dictionary is passed through unmodified to the specified backend. For details of the available backends and their configuration options, or for help writing your own cache backend, refer to [the Dogpile.cache documentation.](https://dogpilecache.sqlalchemy.org/en/latest/api.html#module-dogpile.cache.backends.memory)
