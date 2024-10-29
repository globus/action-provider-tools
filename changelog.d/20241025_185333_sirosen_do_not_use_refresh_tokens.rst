Bugfixes
--------

- Action Provider Tools no longer requests Dependent Refresh Tokens in
  contexts where Access Tokens are sufficient. As a result of this fix, the
  AuthState dependent token cache will never contain dependent refresh tokens.

Deprecations
------------

- The ``required_authorizer_expiration_time`` parameter to
  ``get_authorizer_for_scope`` is deprecated. Given token expiration and
  caching lifetimes, it was not possible for this parameter to have any effect
  based on its prior documented usage.
