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

    -   Build a shared wheel once as an artifact and re-use it across all test environments.
    -   Consolidate standard testing and testing of minimum Flask versions.
