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

from .ap_client import ActionProviderClient
from .app_utils import (
    ActionProviderPydanticInputSchema,
    action_provider_json_input_schema,
)


@pytest.mark.parametrize("api_version", ["1.0", "1.1"])
@pytest.mark.parametrize("use_pydantic_schema", [True, False])
def test_routes_conform_to_api(
    introspect_success_response,
    request,
    aptb_app,
    api_version: str,
    use_pydantic_schema: bool,
):
    _, bp = list(aptb_app.blueprints.items())[0]
    if use_pydantic_schema:
        bp.input_schema = ActionProviderPydanticInputSchema
    else:
        bp.input_schema = action_provider_json_input_schema

    client = ActionProviderClient(
        aptb_app.test_client(), bp.url_prefix, api_version=api_version
    )

    introspect_resp = client.introspect()
    assert list(introspect_resp.access_control_allow_origin) == ["*"]
    client.enumerate()
    action_id = client.run().get_json()["action_id"]
    client.status(action_id)
    client.log(action_id)
    client.cancel(action_id)
    client.release(action_id)


def test_introspect_cors_requests(request, aptb_app):
    """Verify that CORS requests are allowed on introspect routes."""

    client: flask.testing.FlaskClient = aptb_app.test_client()
    _, bp = list(aptb_app.blueprints.items())[0]

    introspection_cors_response = client.options(bp.url_prefix)
    assert introspection_cors_response.status_code == 204

    # Verify the values of each header.
    assert list(introspection_cors_response.access_control_allow_methods) == [
        "GET",
        "OPTIONS",
    ]
    assert list(introspection_cors_response.access_control_allow_origin) == ["*"]
    assert list(introspection_cors_response.access_control_expose_headers) == ["*"]
