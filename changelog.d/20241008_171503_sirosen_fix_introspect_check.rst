Features
--------

- The token introspect checking and caching performed in ``AuthState`` has
  been improved.

  - The cache is keyed off of token hashes, rather than raw token strings.

  - The ``exp`` and ``nbf`` values are no longer verified, removing the
    possibility of incorrect treatment of valid tokens as invalid due to clock
    drift.

  - Introspect response caching caches the raw response even for invalid
    tokens, meaning that Action Providers will no longer repeatedly introspect
    a token once it is known to be invalid.

  - Scope validation raises a new, dedicated error class,
    ``globus_action_provider_tools.authentication.InvalidTokenScopesError``, on
    failure.
