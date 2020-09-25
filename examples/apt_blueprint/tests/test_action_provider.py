import uuid

import pytest

from examples.apt_blueprint.app import create_app
from examples.apt_blueprint.blueprint import description
from globus_action_provider_tools.data_types import ActionStatusValue
from globus_action_provider_tools.testing.patches import (
    flask_blueprint_tokenchecker_patch,
)


@pytest.fixture(scope="module")
def client():
    # Create the app in a patched context so that the Provider can startup
    # without valid credentials AND requests can be made without supplying a
    # valid token
    with flask_blueprint_tokenchecker_patch:
        app = create_app()
        yield app.test_client()


@pytest.fixture(scope="function")
def running_action_id(client):
    data = {
        "request_id": str(uuid.uuid4()),
        "body": {"utc_offset": "1"},
    }
    response = client.post("/apt/run", json=data)
    return response.json["action_id"]


def test_introspection_endpoint(client):
    response = client.get("/apt")

    assert response.status_code == 200
    assert response.json["input_schema"] == description.input_schema


def test_enumeration_endpoint(client):
    response = client.get("/apt/actions")
    assert response.status_code == 200


def test_run_endpoint(client):
    request_id = str(uuid.uuid4())
    data = {
        "request_id": request_id,
        "body": {"utc_offset": "1"},
    }
    response = client.post("/apt/run", json=data)

    assert response.status_code == 201
    assert response.json["status"] == ActionStatusValue.ACTIVE.name


def test_status_endpoint(client, running_action_id):
    response = client.get(f"/apt/{running_action_id}/status")

    assert response.status_code == 200
    assert response.json["status"] == ActionStatusValue.ACTIVE.name


def test_cancel_endpoint(client, running_action_id):
    response = client.post(f"/apt/{running_action_id}/cancel")

    assert response.status_code == 200
    assert response.json["status"] == ActionStatusValue.FAILED.name


def test_release_endpoint(client, running_action_id):
    # Cancel before releasing since our action is asynchronous
    response = client.post(f"/apt/{running_action_id}/cancel")
    response = client.post(f"/apt/{running_action_id}/release")

    assert response.status_code == 200
    assert response.json["status"] == ActionStatusValue.FAILED.name
