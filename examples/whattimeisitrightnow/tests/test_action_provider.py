"""
This file contains basic tests to validate that our Action Provider is behaving
correctly.

When the Provider starts up, it will internally create an instance of a
TokenChecker. The TokenChecker expects to be provided a valid CLIENT_ID and
CLIENT_SECRET.  The import patch (see below) modifies the TokenChecker's
behavior such that it does not care if the ActionProvider is tested with valid
CLIENT credentials.

Depending on your ActionProvider's configuration, each request to an endpoint
will need to contain a Token authorizing access to the Provider. Again, the
token checker patch modifies the TokenChecker's behavior such that requests
without valid Tokens are accepted and acted upon.

These patches should ONLY be used during testing.
"""

import json
import uuid
from unittest import mock

import pytest

from globus_action_provider_tools.data_types import ActionStatusValue
from globus_action_provider_tools.testing.mocks import mock_authstate

# This is how you mock away the need to provide a valid CLIENT_ID and
# CLIENT_SECRET for your ActionProvider during testing. Without the patch
# the Provider will not start. Note how the entire class gets patched
with mock.patch(
    "globus_action_provider_tools.authentication.TokenChecker.check_token",
    return_value=mock_authstate(),
) as patched_check_token:
    from examples.flask.whattimeisitrightnow.app.app import app, schema


@pytest.fixture
def client():
    app.config["TESTING"] = True
    yield app.test_client()


def test_introspection_endpoint(client):
    response = client.get("/")

    assert response.status_code == 200
    assert json.loads(response.data)["input_schema"] == schema


def test_run_endpoint(client):
    request_id = str(uuid.uuid4())
    data = {"request_id": request_id, "body": {"utc_offset": 1}}
    response = client.post("/run", data=json.dumps(data))

    assert response.status_code == 202
    assert json.loads(response.data)["status"] == ActionStatusValue.ACTIVE.name


def test_status_endpoint(client):
    request_id = str(uuid.uuid4())
    data = {"request_id": request_id, "body": {"utc_offset": 1}}
    response = client.post("/run", data=json.dumps(data))
    action_id = json.loads(response.data)["action_id"]
    response = client.get(f"/{action_id}/status")

    assert response.status_code == 200
    assert json.loads(response.data)["status"] == ActionStatusValue.ACTIVE.name


def test_cancel_endpoint(client):
    request_id = str(uuid.uuid4())
    data = {"request_id": request_id, "body": {"utc_offset": 1}}
    response = client.post("/run", data=json.dumps(data))
    action_id = json.loads(response.data)["action_id"]
    response = client.post(f"/{action_id}/cancel")

    assert response.status_code == 200
    assert json.loads(response.data)["status"] == ActionStatusValue.FAILED.name

    # Try re-cancelling the same action, expecting an error to occur
    response = client.post(f"/{action_id}/cancel")
    assert response.status_code == 409


def test_release_endpoint(client):
    request_id = str(uuid.uuid4())
    data = {"request_id": request_id, "body": {"utc_offset": 1}}
    response = client.post("/run", data=json.dumps(data))
    action_id = json.loads(response.data)["action_id"]

    # A release before a cancel should fail
    response = client.post(f"/{action_id}/release")
    assert response.status_code == 409

    # Cancel and then release should succeed
    client.post(f"/{action_id}/cancel")
    response = client.post(f"/{action_id}/release")

    assert response.status_code == 200
    assert json.loads(response.data)["status"] == ActionStatusValue.FAILED.name
