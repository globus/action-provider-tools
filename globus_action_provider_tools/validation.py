import logging
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional

import jsonschema
import yaml

log = logging.getLogger(__name__)

_schema_to_file_map = {
    "ActionRequest": "action_request.yaml",
    "ActionStatus": "action_status.yaml",
}
_validator_map: Dict[str, jsonschema.protocols.Validator] = {}

HERE: Path = Path(__file__).parent
for schema_name, yaml_file in _schema_to_file_map.items():
    with open(HERE / yaml_file, encoding="utf-8") as specfile:
        schema = yaml.safe_load(specfile)
        validator_cls = jsonschema.validators.validator_for(schema)
        _validator_map[schema_name] = validator_cls(schema)


class ValidationRequest(NamedTuple):
    provider_doc_type: str
    request_data: Dict[str, Any]


class ValidationResult(NamedTuple):
    errors: List[str]
    error_msg: Optional[str]


def request_validator(request: ValidationRequest) -> ValidationResult:
    schema_ = _validator_map.get(request.provider_doc_type)
    if schema_ is None:
        log.warning(f"Unable to validate document of type {request.provider_doc_type}")
        return ValidationResult(errors=[], error_msg=None)
    return validate_data(request.request_data, schema_)


response_validator = request_validator


def validate_data(
    data: Dict[str, Any],
    validator: jsonschema.protocols.Validator,
    validation_error_obscuring: bool = True,
) -> ValidationResult:
    if validation_error_obscuring:
        return _validate_data_omitting_request_data(data, validator)
    else:
        return _validate_data_allowing_request_data(data, validator)


def _validate_data_allowing_request_data(
    data: Dict[str, Any], validator: jsonschema.protocols.Validator
) -> ValidationResult:

    error_messages = []
    for error in validator.iter_errors(data):
        if error.path:
            # Elements of the error path may be integers or other non-string types,
            # but we need strings for use with join()
            error_path_for_message = ".".join([str(x) for x in error.path])
            error_message = f"'{error_path_for_message}' invalid due to {error.message}"
        else:
            error_message = error.message
        error_messages.append(error_message)

    error_msg = "; ".join(error_messages) if error_messages else None
    return ValidationResult(errors=error_messages, error_msg=error_msg)


def _validate_data_omitting_request_data(
    data: Dict[str, Any], validator: jsonschema.protocols.Validator
) -> ValidationResult:
    # TODO: If python-jsonschema introduces a means of returning error messages that
    #  do not include input data, modify this to return more specific error information.
    if not validator.is_valid(data):
        message = "Input failed schema validation"
        return ValidationResult(errors=[message], error_msg=message)
    else:
        return ValidationResult(errors=[], error_msg=None)
