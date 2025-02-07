Breaking changes
----------------

*   The ``AuthState`` object now introspects its token when initialized. This
    results in more eager error behaviors, as a failed introspect will now
    raise an error immediately, rather than on the first usage which triggers
    an implicit introspect.

    Callers who are explicitly handling invalid token errors, like
    ``InactiveTokenError``, should put their handling around ``AuthState``
    construction rather than around ``AuthState`` attribute and method usage.

*   The provided ``FlaskAuthStateBuilder`` used by the provided flask blueprint
    now handles ``InactiveTokenError`` and ``InvalidTokenScopesError`` and will
    raise an ``AuthenticationError`` if these are encountered.
    The error handler in the provided blueprint translates these into
    ``UnauthorizedRequest`` exceptions, which render as HTTP 401 Unauthorized
    responses.
