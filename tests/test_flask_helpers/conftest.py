"""
This module contains fixtures for creating Flask app instances using the Flask
helpers with authentication mocked out. Each fixture creates an identical app,
the only difference being in the helper that is used to create the app.
"""


import pytest
from flask import Flask

from globus_action_provider_tools.flask import (
    ActionProviderBlueprint,
)
from globus_action_provider_tools.flask.helpers import assign_json_provider
from globus_action_provider_tools.testing.fixtures import (
    apt_blueprint_noauth,
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
    aptb.action_run(test_action_run)
    aptb.action_status(test_action_status)
    aptb.action_cancel(test_action_cancel)
    aptb.action_release(test_action_release)
    aptb.action_log(test_action_log)
    aptb.action_enumerate(test_action_enumeration)

    apt_blueprint_noauth(aptb)
    app.register_blueprint(aptb)
    return app
