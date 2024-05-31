import dataclasses


@dataclasses.dataclass(frozen=True)
class ActionProviderConfig:
    # When enabled, validation error messages returned to users will be scrubbed of
    # user-provided data.
    # This means provides a more secure response, mitigating the risk of leaking
    # provided data but making the error message less useful for debugging in the
    # process.
    scrub_validation_errors: bool = True


DEFAULT_CONFIG = ActionProviderConfig()
