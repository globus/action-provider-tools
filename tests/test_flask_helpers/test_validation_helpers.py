"""
This module tests some of the shared validation functions in the Flask helpers.
"""
import json

import pytest
from jsonschema.validators import Draft7Validator

from globus_action_provider_tools.flask.exceptions import (
    ActionProviderError,
    BadActionRequest,
)
from globus_action_provider_tools.flask.helpers import (
    get_input_body_validator,
    json_schema_input_validation,
    pydantic_input_validation,
    validate_input,
)

from .app_utils import (
    ActionProviderPydanticInputSchema,
    action_provider_json_input_schema,
    ap_description,
)


def test_can_get_validator_for_str_input_schema():
    ap_description.input_schema = json.dumps(action_provider_json_input_schema)
    validator = get_input_body_validator(ap_description)
    assert validator is not None
    assert validator.func is json_schema_input_validation


def test_can_get_validator_for_dict_input_schema():
    ap_description.input_schema = action_provider_json_input_schema
    validator = get_input_body_validator(ap_description)
    assert validator is not None
    assert validator.func is json_schema_input_validation


def test_can_get_validator_for_pydantic_input_schema():
    ap_description.input_schema = ActionProviderPydanticInputSchema
    validator = get_input_body_validator(ap_description)
    assert validator is not None
    assert validator.func is pydantic_input_validation


def test_exception_on_invalid_input_schema():
    ap_description.input_schema = None

    with pytest.raises(ActionProviderError):
        get_input_body_validator(ap_description)


def test_passing_json_schema_validation():
    validator = Draft7Validator(action_provider_json_input_schema)
    data_in = {"echo_string": "hello"}
    json_schema_input_validation(data_in, validator)


def test_failing_json_schema_validation():
    validator = Draft7Validator(action_provider_json_input_schema)
    with pytest.raises(BadActionRequest):
        json_schema_input_validation({}, validator)


def test_passing_pydantic_validation():
    data_in = {"echo_string": "hello"}
    pydantic_input_validation(data_in, ActionProviderPydanticInputSchema)


def test_failing_pydantic_validation():
    with pytest.raises(BadActionRequest):
        pydantic_input_validation({}, ActionProviderPydanticInputSchema)


def test_validating_malformed_action_request():
    ap_description.input_schema = json.dumps(action_provider_json_input_schema)
    validator = get_input_body_validator(ap_description)
    with pytest.raises(BadActionRequest):
        validate_input({}, validator)


def test_validating_action_request():
    ap_description.input_schema = {}
    validator = get_input_body_validator(ap_description)
    validate_input({"request_id": 100, "body": {}}, validator)


def test_validate_input_typeerror():
    """Verify that a non-object `request_json` argument results in HTTP 400."""

    ap_description.input_schema = json.dumps(action_provider_json_input_schema)
    validator = get_input_body_validator(ap_description)
    with pytest.raises(BadActionRequest) as catcher:
        validate_input("{}", validator)  # type: ignore
    expected = [
        {
            "loc": [""],
            "msg": "json document must be an object",
            "type": "value_error",
        }
    ]
    assert catcher.value.get_response().status_code == 400
    assert catcher.value.get_description() == expected
