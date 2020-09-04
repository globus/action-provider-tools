"""
This file contains basic tests to validate that our Action Provider is behaving
correctly.

When a Provider using the flask API helpers starts up, it internally creates an
instance of a TokenChecker.  The TokenChecker expects to have a valid CLIENT_ID and
CLIENT_SECRET. The patch imported below modifies the TokenChecker's behavior 
such that it does not care if the ActionProvider is tested with valid CLIENT 
credentials.

Depending on your ActionProvider's configuration, each request to an endpoint
will need to contain a Token authorizing access to the Provider. Again, the
token checker patch modifies the TokenChecker's behavior such that requests
without valid Tokens are accepted and acted upon.

These patches should ONLY be used during testing.
"""

import json
import uuid
from unittest.mock import MagicMock

import pytest

from examples.watchasay.app.provider import create_app, load_schema
from globus_action_provider_tools.data_types import ActionStatusValue
from globus_action_provider_tools.testing.patches import (
    flask_api_helpers_tokenchecker_patch,
)


@pytest.fixture(scope="module")
def client():
    # Create the app in a patched context so that the Provider can startup
    # without valid credentials AND requests can be made without supplying a
    # valid token
    with flask_api_helpers_tokenchecker_patch:
        app = create_app()
        app.config["TESTING"] = True
        yield app.test_client()


def test_introspection_endpoint(client):
    response = client.get("/skeleton")

    assert response.status_code == 200
    assert json.loads(response.data)["input_schema"] == load_schema()


def test_enumeration_endpoint(client):
    response = client.get("/skeleton/actions")
    assert response.status_code == 200


def test_run_endpoint(client):
    request_id = str(uuid.uuid4())
    data = {
        "request_id": request_id,
        "body": {"input_string": "Wh-wh-wh-what did you say?"},
    }
    response = client.post("/skeleton/run", data=json.dumps(data))

    assert response.status_code == 201
    assert json.loads(response.data)["status"] == ActionStatusValue.SUCCEEDED.name


def test_status_endpoint(client):
    request_id = str(uuid.uuid4())
    data = {
        "request_id": request_id,
        "body": {"input_string": "Wh-wh-wh-what did you say?"},
    }
    response = client.post("/skeleton/run", data=json.dumps(data))
    action_id = json.loads(response.data)["action_id"]
    response = client.get(f"/skeleton/{action_id}/status")

    assert response.status_code == 200
    assert json.loads(response.data)["status"] == ActionStatusValue.SUCCEEDED.name


def test_cancel_endpoint(client):
    request_id = str(uuid.uuid4())
    data = {
        "request_id": request_id,
        "body": {"input_string": "Wh-wh-wh-what did you say?"},
    }
    response = client.post("/skeleton/run", data=json.dumps(data))
    action_id = json.loads(response.data)["action_id"]

    # Cancels should always succeed since action is synchronous
    response = client.post(f"/skeleton/{action_id}/cancel")

    assert response.status_code == 200
    assert json.loads(response.data)["status"] == ActionStatusValue.SUCCEEDED.name


def test_release_endpoint(client):
    request_id = str(uuid.uuid4())
    data = {
        "request_id": request_id,
        "body": {"input_string": "Wh-wh-wh-what did you say?"},
    }
    response = client.post("/skeleton/run", data=json.dumps(data))
    action_id = json.loads(response.data)["action_id"]

    # Immediate release should succeed since action is synchronous
    response = client.post(f"/skeleton/{action_id}/release")

    assert response.status_code == 200
    assert json.loads(response.data)["status"] == ActionStatusValue.SUCCEEDED.name
