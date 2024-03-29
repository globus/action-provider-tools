Changes
-------

-   Reduce I/O with Globus Auth when possible.

    *   If the action provider is visible to ``"public"``,
        introspection requests are allowed without checking tokens.
    *   If the bearer token is missing, malformed, or is too short or long,
        the incoming request is summarily rejected with HTTP 401
        without introspecting the token.
