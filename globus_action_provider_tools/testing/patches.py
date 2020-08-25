from unittest.mock import patch

from globus_action_provider_tools.testing.mocks import mock_authstate

flask_api_helpers_tokenchecker_patch = patch(
    "globus_action_provider_tools.flask.api_helpers.TokenChecker.check_token",
    return_value=mock_authstate(),
)
