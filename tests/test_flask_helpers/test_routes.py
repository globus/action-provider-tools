"""
A test module for unit testing the Action Provider Tools' Flask helper
libraries.

The helpers automatically handle creating routes that implement the
Action Provider API. These tests validate that the supported AP API versions
are in fact implemented.
"""

import pytest
from flask import Flask
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
    app: Flask = request.getfixturevalue(app_fixture)
    client = app.test_client()
    _, bp = list(app.blueprints.items())[0]

    if use_pydantic_schema:
        bp.input_schema = ActionProviderPydanticInputSchema
    else:
        bp.input_schema = action_provider_json_input_schema

    introspection_resp = ap_introspection(client, bp.url_prefix)
    assert introspection_resp.status_code == 200, introspection_resp.json

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


def ap_introspection(client, url_prefix: str):
    return client.get(url_prefix, follow_redirects=True)


def ap_enumeration(client, url_prefix: str):
    return client.get(f"{url_prefix}/actions")


def ap_run(client, url_prefix: str, *, api_version: str):
    payload = {"request_id": "0", "body": {"echo_string": "This is a test"}}

    if api_version == "1.0":
        return client.post(f"{url_prefix}/run", json=payload)
    if api_version == "1.1":
        return client.post(f"{url_prefix}/actions", json=payload)


def ap_status(client, url_prefix: str, action_id: str, *, api_version: str):
    if api_version == "1.0":
        return client.get(f"{url_prefix}/{action_id}/status")
    if api_version == "1.1":
        return client.get(f"{url_prefix}/actions/{action_id}")


def ap_log(client, url_prefix: str, action_id: str, *, api_version: str):
    if api_version == "1.0":
        return client.get(f"{url_prefix}/{action_id}/log")
    if api_version == "1.1":
        return client.get(f"{url_prefix}/actions/{action_id}/log")


def ap_cancel(client, url_prefix: str, action_id: str, *, api_version: str):
    if api_version == "1.0":
        return client.post(f"{url_prefix}/{action_id}/cancel")
    if api_version == "1.1":
        return client.post(f"{url_prefix}/actions/{action_id}/cancel")


def ap_release(client, url_prefix: str, action_id: str, *, api_version: str):
    if api_version == "1.0":
        return client.post(f"{url_prefix}/{action_id}/release")
    if api_version == "1.1":
        return client.delete(f"{url_prefix}/actions/{action_id}")
