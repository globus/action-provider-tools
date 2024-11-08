from __future__ import annotations

import typing as t
import uuid

import globus_sdk


class ClientFactory:
    """
    This helper defines methods which create relevant SDK client objects for use
    in an ActionProviderBlueprint and other contexts.

    The default implementation sets transport parameters on initialization.

    The client factory can be modified or replaced on an ActionProviderBlueprint
    in order to customize client construction.
    """

    DEFAULT_AUTH_TRANSPORT_PARAMS: tuple[tuple[str, t.Any], ...] = (
        ("http_timeout", 30),
        ("max_retries", 1),
        ("max_sleep", 5),
    )
    DEFAULT_GROUPS_TRANSPORT_PARAMS: tuple[tuple[str, t.Any], ...] = (
        ("http_timeout", 30),
        ("max_retries", 1),
        ("max_sleep", 5),
    )

    def make_confidential_app_auth_client(
        self, client_id: str | uuid.UUID, client_secret: str
    ) -> globus_sdk.ConfidentialAppAuthClient:
        return globus_sdk.ConfidentialAppAuthClient(
            client_id=client_id,
            client_secret=client_secret,
            transport_params=dict(self.DEFAULT_AUTH_TRANSPORT_PARAMS),
        )

    def make_groups_client(
        self,
        authorizer: (
            globus_sdk.AccessTokenAuthorizer | globus_sdk.RefreshTokenAuthorizer | None
        ),
    ) -> globus_sdk.GroupsClient:
        return globus_sdk.GroupsClient(
            authorizer=authorizer,
            transport_params=dict(self.DEFAULT_GROUPS_TRANSPORT_PARAMS),
        )
