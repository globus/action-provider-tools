Breaking changes
----------------

*   Removed the ``AuthState.errors`` attribute.

    In practice, this means that accesses to ``g.auth_state.errors`` will fail,
    but the attribute was always empty and never contained any information.

Bugfixes
--------

*   Fix an HTTP 500 error returned when an unauthorized user enumerates actions.
