CHANGELOG
#########

Unreleased changes
==================

Unreleased changes are documented in files in the `changelog.d`_ directory.

..  _changelog.d: https://github.com/globus/action-provider-tools/tree/main/changelog.d

..  scriv-insert-here

.. _changelog-0.21.0:

0.21.0 — 2025-02-11
===================

Breaking changes
----------------

*   The ``now_isoformat`` and ``principal_urn_regex`` names are no longer
    publicly exported by the library.

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

*   The ``required_authorizer_expiration_time`` parameter for
    ``AuthState.get_authorizer_for_scope`` has been removed. In recent
    releases it had no effect and emitted deprecation warnings.

.. _changelog-0.20.1:

0.20.1 — 2024-12-04
===================

Deprecations
------------

*   ``AuthState.get_dependent_tokens`` is now deprecated. It will be removed in
    a future release.

Features
--------

*   A new component, ``ClientFactory`` is now exposed in
    ``globus_action_provider_tools.client_factory``. This allows users to
    customize the transport-layer settings used for Auth and Groups clients which
    are constructed by the Action Provider Tools library, and sets initial
    parameters for this tuning.

    *   The number of retries for both client types is reduced to 1 (from an
        SDK-default of 5).
    *   The HTTP timeout is reduced to 30 seconds (from an SDK default of 60s).
    *   The max sleep duration is reduced to 5 seconds (from an SDK default of
        10s).
    *   ActionProviderConfig, AuthStateBuilder, and AuthState are all customized to
        accept a ClientFactory, and to use the client factory for any client
        building operations.

.. _changelog-0.20.0:

0.20.0 — 2024-11-07
===================

Breaking changes
----------------

*   Remove the ``globus_action_provider_tools.flask.api_helpers`` module,
    and the helpers it provided.

    If possible, it is recommended to immediately migrate Action Providers
    off of the code in the Flask API helpers module.

    If this cannot be done immediately, it is recommended to pin
    the Action Provider Tools dependency to ``0.19.1``.

Deprecations
------------

*   The ``required_authorizer_expiration_time`` parameter to ``get_authorizer_for_scope`` is deprecated.

    Given token expiration and caching lifetimes,
    it was not possible for this parameter to have any effect based on its prior documented usage.

Bugfixes
--------

*   Action Provider Tools no longer requests Dependent Refresh Tokens
    if Access Tokens are sufficient. As a result of this fix,
    the AuthState dependent token cache will never contain dependent refresh tokens.

Changes
-------

*   ``AuthState.introspect_token()`` will no longer return ``None``
    if the token is not active.

    Instead, a new exception, ``InactiveTokenError``, will be raised.
    ``InactiveTokenError`` is a subclass of ``ValueError``.

    Code that calls ``AuthState.introspect_token()`` no longer returns ``None``, either,
    but will instead raise ``ValueError`` (or a subclass) or a ``globus_sdk.GlobusAPIError``:

    *   ``AuthState.get_authorizer_for_scope``
    *   ``AuthState.effective_identity``
    *   ``AuthState.identities``

*   Group caching behavior in the ``AuthState`` class has been improved
    to ensure that the cache is checked before any external operations
    (e.g., dependent token callouts) are required.
    The cache now uses the token hash as its key, rather than a dependent token.

Documentation
-------------

*   Remove examples from documentation which relied upon the ``api_helpers`` module.

Development
-----------

*   Introduce new scriv categories to better communicate how the project evolves.

    The categories are also re-ordered,
    which defines how fragments will be ordered in the CHANGELOG.

*   Add a changelog fragment template.

.. _changelog-0.19.1:

0.19.1 — 2024-10-22
===================

Bugfixes
--------

- When introspecting tokens, allow the introspected scopes to be a superset of required scopes.

  A bug in the scope comparison code flipped the logic;
  if a user consented to scopes A and B and the action provider required only scope A,
  the comparison would fail *as if A and B were required but only A had been consented to*.

  This is now fixed.

.. _changelog-0.19.0:

0.19.0 — 2024-10-18
===================

**YANKED**

Features
--------

- The token introspect checking and caching performed in ``AuthState`` has
  been improved.

  - The cache is keyed off of token hashes, rather than raw token strings.

  - The ``exp`` and ``nbf`` values are no longer verified, removing the
    possibility of incorrect treatment of valid tokens as invalid due to clock
    drift.

  - Introspect response caching caches the raw response even for invalid
    tokens, meaning that Action Providers will no longer repeatedly introspect
    a token once it is known to be invalid.

  - Scope validation raises a new, dedicated error class,
    ``globus_action_provider_tools.authentication.InvalidTokenScopesError``, on
    failure.

Changes
-------

- The ``TokenChecker`` class has been removed and replaced in all cases with an
  ``AuthStateBuilder`` which better matches the purpose of this class.

- The ``check_token`` flask-specific helper has been replaced with a
  ``FlaskAuthStateBuilder`` which subclasses ``AuthStateBuilder`` and
  specializes it to handle a ``flask.Request`` object.

- The ``aud`` field of token introspect responses is no longer validated and
  fields associated with it have been removed. This includes changes to
  function and class initializer signatures.

  - The ``expected_audience`` field is no longer supported in ``AuthState`` and
    ``TokenChecker``. It has been removed from the initializers for these
    classes.

  - ``globus_auth_client_name`` has been removed from ``ActionProviderBlueprint``.

  - ``client_name`` has been removed from ``add_action_routes_to_blueprint``.

Development
-----------

- Move to `src/` tree layout

- Refactor ``AuthState.get_authorizer_for_scope`` without changing its
  primary outward semantics. The ``bypass_dependent_token_cache`` argument
  has been removed from its interface, as it is not necessary to expose
  with the improved implementation.

Removed
-------

- ``globus_action_provider_tools.testing`` has been removed. Users who were
  relying on these components should make use of their own fixtures and mocks.

.. _changelog-0.18.0:

0.18.0 — 2024-06-14
===================

Features
--------

- Added a new configuration class ``ActionProviderConfig`` with the initial option to
  ``scrub_validation_errors`` (default: True).

  - If disabled, user-provided data may be included in library raised validation errors.

Changes
-------

- Use UUIDs as action IDs.

- Scrubbed and non-scrubbed jsonschema errors have been enhanced. They now follow
  the format

  .. code-block:: text

     Field '<jsonpath>' (category: '<error_category>'): Input failed schema validation

  Sample:

  .. code-block:: text

     Field 'data.attributes.name' (category: 'required'): Input failed schema validation

- Pydantic errors will similarly include a category in their error messages.

Dependencies
------------

- Remove ``pybase62`` as a project dependency.

.. _changelog-0.17.0:

0.17.0 — 2024-04-11
===================

Bugfixes
--------

-   Allow package consumers to run with Python optimizations enabled.

    This is supported by replacing ``assert`` statements with ``raise AssertionError``.

Changes
-------

-   Remove references to web browsers from HTTP 401 Unauthorized responses.

-   Reduce I/O with Globus Auth when possible.

    *   If the action provider is visible to ``"public"``,
        introspection requests are allowed without checking tokens.
    *   If the bearer token is missing, malformed, or is too short or long,
        the incoming request is summarily rejected with HTTP 401
        without introspecting the token.

.. _changelog-0.16.0:

0.16.0 — 2024-03-27
===================

Features
--------

*   Support CORS requests to introspection routes.

Bugfixes
--------

*   Prevent ``TypeError``\s from occurring during pydantic error formatting.

    This was caused by integer list indexes in pydantic error locations.

Documentation
-------------

*   Fix failing documentation builds (locally, and in Read the Docs).
*   Enforce reproducible documentation builds using full dependency locking.
*   Bump the OpenAPI documentation version and build the documentation.

Development
-----------

*   Test documentation builds in GitHub CI.

*   Update ``make install`` so it can get developers up and running.
*   Document that ``make install`` can get developers up and running.

Dependencies
------------

*   Manage test, mypy, and doc dependencies using a consistent framework.
*   Introduce a standard command, ``tox run -m update``, that can update dependencies.

.. _changelog-0.15.0:

0.15.0 — 2024-01-26
===================

Bugfixes
--------

- Groups were not being properly considered in authorization checks.

Changes
-------

- Error descriptions in responses are now always strings (previously they could also
  be lists of strings or lists of dictionaries).
- Input validation errors now use an HTTP response status code of 422.
- Validation errors no longer return input data in their description.

.. _changelog-0.14.1:

0.14.1 — 2023-10-27
===================

Changes
-------

- Change the way that dependent token caching computes cache keys to improve
  upstream cache busting

.. _changelog-0.14.0:

0.14.0 — 2023-10-19
===================

Features
--------

- Added a CloudWatchEMFLogger ``RequestLifecycleHook`` class.
  When attached to an ``ActionProviderBlueprint``, it will emit request count, latency,
  and response category (2xxs, 4xxs, 5xxs) count metrics through CloudWatch EMF. Metrics
  are emitted both for the aggregate AP dimension set and the individual route dimension
  set.

  - Classes may be provided at Blueprint instantiation time to register before, after,
    and/or teardown functionality wrapping route invocation.

.. _changelog-0.13.0rc2:

0.13.0rc2 — 2023-10-06
======================

Python support
--------------

-   Support Python 3.12.
-   Drop support for Python 3.7.

Development
-----------

-   Remove unused dependencies.

Dependencies
------------

-   Raise the minimum Flask version to 2.3.0, which dropped support for Python 3.7.

.. _changelog-0.13.0rc1:

0.13.0rc1 — 2023-07-24
======================

Changes
-------

- The minimum pyyaml version is now 6.0

Deprecations
------------

- Imports from ``globus_action_provider_tools.flask`` will no longer emit a
  ``DeprecationWarning``

Development
-----------

-   During local testing, build a shared wheel.

    Previously, a shared ``.tar.gz`` file was created.
    However, in each tox environment, pip would convert this to a wheel during installation.

    This change decreases local test times from ~20 seconds to ~12 seconds.

-   Support running tox test environments in parallel (run ``tox p``).

    This change decreases local test times to only ~3 seconds.

-   Overhaul CI.

    -   Introduce caching of the ``.tox/`` and ``.venv/`` directories.

        The cache is invalidated once each week (``date %U`` rolls the week on Sundays).

    -   Build a shared wheel once as an artifact and reuse it across all test environments.
    -   Consolidate standard testing and testing of minimum Flask versions.

.. _changelog-0.13.0b2:

0.13.0b2 — 2022-12-16
=====================

Changes
-------

-   Remove an unused parameter from ``TokenChecker``: ``cache_config``.
-   Remove a no-op call to Globus Auth during ``TokenChecker`` instantiation.
-   Remove the ``ConfigurationError`` class.

.. _changelog-0.13.0b1:

0.13.0b1 — 2022-12-14
=====================

Python support
--------------

- Add support for Python 3.11.
- Drop support for Python 3.6.

Bugfixes
--------

-   Fix a crash that will occur if a non-object JSON document is submitted.
    For example, this will happen if the incoming JSON document is ``"string"``
    or ``["array"]``.

- Fix a crash that occurs when an HTTP 400 "invalid grant" error is received
  from Globus Auth while getting an authorizer for a given scope.

  This is now caught by ``AuthState.get_authorizer_for_scope()`` and ``None`` is returned.

Changes
-------

-   Remove the ``__version__`` attribute.

    The ``importlib.metadata`` module in Python 3.8 and higher
    (or the backported ``importlib_metadata`` package)
    can be used to query the version of installed packages if needed.

- ``jsonschema>=4.17,<5`` is now required by action-provider-tools.

  Consumers of the library will have to update to a more recent version of ``jsonschema``
  if they are using it explicitly.

0.12.0 - 2022-03-02
===================

*No changes from 0.12.0b1.*


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
