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
import uuid

import pytest

from examples.watchasay.app.provider import create_app, load_schema
from globus_action_provider_tools.data_types import ActionStatusValue
from globus_action_provider_tools.testing.fixtures import flask_helpers_noauth


@pytest.fixture
def client(flask_helpers_noauth):
    # Patch the app using the flask_helpers_noauth fixture so that the Provider
    # can start up without valid credentials AND requests can be made without
    # supplying a valid token
    app = create_app()
    app.config["TESTING"] = True
    yield app.test_client()


@pytest.fixture(scope="function")
def running_action_id(client):
    data = {
        "request_id": str(uuid.uuid4()),
        "body": {"input_string": "Wh-wh-wh-what did you say?"},
    }
    response = client.post("/skeleton/run", json=data)
    return response.json["action_id"]


def test_introspection_endpoint(client):
    response = client.get("/skeleton")

    assert response.status_code == 200
    assert response.json["input_schema"] == load_schema()


def test_enumeration_endpoint(client, running_action_id):
    data = {"status": "ACTIVE,INACTIVE,Failed,Succeeded"}
    response = client.get("/skeleton/actions", query_string=data)
    assert response.status_code == 200
    assert len(response.json) == 1


def test_run_endpoint(client):
    data = {
        "request_id": str(uuid.uuid4()),
        "body": {"input_string": "Wh-wh-wh-what did you say?"},
    }
    response = client.post("/skeleton/run", json=data)

    assert response.status_code == 202
    assert response.json["status"] == ActionStatusValue.SUCCEEDED


def test_status_endpoint(client, running_action_id):
    response = client.get(f"/skeleton/{running_action_id}/status")

    assert response.status_code == 200
    assert response.json["status"] == ActionStatusValue.SUCCEEDED


def test_cancel_endpoint(client, running_action_id):
    # Cancels should always succeed since action is synchronous
    response = client.post(f"/skeleton/{running_action_id}/cancel")

    assert response.status_code == 200
    assert response.json["status"] == ActionStatusValue.SUCCEEDED


def test_release_endpoint(client, running_action_id):
    # Immediate release should succeed since action is synchronous
    response = client.post(f"/skeleton/{running_action_id}/release")

    assert response.status_code == 200
    assert response.json["status"] == ActionStatusValue.SUCCEEDED
