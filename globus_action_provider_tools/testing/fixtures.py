from unittest.mock import patch

import pytest

from globus_action_provider_tools.flask.apt_blueprint import ActionProviderBlueprint
from globus_action_provider_tools.testing.mocks import mock_authstate, mock_tokenchecker


@pytest.fixture(scope="session")
def apt_blueprint_noauth():
    """
    A fixture designed to mock an ActionProviderBlueprint instance's Globus
    Auth integration. The fixture returns a function to which the instance
    should be supplied as a parameter:

    i.e. apt_blueprint_noauth(aptb)
    """

    def _apt_blueprint_noauth(aptb: ActionProviderBlueprint):
        # Manually remove the function that creates the internal token_checker
        for f in aptb.deferred_functions:
            if f.__name__ == "_create_token_checker":
                aptb.deferred_functions.remove(f)

        # Use a mocked token checker internally
        aptb.checker = mock_tokenchecker()

    return _apt_blueprint_noauth


@pytest.fixture(scope="session")
def flask_helpers_noauth():
    """
    A fixture designed to mock the Globus Auth integration in an Flask app
    created using the api_helpers. Simply using this fixture will allow creating
    the mocked app.
    """
    with patch(
        "globus_action_provider_tools.flask.api_helpers.TokenChecker.check_token",
        return_value=mock_authstate(),
    ):
        yield
