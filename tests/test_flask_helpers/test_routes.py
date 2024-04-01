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
    client = app.test_client()
    _, bp = list(app.blueprints.items())[0]

    if use_pydantic_schema:
        bp.input_schema = ActionProviderPydanticInputSchema
    else:
        bp.input_schema = action_provider_json_input_schema

    introspection_resp = ap_introspection(client, bp.url_prefix)
    assert introspection_resp.status_code == 200, introspection_resp.json

    # Verify CORS response
    assert list(introspection_resp.access_control_allow_origin) == ["*"]

    trailing_slash_introspection_resp = ap_introspection(client, bp.url_prefix + "/")
    assert (
        trailing_slash_introspection_resp.status_code == 200
    ), trailing_slash_introspection_resp.json

    if api_version == "1.1":
        enumeration_resp = ap_enumeration(client, bp.url_prefix)
        assert enumeration_resp.status_code == 200, enumeration_resp.json

    run_resp = ap_run(client, bp.url_prefix, api_version=api_version)
    assert run_resp.status_code == 202, run_resp.json

    action_id = run_resp.get_json()["action_id"]
    status_resp = ap_status(client, bp.url_prefix, action_id, api_version=api_version)
    assert status_resp.status_code == 200, status_resp.json

    log_resp = ap_log(client, bp.url_prefix, action_id, api_version=api_version)
    assert log_resp.status_code == 200, log_resp.json

    cancel_resp = ap_cancel(client, bp.url_prefix, action_id, api_version=api_version)
    assert cancel_resp.status_code == 200, cancel_resp.json

    release_resp = ap_release(client, bp.url_prefix, action_id, api_version=api_version)
    assert release_resp.status_code == 200, release_resp.json


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
    client = app.test_client()
    _, bp = list(app.blueprints.items())[0]

    bp.input_schema = ActionProviderPydanticInputSchema

    headers = []
    if authorization_header is not None:
        headers.append(("Authorization", authorization_header))

    if api_version == "1.1":
        enumeration_resp = ap_enumeration(client, bp.url_prefix, headers=headers)
        assert enumeration_resp.status_code == 401, enumeration_resp.json

    run_resp = ap_run(client, bp.url_prefix, api_version=api_version, headers=headers)
    assert run_resp.status_code == 401, run_resp.json

    status_resp = ap_status(
        client, bp.url_prefix, "any", api_version=api_version, headers=headers
    )
    assert status_resp.status_code == 401, status_resp.json

    log_resp = ap_log(
        client, bp.url_prefix, "any", api_version=api_version, headers=headers
    )
    assert log_resp.status_code == 401, log_resp.json

    cancel_resp = ap_cancel(
        client, bp.url_prefix, "any", api_version=api_version, headers=headers
    )
    assert cancel_resp.status_code == 401, cancel_resp.json

    release_resp = ap_release(
        client, bp.url_prefix, "any", api_version=api_version, headers=headers
    )
    assert release_resp.status_code == 401, release_resp.json


def ap_introspection(client, url_prefix: str):
    return client.get(url_prefix, follow_redirects=True)


def ap_enumeration(client, url_prefix: str, **kwargs):
    kwargs.setdefault("headers", [("Authorization", "Bearer AAAAAAAAAA")])
    return client.get(f"{url_prefix}/actions", **kwargs)


def ap_run(client, url_prefix: str, *, api_version: str, **kwargs):
    kwargs.setdefault("headers", [("Authorization", "Bearer AAAAAAAAAA")])
    payload = {"request_id": "0", "body": {"echo_string": "This is a test"}}

    if api_version == "1.0":
        return client.post(f"{url_prefix}/run", json=payload, **kwargs)
    if api_version == "1.1":
        return client.post(f"{url_prefix}/actions", json=payload, **kwargs)


def ap_status(client, url_prefix: str, action_id: str, *, api_version: str, **kwargs):
    kwargs.setdefault("headers", [("Authorization", "Bearer AAAAAAAAAA")])
    if api_version == "1.0":
        return client.get(f"{url_prefix}/{action_id}/status", **kwargs)
    if api_version == "1.1":
        return client.get(f"{url_prefix}/actions/{action_id}", **kwargs)


def ap_log(client, url_prefix: str, action_id: str, *, api_version: str, **kwargs):
    kwargs.setdefault("headers", [("Authorization", "Bearer AAAAAAAAAA")])
    if api_version == "1.0":
        return client.get(f"{url_prefix}/{action_id}/log", **kwargs)
    if api_version == "1.1":
        return client.get(f"{url_prefix}/actions/{action_id}/log", **kwargs)


def ap_cancel(client, url_prefix: str, action_id: str, *, api_version: str, **kwargs):
    kwargs.setdefault("headers", [("Authorization", "Bearer AAAAAAAAAA")])
    if api_version == "1.0":
        return client.post(f"{url_prefix}/{action_id}/cancel", **kwargs)
    if api_version == "1.1":
        return client.post(f"{url_prefix}/actions/{action_id}/cancel", **kwargs)


def ap_release(client, url_prefix: str, action_id: str, *, api_version: str, **kwargs):
    kwargs.setdefault("headers", [("Authorization", "Bearer AAAAAAAAAA")])
    if api_version == "1.0":
        return client.post(f"{url_prefix}/{action_id}/release", **kwargs)
    if api_version == "1.1":
        return client.delete(f"{url_prefix}/actions/{action_id}", **kwargs)
