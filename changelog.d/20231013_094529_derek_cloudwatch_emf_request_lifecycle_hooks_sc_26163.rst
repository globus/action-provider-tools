
Features
--------

- `[sc-26163] <https://app.shortcut.com/globus/story/26163>`
  Added support for ``RequestLifecycleHook`` class registration to the flask
  ``ActionProviderBlueprint`` class.
  Classes may be provided at Blueprint instantiation time to register before, after,
  and/or teardown functionality wrapping route invocation.

- `[sc-26163] <https://app.shortcut.com/globus/story/26163>`
  Added a CloudWatchEMFLogger ``RequestLifecycleHook`` class.
  When attached to an ``ActionProviderBlueprint``, it will emit request count, latency,
  and response category (2xxs, 4xxs, 5xxs) count metrics through CloudWatch EMF. Metrics
  are emitted both for the aggregate AP dimension set and the individual route dimension
  set.
