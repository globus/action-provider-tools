"""
A test module for unit testing the Action Provider Tools' Flask helper
libraries.

The helpers automatically handle creating routes that implement the
Action Provider API. These tests validate that the supported AP API versions 
are in fact implemented.
"""

from typing import Dict
from unittest.mock import Mock

import pytest
from flask import Flask

from globus_action_provider_tools.data_types import ActionProviderDescription
from globus_action_provider_tools.flask.apt_blueprint import ActionProviderBlueprint


@pytest.mark.parametrize("app_fixture", ["aptb_app", "add_routes_app"])
@pytest.mark.parametrize("api_version", ["1.0", "1.1"])
def test_routes_conform_to_api(
    request,
    app_fixture: str,
    api_version: str,
):
    app: Flask = request.getfixturevalue(app_fixture)
    client = app.test_client()
    _, bp = list(app.blueprints.items())[0]

    introspection_resp = ap_introspection(client, bp.url_prefix)
    assert introspection_resp.status_code == 200

    if api_version == "1.1":
        enumeration_resp = ap_enumeration(client, bp.url_prefix)
        assert enumeration_resp.status_code == 200

    run_resp = ap_run(client, bp.url_prefix, api_version=api_version)
    assert run_resp.status_code == 201

    action_id = run_resp.get_json()["action_id"]
    status_resp = ap_status(client, bp.url_prefix, action_id, api_version=api_version)
    assert status_resp.status_code == 200

    log_resp = ap_log(client, bp.url_prefix, action_id, api_version=api_version)
    assert log_resp.status_code == 200

    cancel_resp = ap_cancel(client, bp.url_prefix, action_id, api_version=api_version)
    assert cancel_resp.status_code == 200

    release_resp = ap_release(client, bp.url_prefix, action_id, api_version=api_version)
    assert release_resp.status_code == 200


def ap_introspection(client, url_prefix: str):
    return client.get(url_prefix)


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
        return client.post(f"{url_prefix}/actions/{action_id}/release")
