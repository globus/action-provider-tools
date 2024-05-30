import dataclasses


@dataclasses.dataclass(frozen=True)
class ActionProviderConfig:
    # When enabled, error messages returned to users will not include any user provided
    #   data.
    validation_error_obscuring: bool = True


DEFAULT_CONFIG = ActionProviderConfig()
