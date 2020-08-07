Caching
=======

To avoid excessively taxing Globus Auth, the ``AuthState`` will, by default,
cache identities and group memberships for 30 seconds. Action Provider Tools
include caching based on the `dogpile.cache
library <https://dogpilecache.sqlalchemy.org/en/latest/>`_. This is a fairly
mature library from the author of SQLAlchemy that offers a standardized
interface that can be used with a variety of different caching backends.


The cache is initialized when you first instantiate your ``TokenChecker()``.
You should only need to create one TokenChecker instance for your application,
and then you can re-use it to check each new token. In the event that you do
need more than one TokenChecker, be aware that all TokenChecker instances in an
app share the same underlying cache.

By default, the Action Provider Tools `authentication.TokenChecker()` will use a
basic in-memory cache backend. However, if you are deploying your Action
Provider in an environment where something like *Redis* or *Memcached* is
available, you might want to configure one of those services to act as the
backend for your cache.

To customize the TokenChecker, supply a `cache_config` argument when
instantiating it, this `cache_config` will get passed on to the dogpile cache
backend. Each new instance of a TokenChecker with a custom configuration will
drop the cache and recreate it with the desired settings.  Since all
TokenCheckers share the same underlying cache, subsequent attempts to configure
the cache will overwrite the previous cache's settings and therefore only the
last applied configuration will persist.

.. code-block:: python

    from globus_action_provider_tools.authentication import TokenChecker

    # Create TokenChecker with default settings
    my_token_checker = TokenChecker(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        expected_scopes=EXPECTED_SCOPES,
    )

    # Creating a TokenChecker with a custom config will drop the previous cache and
    # create it with the new settings. Both TokenCheckers will use this new cache
    new_token_checker = TokenChecker(
            client_id=config["client_id"],
            client_secret=config["client_secret"],
            expected_scopes=config["expected_scopes"],
            cache_config={
                'backend': 'dogpile.cache.memcached',
                'timeout': 60,  # seconds, default: 30
                'url': "127.0.0.1:11211"
            }
        )


The `timeout` value sets how long (in seconds) identity and group membership
results are cached, and `backend` is a string that determines which caching
backend is used. The rest of the `cache_config` dictionary is passed through
unmodified to the specified backend. For details of the available backends and
their configuration options, or for help writing your own cache backend, refer
to `the Dogpile.cache
documentation.
<https://dogpilecache.sqlalchemy.org/en/latest/api.html#module-dogpile.cache.backends.memory>`_
