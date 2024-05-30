"""
This module contains fixtures for creating Flask app instances using the Flask
helpers with authentication mocked out. Each fixture creates an identical app,
the only difference being in the helper that is used to create the app.
"""

import pytest
from flask import Blueprint, Flask

from globus_action_provider_tools.flask import (
    ActionProviderBlueprint,
    add_action_routes_to_blueprint,
)
from globus_action_provider_tools.flask.helpers import assign_json_provider

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
def aptb_app(create_app_from_blueprint):
    """
    This fixture creates a Flask app using the ActionProviderBlueprint
    helper. The function form of the decorators are used to register each
    endpoint's functions.
    """
    blueprint = ActionProviderBlueprint(
        name="aptb",
        import_name=__name__,
        url_prefix="/aptb",
        provider_description=ap_description,
    )
    return create_app_from_blueprint(blueprint)


@pytest.fixture
def create_app_from_blueprint(apt_blueprint_noauth, auth_state):
    def _create_app_from_blueprint(blueprint: ActionProviderBlueprint) -> Flask:
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


@pytest.fixture()
def add_routes_app(flask_helpers_noauth, auth_state):
    """
    This fixture creates a Flask app with routes loaded via the
    add_action_routes_to_blueprint Flask helper.
    """
    app = Flask(__name__)
    assign_json_provider(app)
    bp = Blueprint("func_helper", __name__, url_prefix="/func_helper")
    add_action_routes_to_blueprint(
        blueprint=bp,
        client_id="bogus",
        client_secret="bogus",
        client_name=None,
        provider_description=ap_description,
        action_run_callback=mock_action_run_func,
        action_status_callback=mock_action_status_func,
        action_cancel_callback=mock_action_cancel_func,
        action_release_callback=mock_action_release_func,
        action_log_callback=mock_action_log_func,
        action_enumeration_callback=mock_action_enumeration_func,
        additional_scopes=[
            "https://auth.globus.org/scopes/d3a66776-759f-4316-ba55-21725fe37323/secondary_scope"
        ],
    )
    app.register_blueprint(bp)
    return app
