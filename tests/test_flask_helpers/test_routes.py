"""
A test module for unit testing the Action Provider Tools' Flask helper
libraries.

The helpers automatically handle creating routes that implement the
Action Provider API. These tests validate that the supported AP API versions
are in fact implemented.
"""

import flask
import flask.testing
import pytest
from globus_sdk._testing import load_response

from .ap_client import ActionProviderClient
from .app_utils import (
    ActionProviderPydanticInputSchema,
    action_provider_json_input_schema,
)


@pytest.mark.parametrize("app_fixture", ["aptb_app", "add_routes_app"])
@pytest.mark.parametrize("api_version", ["1.0", "1.1"])
@pytest.mark.parametrize("use_pydantic_schema", [True, False])
def test_routes_conform_to_api(
    freeze_time, request, app_fixture: str, api_version: str, use_pydantic_schema: bool
):
    freeze_time(load_response("token-introspect", case="success"))
    app: flask.Flask = request.getfixturevalue(app_fixture)
    _, bp = list(app.blueprints.items())[0]
    if use_pydantic_schema:
        bp.input_schema = ActionProviderPydanticInputSchema
    else:
        bp.input_schema = action_provider_json_input_schema

    client = ActionProviderClient(
        app.test_client(), bp.url_prefix, api_version=api_version
    )

    introspect_resp = client.introspect()
    assert list(introspect_resp.access_control_allow_origin) == ["*"]
    client.enumerate()
    action_id = client.run().get_json()["action_id"]
    client.status(action_id)
    client.log(action_id)
    client.cancel(action_id)
    client.release(action_id)


@pytest.mark.parametrize("app_fixture", ["aptb_app", "add_routes_app"])
def test_introspect_cors_requests(request, app_fixture):
    """Verify that CORS requests are allowed on introspect routes."""

    app: flask.Flask = request.getfixturevalue(app_fixture)
    client: flask.testing.FlaskClient = app.test_client()
    _, bp = list(app.blueprints.items())[0]

    introspection_cors_response = client.options(bp.url_prefix)
    assert introspection_cors_response.status_code == 204

    # Verify the values of each header.
    assert list(introspection_cors_response.access_control_allow_methods) == [
        "GET",
        "OPTIONS",
    ]
    assert list(introspection_cors_response.access_control_allow_origin) == ["*"]
    assert list(introspection_cors_response.access_control_expose_headers) == ["*"]


@pytest.mark.parametrize("app_fixture", ["aptb_app", "add_routes_app"])
@pytest.mark.parametrize("api_version", ["1.0", "1.1"])
@pytest.mark.parametrize(
    "authorization_header",
    (
        pytest.param(None, id="missing Authorization header"),
        pytest.param("", id="blank header value"),
        pytest.param("  ", id="whitespace header value"),
        pytest.param("A" * 100, id="no 'Bearer ' prefix"),
        pytest.param("Bearer " + "A" * 9, id="short token"),
        pytest.param("Bearer " + "A" * 2049, id="long token"),
    ),
)
def test_bogus_authorization_headers_are_rejected_without_io(
    request, app_fixture, api_version, authorization_header
):
    app: flask.Flask = request.getfixturevalue(app_fixture)
    _, bp = list(app.blueprints.items())[0]
    bp.input_schema = ActionProviderPydanticInputSchema

    client = ActionProviderClient(
        app.test_client(), bp.url_prefix, api_version=api_version
    )

    headers = []
    if authorization_header is not None:
        headers.append(("Authorization", authorization_header))

    client.enumerate(assert_status=401, headers=headers)
    client.run(assert_status=401, headers=headers)
    client.status("any", assert_status=401, headers=headers)
    client.log("any", assert_status=401, headers=headers)
    client.cancel("any", assert_status=401, headers=headers)
    client.release("any", assert_status=401, headers=headers)
