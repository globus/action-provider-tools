Bugfixes
--------

- Fixes an issue where the `ActionProviderBlueprint` decorators were not
  returning the decorated functions. This meant that the registered functions
  were loaded onto the Action Provider correctly but were `None` in the module
  in which they were defined.
