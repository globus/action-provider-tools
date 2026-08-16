Bugfixes
--------

*   Eliminate race conditions in token cache handling code.

    If triggered, this would have manifested as uncaught ``KeyError`` exceptions.
