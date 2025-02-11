"""
This module contains fixtures for creating a Flask app using the
ActionProviderBlueprint, but with authentication mocked out.
"""

from unittest import mock

import pytest

from .app_utils import (
    ap_description,
    mock_action_cancel_func,
    mock_action_enumeration_func,
    mock_action_log_func,
    mock_action_release_func,
    mock_action_run_func,
    mock_action_status_func,
)


@pytest.fixture
def aptb_app(auth_state, create_app_from_blueprint):
    """
    This fixture creates a Flask app using the ActionProviderBlueprint
    helper. The function form of the decorators are used to register each
    endpoint's functions.
    """
    from globus_action_provider_tools.flask import ActionProviderBlueprint

    blueprint = ActionProviderBlueprint(
        name="aptb",
        import_name=__name__,
        url_prefix="/aptb",
        provider_description=ap_description,
    )
    with mock.patch(
        "globus_action_provider_tools.authentication.AuthStateBuilder.build",
        return_value=auth_state,
    ):
        yield create_app_from_blueprint(blueprint)


@pytest.fixture
def create_app_from_blueprint(apt_blueprint_noauth, auth_state):
    from flask import Flask

    from globus_action_provider_tools.flask.helpers import assign_json_provider

    def _create_app_from_blueprint(blueprint) -> Flask:
        app = Flask(__name__)
        assign_json_provider(app)
        blueprint.action_run(mock_action_run_func)
        blueprint.action_status(mock_action_status_func)
        blueprint.action_cancel(mock_action_cancel_func)
        blueprint.action_release(mock_action_release_func)
        blueprint.action_log(mock_action_log_func)
        blueprint.action_enumerate(mock_action_enumeration_func)

        apt_blueprint_noauth(blueprint)
        app.register_blueprint(blueprint)
        return app

    return _create_app_from_blueprint
