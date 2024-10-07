Changes
-------

- The ``TokenChecker`` class has been removed and replaced in all cases with an
  ``AuthStateBuilder`` which better matches the purpose of this class.

- The ``check_token`` flask-specific helper has been replaced with a
  ``FlaskAuthStateBuilder`` which subclasses ``AuthStateBuilder`` and
  specializes it to handle a ``flask.Request`` object.
