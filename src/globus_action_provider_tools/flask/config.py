import dataclasses

from globus_action_provider_tools.client_factory import ClientFactory


@dataclasses.dataclass(frozen=True)
class ActionProviderConfig:
    # When enabled, validation error messages returned to users will be scrubbed of
    # user-provided data.
    # This means provides a more secure response, mitigating the risk of leaking
    # provided data but making the error message less useful for debugging in the
    # process.
    scrub_validation_errors: bool = True
    # by default, the config provides a base ClientFactory as the constructor for
    # Auth and Groups clients, with default parameters
    client_factory: ClientFactory = ClientFactory()


DEFAULT_CONFIG = ActionProviderConfig()
