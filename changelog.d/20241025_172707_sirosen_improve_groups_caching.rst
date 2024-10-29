Changes
-------

- Group caching behavior in the ``AuthState`` class has been improved to ensure
  that the cache is checked before any external operations (e.g., dependent
  token callouts) are required. The cache now uses the token hash as its key,
  rather than a dependent token.
