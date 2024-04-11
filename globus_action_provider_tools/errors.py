class ActionProviderToolsError(Exception):
    """
    The base Exception class for errors in Action Provider Tools.
    """


class AuthenticationError(ActionProviderToolsError):
    """
    An Exception class for errors triggered due to Authentication.
    """


class UnverifiedAuthenticationError(AuthenticationError):
    """
    Indicates that a token has been rejected without an I/O call to Globus Auth.

    This may occur if the request is missing an Authorization header,
    or if the header value is malformed (such as missing the ``"Bearer "`` prefix),
    or if the token does not meet known token length requirements.
    """
