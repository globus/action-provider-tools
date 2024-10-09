Development
-----------

- Refactor ``AuthState.get_authorizer_for_scope`` without changing its
  primary outward semantics. The ``bypass_dependent_token_cache`` argument
  has been removed from its interface, as it is not necessary to expose
  with the improved implementation.
