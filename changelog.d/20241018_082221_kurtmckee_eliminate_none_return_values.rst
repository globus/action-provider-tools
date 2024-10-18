Changes
-------

-   ``AuthState.introspect_token()`` will no longer return ``None`` if the token is not active.

    Instead, a new exception, ``InactiveTokenError``, will be raised.
    ``InactiveTokenError`` is a subclass of ``ValueError``.

    Existing code that calls ``AuthState.introspect_token()`` no longer returns ``None``, either,
    but will instead raise ``ValueError`` (or a subclass) or a ``globus_sdk.GlobusAPIError``:

    *   ``AuthState.get_authorizer_for_scope``
    *   ``AuthState.effective_identity``
    *   ``AuthState.identities``
