from __future__ import annotations

import json

import pytest
from flask import Flask

from globus_action_provider_tools import ActionRequest, AuthState
from globus_action_provider_tools.flask import ActionProviderBlueprint
from globus_action_provider_tools.flask.exceptions import (
    ActionNotFound,
    ActionProviderError,
)
from globus_action_provider_tools.flask.helpers import assign_json_provider
from globus_action_provider_tools.flask.request_lifecycle_hooks import (
    CloudWatchMetricEMFLogger,
)
from tests.test_flask_helpers.app_utils import ap_description, mock_action_run_func


def erroring_4xx_run_route(action_request: ActionRequest, auth: AuthState):
    raise ActionNotFound("Not Found")


def erroring_5xx_run_route(action_request: ActionRequest, auth: AuthState):
    raise ActionProviderError("Internal Server Error")


@pytest.mark.parametrize(
    "run_view_func,expected_2xxs,expected_4xxs,expected_5xxs",
    [
        (mock_action_run_func, 1, 0, 0),
        (erroring_4xx_run_route, 0, 1, 0),
        (erroring_5xx_run_route, 0, 0, 1),
    ],
)
def test_routes_emit_emf_logs(
    apt_blueprint_noauth,
    auth_state,
    capsys,
    run_view_func,
    expected_2xxs,
    expected_4xxs,
    expected_5xxs,
):
    app = Flask(__name__)
    assign_json_provider(app)
    aptb = ActionProviderBlueprint(
        name="TrackedActionProvider",
        import_name=__name__,
        url_prefix="/tracked",
        provider_description=ap_description,
        request_lifecycle_hooks=[
            CloudWatchMetricEMFLogger(
                namespace="ActionProviders",
                action_provider_name="TrackedActionProvider",
            )
        ],
    )
    aptb.action_run(run_view_func)

    apt_blueprint_noauth(aptb)
    app.register_blueprint(aptb)

    req = {"request_id": "0", "body": {"echo_string": "This is a test"}}
    app.test_client().post("/tracked/run", json=req)
    out, _ = capsys.readouterr()
    emf_log = json.loads(out)

    assert "_aws" in emf_log
    assert emf_log.get("Count") == 1
    assert emf_log.get("2XXs") == expected_2xxs
    assert emf_log.get("4XXs") == expected_4xxs
    assert emf_log.get("5XXs") == expected_5xxs
    assert type(emf_log.get("RequestLatency")) == float
    assert emf_log.get("ActionProvider") == "TrackedActionProvider"
    assert emf_log.get("Route") == "run"
