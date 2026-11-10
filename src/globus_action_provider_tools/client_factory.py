from __future__ import annotations

import uuid

import globus_sdk
from globus_sdk.transport import RequestsTransport, RetryConfig


class ClientFactory:
    """
    This helper defines methods which create relevant SDK client objects for use
    in an ActionProviderBlueprint and other contexts.

    The default implementation sets transport parameters on initialization.

    The client factory can be modified or replaced on an ActionProviderBlueprint
    in order to customize client construction.
    """

    DEFAULT_TRANSPORT_TIMEOUT: float = 30
    DEFAULT_RETRY_CONFIG: RetryConfig = RetryConfig(max_retries=1, max_sleep=5)

    def make_confidential_app_auth_client(
        self, client_id: str | uuid.UUID, client_secret: str
    ) -> globus_sdk.ConfidentialAppAuthClient:
        return globus_sdk.ConfidentialAppAuthClient(
            client_id=client_id,
            client_secret=client_secret,
            transport=RequestsTransport(http_timeout=self.DEFAULT_TRANSPORT_TIMEOUT),
            retry_config=self.DEFAULT_RETRY_CONFIG,
        )

    def make_groups_client(
        self,
        authorizer: (
            globus_sdk.AccessTokenAuthorizer | globus_sdk.RefreshTokenAuthorizer | None
        ),
    ) -> globus_sdk.GroupsClient:
        return globus_sdk.GroupsClient(
            authorizer=authorizer,
            transport=RequestsTransport(http_timeout=self.DEFAULT_TRANSPORT_TIMEOUT),
            retry_config=self.DEFAULT_RETRY_CONFIG,
        )
