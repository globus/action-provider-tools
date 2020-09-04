import json
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


def test_introspection_endpoint(client):
    response = client.get("/apt")

    assert response.status_code == 200
    assert json.loads(response.data)["input_schema"] == description.input_schema


def test_enumeration_endpoint(client):
    response = client.get("/apt/actions")
    print(response.data)
    assert response.status_code == 200


def test_run_endpoint(client):
    request_id = str(uuid.uuid4())
    data = {
        "request_id": request_id,
        "body": {"utc_offset": "1"},
    }
    response = client.post("/apt/run", data=json.dumps(data))

    assert response.status_code == 201
    assert json.loads(response.data)["status"] == ActionStatusValue.ACTIVE.name


def test_status_endpoint(client):
    request_id = str(uuid.uuid4())
    data = {
        "request_id": request_id,
        "body": {"utc_offset": "1"},
    }
    response = client.post("/apt/run", data=json.dumps(data))
    action_id = json.loads(response.data)["action_id"]
    response = client.get(f"/apt/{action_id}/status")

    assert response.status_code == 200
    assert json.loads(response.data)["status"] == ActionStatusValue.ACTIVE.name


def test_cancel_endpoint(client):
    request_id = str(uuid.uuid4())
    data = {
        "request_id": request_id,
        "body": {"utc_offset": "1"},
    }
    response = client.post("/apt/run", data=json.dumps(data))
    action_id = json.loads(response.data)["action_id"]

    response = client.post(f"/apt/{action_id}/cancel")

    assert response.status_code == 200
    assert json.loads(response.data)["status"] == ActionStatusValue.FAILED.name


def test_release_endpoint(client):
    request_id = str(uuid.uuid4())
    data = {
        "request_id": request_id,
        "body": {"utc_offset": "1"},
    }
    response = client.post("/apt/run", data=json.dumps(data))
    action_id = json.loads(response.data)["action_id"]

    # Cancel before releasing since our action is asynchronous
    response = client.post(f"/apt/{action_id}/cancel")
    response = client.post(f"/apt/{action_id}/release")

    assert response.status_code == 200
    assert json.loads(response.data)["status"] == ActionStatusValue.FAILED.name
