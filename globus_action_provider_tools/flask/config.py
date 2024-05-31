import dataclasses


@dataclasses.dataclass(frozen=True)
class ActionProviderConfig:
    # When enabled, validation error messages returned to users will be scrubbed of
    #   user-provided data.
    # Implicitly this means that the error message will be less informative to the user.
    scrubbed_validation_errors: bool = True


DEFAULT_CONFIG = ActionProviderConfig()
