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
    data: Dict[str, Any], validator: jsonschema.protocols.Validator
) -> ValidationResult:
    # TODO: If python-jsonschema introduces a means of returning error messages that
    # do not include input data, modify this to return more specific error information.
    if not validator.is_valid(data):
        message = "Input failed schema validation"
        result = ValidationResult(errors=[message], error_msg=message)
    else:
        result = ValidationResult(errors=[], error_msg=None)

    return result
