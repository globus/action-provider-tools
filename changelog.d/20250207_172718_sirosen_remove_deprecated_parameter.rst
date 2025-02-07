Breaking changes
----------------

*   The ``required_authorizer_expiration_time`` parameter for
    ``AuthState.get_authorizer_for_scope`` has been removed. In recent
    releases it had no effect and emitted deprecation warnings.
