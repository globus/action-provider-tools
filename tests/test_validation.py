from globus_action_provider_tools.validation import ValidationRequest, request_validator


def test_valid_action_request():
    valid_payload = {
        "request_id": "1234",
        "label": "My action",
        "body": {"custom": "anything goes here", "value": False},
        "manage_by": [
            "urn:globus:auth:identity:ca73e829-715f-4522-9dec-a507fe57a661",
            "urn:globus:auth:identity:ae2a1750-d274-11e5-b867-e74762c29f57",
        ],
        "monitor_by": [
            "urn:globus:auth:identity:ca73e829-715f-4522-9dec-a507fe57a661",
            "urn:globus:auth:identity:ae2a1750-d274-11e5-b867-e74762c29f57",
        ],
        "allowed_clients": ["public"],
        "deadline": "2019-06-21T17:01:55.806781+00:00",
        "release_after": "P30D",
    }
    valid_request = ValidationRequest(
        request_data=valid_payload, provider_doc_type="ActionRequest"
    )
    result = request_validator(valid_request)
    assert not result.errors, result.error_msg


def test_invalid_action_request():
    # invalid_payload is missing the request_id
    invalid_payload = {"body": {"custom": "anything goes here", "value": False}}
    invalid_request = ValidationRequest(
        request_data=invalid_payload, provider_doc_type="ActionRequest"
    )
    result = request_validator(invalid_request)
    assert result.errors, result.error_msg


def test_invalid_action_response():
    # invalid_payload is missing the creator_id
    invalid_payload = {
        "action_id": "zyx098",
        "label": "My action",
        "status": "ACTIVE",
        "details": {"is_purple": True},
        "start_time": "1985-10-17 09:04:42+00:00",
        "release_after": "P30D",
    }
    invalid_request = ValidationRequest(
        request_data=invalid_payload, provider_doc_type="ActionStatus"
    )
    result = request_validator(invalid_request)
    assert result.errors, result.error_msg


def test_valid_action_response():
    valid_payload = {
        "action_id": "6529",
        "status": "ACTIVE",
        "creator_id": "urn:globus:auth:identity:ae2a1750-d274-11e5-b867-e74762c29f57",
        "label": "some label",
        "monitor_by": [
            "urn:globus:auth:identity:ca73e829-715f-4522-9dec-a507fe57a661",
            "urn:globus:auth:identity:ae2a1750-d274-11e5-b867-e74762c29f57",
        ],
        "manage_by": [
            "urn:globus:auth:identity:ca73e829-715f-4522-9dec-a507fe57a661",
            "urn:globus:auth:identity:ae2a1750-d274-11e5-b867-e74762c29f57",
        ],
        "start_time": "2019-06-21T17:01:55.806781+00:00",
        "completion_time": "2019-06-21T17:01:55.806781+00:00",
        "release_after": "P30D",
        "display_status": "OK",
        "details": {"estimated_complete": "2019-06-21T17:15:04.805868+00:00"},
    }
    valid_request = ValidationRequest(
        request_data=valid_payload, provider_doc_type="ActionStatus"
    )
    result = request_validator(valid_request)
    assert not result.errors, result.error_msg
