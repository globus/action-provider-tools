Caching
=======

To avoid excessively taxing Globus Auth, the ``AuthState`` will, by default,
cache values returned from Globus Auth and Globus Groups related to token validation (introspection), dependent token creation and group membership. These caches are maintained at the global level, and thus are shared across all invocations of methods on any ``AuthState`` object. In turn, this means that as the Action Provider handles multiple requests from a small set of users over a short period of time, many Globus Auth calls will be handled from the local cache(s) rather than via an additional remote request.

In more detail, there are three caches maintained: one for results of token validation/introspection, one for results from requesting dependent tokens and one for Groups membership look ups. The policies implemented in these caches are considered the best practice by the Globus team as they trade-off the performance benefits of caching with the need for consistency with out-of-band operations such as a user rescinding consent for a previously allowed operation on their behalf or if the user's Group membership status changes. The policies for each of the caches is as follows:

* Introspection cache: uses the incoming request's Access Token as present in the ``Authorization`` header of the HTTP request following the identification string ``Bearer``. A value in the cache has a lifetime of 30 seconds, and, thus, after 30 seconds, a new request presenting the same access token will be served via a call to Globus Auth.

* Dependent token cache: Dependent tokens are used when the Action Provider needs to make calls to other services on behalf of the user making a request. Action Provider Tools performs a dependent token grant when either the ``AuthState.get_dependent_tokens`` or ``AuthState.get_authorizer_for_scope`` methods are performed. The key to this cache is determined by a preceding call to token introspection (which, per the cache above, may return a cached value). The introspection result returns a field specifically for managing such a cache called ``dependent_tokens_cache_id``. This value is used as the key for the cache lookup, and there is no timeout associated with the cache.

* Group Membership cache: Invoking the Groups service required a dependent token, which will be retrieved by an invocation to ``AuthState.get_dependent_tokens`` (which, as stated above, may return a cached value). The access token for the Groups service is used as a key to the group membership cache. A value in the cache has a lifetime of 5 minutes, and, thus, after 5 minutes, the Groups service will be invoked to get group membership even if the access token to be used for accessing the Groups service is still in the Dependent token cache.

Each of the caches has a maximum storage size of 100 elements.
