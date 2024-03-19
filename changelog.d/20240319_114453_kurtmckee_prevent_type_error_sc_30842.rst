Bugfixes
--------

*   Prevent ``TypeError``\s from occurring during pydantic error formatting.

    This was caused by integer list indexes in pydantic error locations.
