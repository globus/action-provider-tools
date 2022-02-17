import json
from time import time
from typing import Callable, List
from unittest.mock import Mock

from globus_sdk import BaseClient, GlobusHTTPResponse, OAuthDependentTokenResponse
from requests import Response

from globus_action_provider_tools.groups_client import GROUPS_SCOPE


class MockClient(BaseClient):
    service_name = "mock"


def resp(data, status_code=200):
    resp = Response()
    resp.status_code = status_code
    resp._content = json.dumps(data).encode("utf-8")
    resp.headers.update({"Content-Type": "application/json"})
    return resp


def groups_response() -> Callable[[], List]:
    return Mock(
        return_value=[
            {"id": "a34c9958-6bd2-11e3-b3ad-12313809f035"},
            {"id": "b0967b7a-312a-11e3-a9af-12313d2d6e7f"},
            {"id": "e489c9b8-7978-11e4-937b-123139141556"},
            {"id": "93e5926e-abee-11e4-b1f5-22000ab68755"},
            {"id": "8cfbd6b8-a47c-11e8-8e71-0a4677637dcc"},
            {"id": "05e1acce-a47d-11e8-b12f-0a4677637dcc"},
            {"id": "eae86240-a6d5-11e8-a980-0e5621afa498"},
            {"id": "cdd90ec0-7030-11e9-948c-0ef301d936cc"},
        ]
    )


def dependent_token_response() -> Callable[[], GlobusHTTPResponse]:
    return Mock(
        return_value=OAuthDependentTokenResponse(
            resp(
                [
                    {
                        "access_token": "ACCESS_TOKEN",
                        "expires_in": 172800,
                        "resource_server": "nexus.api.globus.org",
                        "token_type": "Bearer",
                        "scope": GROUPS_SCOPE,
                        "refresh_token": "REFRESH_TOKEN",
                    }
                ]
            ),
            client=MockClient(),
        )
    )


def introspect_response() -> Callable[[], GlobusHTTPResponse]:
    now = time()
    return Mock(
        return_value=GlobusHTTPResponse(
            resp(
                {
                    "username": mock_username(),
                    "dependent_tokens_cache_id": "CACHE_ID",
                    "token_type": "Bearer",
                    "client_id": mock_client_id(),
                    "scope": mock_scope(),
                    "active": True,
                    "nbf": now - 300,
                    "name": mock_username(),
                    "aud": [
                        "e6c75d97-532a-4c88-b031-8584a319fa3e",
                        "952d2aa2-aa0c-4d6e-ba1a-9d5fb131ec93",
                        "action_provider_tools_automated_tests",
                    ],
                    "identity_set": [
                        "ae2a1750-d274-11e5-b867-e74762c29f57",
                        "6e259134-032a-11e6-a68a-537f3952f25a",
                        "4984bc70-c0b7-11e5-9076-8b4826e7e700",
                        "ae2a64c6-d274-11e5-b868-2bbfe4b1a2b7",
                        "ca73e829-715f-4522-9dec-a507fe57a661",
                        "14bf3755-6267-42f2-9e9c-ad324de4a1fb",
                        mock_effective_identity(),
                    ],
                    "sub": mock_effective_identity(),
                    "iss": "https://auth.globus.org",
                    "exp": now + 3600,
                    "iat": now - 300,
                    "email": "brendan.mccollam+revalidate@gmail.com",
                }
            ),
            client=MockClient(),
        )
    )


def mock_scope():
    return "https://auth.globus.org/scopes/00000000-0000-0000-0000-000000000000/MOCK_SCOPE_SUFFIX"


def mock_username():
    return "MOCK_USERNAME"


def mock_client_id():
    return "11111111-1111-1111-1111-111111111111"


def mock_client_secret():
    return "MOCK_CLIENT_SECRET"


def mock_effective_identity() -> str:
    return "00000000-0000-0000-0000-000000000000"


def mock_expected_audience() -> str:
    return "action_provider_tools_automated_tests"
