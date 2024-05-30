import pytest

from globus_action_provider_tools.flask import (
    ActionProviderBlueprint,
    ActionProviderConfig,
)
from tests.test_flask_helpers.ap_client import ActionProviderClient
from tests.test_flask_helpers.app_utils import ap_description


@pytest.mark.parametrize(
    "validation_error_obscuring,error_message",
    (
        (False, "'foo' invalid due to 'not-an-int' is not of type 'integer'"),
        (True, "Input failed schema validation"),
    ),
)
def test_blueprint_config_informs_validation_error_obscuring_in_jsonschema_errors(
    create_app_from_blueprint, validation_error_obscuring, error_message
):
    mutable_ap_description = ap_description.copy()
    mutable_ap_description.input_schema = {
        "type": "object",
        "properties": {"foo": {"type": "integer"}},
    }

    blueprint = ActionProviderBlueprint(
        name="TestBlueprint",
        import_name=__name__,
        url_prefix="/my_cool_ap",
        provider_description=mutable_ap_description,
        config=ActionProviderConfig(
            validation_error_obscuring=validation_error_obscuring
        ),
    )
    app = create_app_from_blueprint(blueprint)

    client = ActionProviderClient(app.test_client(), blueprint.url_prefix)

    resp = client.run(
        payload={"request_id": 0, "body": {"foo": "not-an-int"}}, assert_status=422
    )
    assert resp.json["description"] == error_message
