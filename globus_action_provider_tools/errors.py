class ActionProviderToolsError(Exception):
    """Base class for exceptions from this library."""


class AuthenticationError(ActionProviderToolsError):
    """
    Errors in the authentication helpers.
    """


class ConfigurationError(AuthenticationError):
    """
    Raised for errors triggered by misconfiguration.
    """

    def __init__(self, message, original_error):
        super().__init__(message)
        self.original_error = original_error


class TokenValidationError(AuthenticationError):
    def __init__(self, original_error):
        super().__init__(str(original_error))
        self.original_error = original_error
