Features
--------

- A new component, ``ClientFactory`` is now exposed in
  ``globus_action_provider_tools.client_factory``. This allows users to
  customize the transport-layer settings used for Auth and Groups clients which
  are constructed by the Action Provider Tools library, and sets initial
  parameters for this tuning.

  - The number of retries for both client types is reduced to 1 (from an
    SDK-default of 5).
  - The HTTP timeout is reduced to 30 seconds (from an SDK default of 60s).
  - The max sleep duration is reduced to 5 seconds (from an SDK default of
    10s).
  - ActionProviderConfig, AuthStateBuilder, and AuthState are all customized to
    accept a ClientFactory, and to use the client factory for any client
    building operations.
