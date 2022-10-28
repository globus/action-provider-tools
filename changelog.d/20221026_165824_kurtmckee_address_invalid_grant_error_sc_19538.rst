Bugfixes
--------

- Fix a crash that occurs when an HTTP 400 "invalid grant" error is received
  from Globus Auth while getting an authorizer for a given scope.

  This is now caught by ``AuthState.get_authorizer_for_scope()`` and ``None`` is returned.
