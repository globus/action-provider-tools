
Features
--------

- `[sc-26163] <https://app.shortcut.com/globus/story/26163>`
  Added support for middleware registration to the flask ActionProviderBlueprint class.
  Classes may be provided at Blueprint instantiation time to register before, after, or
  teardown functionality to wrap all view invocation.

- `[sc-26163] <https://app.shortcut.com/globus/story/26163>`
  Added a CloudWatchEMFLogger middleware class.
  When attached to an ActionProviderBlueprint, it will emit request count, latency, and
  response category (2xxs, 4xxs, 5xxs) count metrics through CloudWatch EMF. Metrics
  are emitted both at the aggregate AP and at the individual route level.
