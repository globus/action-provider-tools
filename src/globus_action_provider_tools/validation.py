from __future__ import annotations

import logging
import typing as t
from pathlib import Path

import yaml
from jsonschema.exceptions import ValidationError
from jsonschema.protocols import Validator
from jsonschema.validators import validator_for

log = logging.getLogger(__name__)

_schema_to_file_map = {
    "ActionRequest": "action_request.yaml",
    "ActionStatus": "action_status.yaml",
}
_validator_map: dict[str, Validator] = {}

HERE: Path = Path(__file__).parent
for schema_name, yaml_file in _schema_to_file_map.items():
    with open(HERE / yaml_file, encoding="utf-8") as specfile:
        schema = yaml.safe_load(specfile)
        validator_cls = validator_for(schema)
        _validator_map[schema_name] = validator_cls(schema)


class ValidationRequest(t.NamedTuple):
    provider_doc_type: str
    request_data: dict[str, t.Any]


class ValidationResult(t.NamedTuple):
    errors: list[str]
    error_msg: str | None


def request_validator(request: ValidationRequest) -> ValidationResult:
    schema_ = _validator_map.get(request.provider_doc_type)
    if schema_ is None:
        log.warning(f"Unable to validate document of type {request.provider_doc_type}")
        return ValidationResult(errors=[], error_msg=None)
    return validate_data(request.request_data, schema_)


response_validator = request_validator


def validate_data(
    data: dict[str, t.Any],
    validator: Validator,
    scrub_validation_errors: bool = True,
) -> ValidationResult:
    """
    :param data: A Dictionary of data to validate
    :param validator: A JSONSchema validator
    :param scrub_user_data: Whether to scrub user data from validation errors
    :return: A ValidationResult object
    """
    error_messages = [
        _format_jsonschema_error(err, scrub_validation_errors)
        for err in validator.iter_errors(data)
    ]
    error_msg = "; ".join(error_messages) if error_messages else None

    return ValidationResult(errors=error_messages, error_msg=error_msg)


def _format_jsonschema_error(
    error: ValidationError, scrub_validation_errors: bool
) -> str:
    error_message = None if scrub_validation_errors else error.message
    category = str(error.validator)

    return format_validation_error(error.json_path, category, error_message)


def format_validation_error(
    jsonpath: str, category: str, message: str | None = None
) -> str:
    """
    Format a validation error message for a specific field in a JSON document.

    This method mostly exists to standardize the formatting of errors across different
    schema languages.
    """
    message = message or "Input failed schema validation"
    return f"Field '{jsonpath}' (category: '{category}'): {message}"
