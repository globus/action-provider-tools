class ActionProviderToolsError(Exception):
    """
    The base Exception class for errors in Action Provider Tools.
    """


class AuthenticationError(ActionProviderToolsError):
    """
    An Exception class for errors triggered due to Authentication.
    """


class ConfigurationError(ActionProviderToolsError):
    """
    An Exception class for errors triggered by misconfiguration.
    """
