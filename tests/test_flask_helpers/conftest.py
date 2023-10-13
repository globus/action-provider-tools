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
from globus_action_provider_tools.testing.fixtures import (
    apt_blueprint_noauth,
    flask_helpers_noauth,
)

from .app_utils import (
    ap_description,
    mock_action_cancel_func,
    mock_action_enumeration_func,
    mock_action_log_func,
    mock_action_release_func,
    mock_action_run_func,
    mock_action_status_func,
)


@pytest.fixture()
def aptb_app(apt_blueprint_noauth, auth_state):
    """
    This fixture creates a Flask app using the ActionProviderBlueprint
    helper. The function form of the decorators are used to register each
    endpoint's functions.
    """
    app = Flask(__name__)
    assign_json_provider(app)
    aptb = ActionProviderBlueprint(
        name="aptb",
        import_name=__name__,
        url_prefix="/aptb",
        provider_description=ap_description,
    )
    aptb.action_run(mock_action_run_func)
    aptb.action_status(mock_action_status_func)
    aptb.action_cancel(mock_action_cancel_func)
    aptb.action_release(mock_action_release_func)
    aptb.action_log(mock_action_log_func)
    aptb.action_enumerate(mock_action_enumeration_func)

    apt_blueprint_noauth(aptb)
    app.register_blueprint(aptb)
    return app


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
