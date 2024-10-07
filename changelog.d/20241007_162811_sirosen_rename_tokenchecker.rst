Changes
-------

- The ``TokenChecker`` class has been removed and replaced in all cases with an
  ``AuthStateBuilder`` which better matches the purpose of this class.

- The ``check_token`` flask-specific helper has been replaced with a
  ``FlaskAuthStateBuilder`` which subclasses ``AuthStateBuilder`` and
  specializes it to handle a ``flask.Request`` object.

- The flask helpers no longer attempt to validate the ``aud`` field of tokens
  during introspection, and users are no longer allowed to provide an
  ``expected_audience`` or similar field in order to control such validation.

Removed
-------

- The ``testing`` subpackage has been removed.
