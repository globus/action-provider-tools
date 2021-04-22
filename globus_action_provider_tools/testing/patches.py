import warnings
from unittest.mock import patch

from globus_action_provider_tools.testing.mocks import mock_authstate

warnings.warn(
    (
        "The globus_action_provider_tools.testing.patches module is deprecated and will "
        "be removed in 0.12.0. Please consider using the "
        "globus_action_provider_tools.testing.fixtures module instead."
    ),
    DeprecationWarning,
    stacklevel=2,
)


flask_api_helpers_tokenchecker_patch = patch(
    "globus_action_provider_tools.flask.api_helpers.TokenChecker.check_token",
    return_value=mock_authstate(),
)

flask_blueprint_tokenchecker_patch = patch(
    "globus_action_provider_tools.flask.apt_blueprint.TokenChecker.check_token",
    return_value=mock_authstate(),
)
