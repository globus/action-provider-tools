import logging
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional

import yaml
from jsonschema.validators import Draft7Validator

log = logging.getLogger(__name__)

_schema_to_file_map = {
    "ActionRequest": "action_request.yaml",
    "ActionStatus": "action_status.yaml",
}
_validator_map: Dict[str, Draft7Validator] = {}

HERE: Path = Path(__file__).parent
for schema_name, yaml_file in _schema_to_file_map.items():
    with open(HERE / yaml_file, "r", encoding="utf-8") as specfile:
        jsonschema = yaml.safe_load(specfile)
        _validator_map[schema_name] = Draft7Validator(jsonschema)


class ValidationRequest(NamedTuple):
    provider_doc_type: str
    request_data: Dict[str, Any]


class ValidationResult(NamedTuple):
    errors: List[str]
    error_msg: Optional[str]


def request_validator(request: ValidationRequest) -> ValidationResult:
    schema = _validator_map.get(request.provider_doc_type)
    if schema is None:
        log.warn(f"Unable to validate document of type {request.provider_doc_type}")
        return ValidationResult(errors=[], error_msg=None)
    return validate_data(request.request_data, schema)


response_validator = request_validator


def validate_data(data: Dict[str, Any], validator: Draft7Validator) -> ValidationResult:
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
    result = ValidationResult(errors=error_messages, error_msg=error_msg)
    return result
