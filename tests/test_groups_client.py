import pytest
from globus_sdk import AccessTokenAuthorizer

from globus_action_provider_tools.groups_client import GroupsClient

SDK_ENVS = ["production", "integration", "test", "sandbox"]


@pytest.mark.parametrize("sdk_env", SDK_ENVS)
def test_create_groups_client(monkeypatch, sdk_env: str):
    monkeypatch.setenv("GLOBUS_SDK_ENVIRONMENT", sdk_env)
    gc = GroupsClient(authorizer=AccessTokenAuthorizer("fake token"))
    assert gc.service_name == "groups"
    assert gc.environment == sdk_env
    if sdk_env == "production":
        assert gc.base_url == "https://groups.api.globus.org/v2/"
    else:
        assert gc.base_url == f"https://groups.api.{sdk_env}.globuscs.info/v2/"
