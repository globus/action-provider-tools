CHANGELOG
#########

Unreleased changes
==================

Unreleased changes are documented in files in the `changelog.d`_ directory.

..  _changelog.d: https://github.com/globus/action-provider-tools/tree/main/changelog.d

..  scriv-insert-here

0.12.0b1 - 2022-02-11
=====================

Features
--------

- Upgrade to use major version 3 of the `Globus SDK
  <https://github.com/globus/globus-sdk-python>`_. If you are using Action
  Provider Tools in an environment which is currently using an earlier version
  of the Globus SDK, then you will need to upgrade first in order for this
  version to be compatible.

Bugfixes
--------

- Fixes an issue where the `ActionProviderBlueprint` decorators were not
  returning the decorated functions. This meant that the registered functions
  were loaded onto the Action Provider correctly but were `None` in the module
  in which they were defined.

0.11.5 - 2021-12-13
===================

Documentation
-------------

- Add a CHANGELOG and include it in the documentation.
- Use scriv for CHANGELOG management.

Added
-----

- Improved logging around the authentication module's cache hits and misses.

Fixed
-----

* Fixed handling of missing refresh tokens in dependent token grants. Now, even if a refresh token is expected in a dependent grant, it falls back to just using the access token up until the time the access token expires. We also shorten the dependent token grant cache to be less than the expected lifetime of an access token and, thus, from cache, we should not retrieve an access token which is already expired.

0.11.4 - 2021-11-01
===================

Features
--------

- Adds caching to the following Globus Auth operations: token introspection,
  group membership, dependent token grants.

Documentation
-------------

- Adds documentation around the new caching behavior:
  https://action-provider-tools.readthedocs.io/en/latest/toolkit/caching.html


0.11.3 - 2021-05-27
===================

Features
--------

- Bumps globus-sdk version dependency.

0.11.2 - 2021-05-21
===================

Features
--------

- Logs authentication errors when a token fails introspection or token validation.

Bugfixes
--------

- Updates pydantic version to address CVE-2021-29510

0.11.1 - 2021-04-30
===================

Features
--------

- Allows the detail field to be a string.
- Improves logging output in the case where there is an Action Provider throws
  Exceptions or an authentication issue.
- Allows for environment variable configuration.
- Bundles Flask an an optional dependency. See the README.md for information on
  installing the toolkit with Flask.
- Stabilizes package API.

Bugfixes
--------

- Updates serialization to output timezone aware datatime objects
- Updates the return type for Action Resume operations to allow for status codes
  to be returned from the route.
- Cleanly separates the Flask HTTP components from the plain Python components.

Deprecations
------------

- The Flask Callback Loader Helper is now deprecated in favor of the Flask
  Blueprint Helper.

0.11.0 - 2021-03-29
===================

Features
--------

- Provide helpers to standardize output formats for INACTIVE and FAILED states
- Adds a new resume operation to the helpers which is used to signal that an
  INACTIVE Action may be resumed.

0.10.5 - 2021-01-27
===================

Features
--------

- Adds exceptions that can be raised from Flask views to return standardized
  JSON responses.
- Adds support for Action Provider schema definitions based on Pydantic.
- Migrates ActionStatus, ActionRequest, and ActionProviderDescription to
  Pydantic classes.

Bugfixes
--------

- Modifies ActionProvider introspection endpoint creation on the
  ActionProviderBlueprint so that HTTP requests with and without trailing
  slashes receive the same results.

Documentation
-------------

- Action Provider Pydantic classes:
  https://action-provider-tools.readthedocs.io/en/latest/toolkit/validation.html
- Action Provider Pydantic input schema support:
  https://action-provider-tools.readthedocs.io/en/latest/examples/input_schemas.html#pydantic


0.10.4 - 2020-10-14
===================

Features
--------

- Improves testing tools for isolating tests between different instances of
  ActionProviderBlueprints and the Flask helpers.

0.10.3 - 2020-10-01
===================

Features
--------

- Adds a shared patch to the testing library to mock out an
  ActionProviderBlueprints TokenChecker
- Users can now specify a Globus Auth Client Name (legacy) when creating an
  instance of the ActionProviderBlueprint
- Users can now specify multiple acceptable scopes when creating an instance of
  the ActionProviderBlueprint

Bugfixes
--------

- Fixes an issue in the ActionProviderBlueprint where registering multiple
  Blueprints on a Flask app would only register one set of routes
