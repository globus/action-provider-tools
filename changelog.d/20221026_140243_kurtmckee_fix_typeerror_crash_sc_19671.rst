Bugfixes
--------

-   Fix a crash that will occur if a non-object JSON document is submitted.
    For example, this will happen if the incoming JSON document is ``"string"``
    or ``["array"]``.
