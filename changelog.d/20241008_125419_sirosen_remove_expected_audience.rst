Changes
-------

- The ``aud`` field of token introspect responses is no longer validated and
  fields associated with it have been removed. This includes changes to
  function and class initializer signatures.

  - The ``expected_audience`` field is no longer supported in ``AuthState`` and
    ``TokenChecker``. It has been removed from the initializers for these
    classes.

  - ``globus_auth_client_name`` has been removed from ``ActionProviderBlueprint``.

  - ``client_name`` has been removed from ``add_action_routes_to_blueprint``.
