.. A new scriv changelog fragment.
..
.. Uncomment the header that is right (remove the leading dots).
..
.. Removed
.. -------
..
.. - A bullet item for the Removed category.
..
.. Added
.. -----
..
.. - A bullet item for the Added category.
..
.. Changed
.. -------
..
.. - A bullet item for the Changed category.
..
.. Deprecated
.. ----------
..
.. - A bullet item for the Deprecated category.
..
.. Fixed
.. -----
..
.. - A bullet item for the Fixed category.
..
* Fixed handling of missing refresh tokens in dependent token grants. Now, even if a refresh token is expected in a dependent grant, it falls back to just using the access token up until the time the access token expires. We also shorten the dependent token grant cache to be less than the expected lifetime of an access token and, thus, from cache, we should not retrieve an access token which is already expired.
.. Security
.. --------
..
.. - A bullet item for the Security category.
..
