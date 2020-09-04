"""
This module contains fixtures for creating Flask app instances using the Flask
helpers with authentication mocked out. Each fixture creates an identical app,
the only difference being in the helper that is used to create the app.
"""


from unittest.mock import patch

import pytest
from flask import Blueprint, Flask

from globus_action_provider_tools.data_types import ActionProviderDescription
from globus_action_provider_tools.flask import (
    ActionProviderBlueprint,
    add_action_routes_to_blueprint,
)

from .app_utils import (
    ap_description,
    test_action_cancel,
    test_action_enumeration,
    test_action_log,
    test_action_release,
    test_action_run,
    test_action_status,
)


@pytest.fixture()
def aptb_app(auth_state):
    """
    This fixture creates a Flask app using the ActionProviderBlueprint
    helper. The function form of the decorators are used to register each
    endpoint's functions.
    """
    app = Flask(__name__)
    aptb = ActionProviderBlueprint(
        name="aptb",
        import_name=__name__,
        url_prefix="/aptb",
        provider_description=ap_description,
    )
    aptb.action_run(test_action_run)
    aptb.action_status(test_action_status)
    aptb.action_cancel(test_action_cancel)
    aptb.action_release(test_action_release)
    aptb.action_log(test_action_log)
    aptb.action_enumerate(test_action_enumeration)

    with patch(
        "globus_action_provider_tools.flask.apt_blueprint.TokenChecker.check_token",
        return_value=auth_state,
    ):
        app.register_blueprint(aptb)
        yield app


@pytest.fixture()
def add_routes_app(auth_state):
    """
    This fixture creates a Flask app with routes loaded via the
    add_action_routes_to_blueprint Flask helper.
    """
    app = Flask(__name__)
    bp = Blueprint("func_helper", __name__, url_prefix="/func_helper")

    with patch(
        "globus_action_provider_tools.flask.api_helpers.TokenChecker.check_token",
        return_value=auth_state,
    ):
        add_action_routes_to_blueprint(
            blueprint=bp,
            client_id=None,
            client_secret=None,
            client_name=None,
            provider_description=ap_description,
            action_run_callback=test_action_run,
            action_status_callback=test_action_status,
            action_cancel_callback=test_action_cancel,
            action_release_callback=test_action_release,
            action_log_callback=test_action_log,
            action_enumeration_callback=test_action_enumeration,
            additional_scopes=[
                "https://auth.globus.org/scopes/d3a66776-759f-4316-ba55-21725fe37323/secondary_scope"
            ],
        )
        app.register_blueprint(bp)
        yield app
