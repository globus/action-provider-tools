import typing as t
from unittest import mock

import pytest
from pydantic import BaseModel

from globus_action_provider_tools.authentication import InactiveTokenError
from globus_action_provider_tools.flask import (
    ActionProviderBlueprint,
    ActionProviderConfig,
)
from globus_action_provider_tools.flask.helpers import FlaskAuthStateBuilder
from tests.flask.ap_client import ActionProviderClient
from tests.flask.app_utils import ap_description


class _ScalarPydanticModel(BaseModel):
    foo: int


class _NestedPydanticModel(BaseModel):
    outer: t.List[_ScalarPydanticModel]


_SCALAR_JSONSCHEMA_MODEL = {"properties": {"foo": {"type": "integer"}}}

_NESTED_JSONSCHEMA_MODEL = {
    "properties": {"outer": {"items": _SCALAR_JSONSCHEMA_MODEL}}
}


@pytest.mark.parametrize(
    "input_schema,request_body,expected",
    (
        # Simple Scalar Models - input is mistyped (expects int, gets str)
        (
            _ScalarPydanticModel,
            {"foo": "not-an-int"},
            (
                "Field '$.foo' (category: 'type_error.integer'): "
                "value is not a valid integer"
            ),
        ),
        (
            _SCALAR_JSONSCHEMA_MODEL,
            {"foo": "not-an-int"},
            "Field '$.foo' (category: 'type'): Input failed schema validation",
        ),
        # More complex models - nested input is mistyped (expects int, gets str)
        (
            _NestedPydanticModel,
            {"outer": [{"foo": "not-an-int"}]},
            (
                "Field '$.outer[0].foo' (category: 'type_error.integer'): "
                "value is not a valid integer"
            ),
        ),
        (
            _NESTED_JSONSCHEMA_MODEL,
            {"outer": [{"foo": "not-an-int"}]},
            "Field '$.outer[0].foo' (category: 'type'): Input failed schema validation",
        ),
    ),
)
def test_validation_errors(
    input_schema, request_body, expected, create_app_from_blueprint
):
    mutable_ap_description = ap_description.copy()
    mutable_ap_description.input_schema = input_schema

    blueprint = ActionProviderBlueprint(
        name="TestBlueprint",
        import_name=__name__,
        url_prefix="/my_cool_ap",
        provider_description=mutable_ap_description,
    )
    app = create_app_from_blueprint(blueprint)
    client = ActionProviderClient(app.test_client(), blueprint.url_prefix)

    resp = client.run(body=request_body, assert_status=422)

    assert resp.json["description"] == expected


def test_validation_errors__WHEN_scrubbing_is_disabled(create_app_from_blueprint):
    mutable_ap_description = ap_description.copy()
    mutable_ap_description.input_schema = {"properties": {"foo": {"type": "integer"}}}

    blueprint = ActionProviderBlueprint(
        name="TestBlueprint",
        import_name=__name__,
        url_prefix="/my_cool_ap",
        provider_description=mutable_ap_description,
        config=ActionProviderConfig(scrub_validation_errors=False),
    )
    app = create_app_from_blueprint(blueprint)
    client = ActionProviderClient(app.test_client(), blueprint.url_prefix)

    resp = client.run(body={"foo": "not-an-int"}, assert_status=422)

    expected = "Field '$.foo' (category: 'type'): 'not-an-int' is not of type 'integer'"
    assert resp.json["description"] == expected


def test_invalid_token_results_in_401_unauthorized(create_app_from_blueprint):
    blueprint = ActionProviderBlueprint(
        name="TestBlueprint",
        import_name=__name__,
        url_prefix="/my_cool_ap",
        provider_description=ap_description,
    )
    app = create_app_from_blueprint(blueprint)
    client = ActionProviderClient(app.test_client(), blueprint.url_prefix)

    # create a dummy builder but ensure the real class is used
    # (`create_app_from_blueprint` mocks over this)
    #
    # instead, inject an error when an AuthState is being constructed
    # narrowly, this just needs to be during the init-time call to introspect_token
    blueprint.state_builder = FlaskAuthStateBuilder(mock.Mock(), ("foo-scope",))
    with mock.patch(
        "globus_action_provider_tools.authentication.AuthState.introspect_token",
        side_effect=InactiveTokenError("token wuz bad"),
    ):
        resp = client.run(
            body={"echo_string": "hello badly authenticated world"}, assert_status=401
        )

    # confirm that the customized 401 renders as desired as JSON
    assert resp.json["code"] == "UnauthorizedRequest"
    assert resp.json["description"] == (
        "The server could not verify that you are authorized "
        "to access the URL requested."
    )
