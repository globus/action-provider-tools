import typing as t

import pytest
from pydantic import BaseModel

from globus_action_provider_tools.flask import (
    ActionProviderBlueprint,
    ActionProviderConfig,
)
from tests.test_flask_helpers.ap_client import ActionProviderClient
from tests.test_flask_helpers.app_utils import ap_description


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
        config=ActionProviderConfig(scrubbed_validation_errors=False),
    )
    app = create_app_from_blueprint(blueprint)
    client = ActionProviderClient(app.test_client(), blueprint.url_prefix)

    resp = client.run(body={"foo": "not-an-int"}, assert_status=422)

    expected = "Field '$.foo' (category: 'type'): 'not-an-int' is not of type 'integer'"
    assert resp.json["description"] == expected
