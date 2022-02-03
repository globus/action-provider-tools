import uuid

import pytest

from examples.apt_blueprint.app import create_app
from examples.apt_blueprint.blueprint import aptb, description
from globus_action_provider_tools.data_types import ActionStatusValue
from globus_action_provider_tools.testing.fixtures import apt_blueprint_noauth


@pytest.fixture(scope="module")
def client(apt_blueprint_noauth):
    # Patch the blueprint BEFORE attaching it to an app so that the Provider can
    # start without valid credentials AND requests can be made without supplying
    # a valid token
    apt_blueprint_noauth(aptb)
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
    response = client.get("/apt/")

    assert response.status_code == 200
    assert response.json["input_schema"] == description.input_schema.schema()


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

    assert response.status_code == 202
    assert response.json["status"] == ActionStatusValue.ACTIVE


def test_status_endpoint(client, running_action_id):
    response = client.get(f"/apt/{running_action_id}/status")

    assert response.status_code == 200
    assert response.json["status"] == ActionStatusValue.ACTIVE


def test_cancel_endpoint(client, running_action_id):
    response = client.post(f"/apt/{running_action_id}/cancel")

    assert response.status_code == 200
    assert response.json["status"] == ActionStatusValue.FAILED


def test_release_endpoint(client, running_action_id):
    # Cancel before releasing since our action is asynchronous
    response = client.post(f"/apt/{running_action_id}/cancel")
    response = client.post(f"/apt/{running_action_id}/release")

    assert response.status_code == 200
    assert response.json["status"] == ActionStatusValue.FAILED
