from __future__ import annotations

import typing as t

import pytest
from flask.testing import FlaskClient
from werkzeug import Response

_BEARER_AUTHORIZATION = [("Authorization", "Bearer fake-access-token")]


class ActionProviderClient:

    def __init__(self, client: FlaskClient, url_prefix: str, api_version: str = "1.0"):
        self._client = client
        self._url_prefix = url_prefix
        self._api_version = api_version

    def introspect(self, assert_status: int | list[int] = 200, **kwargs) -> Response:
        # Explicitly set headers to the empty list to avoid sending Authorization header
        kwargs["headers"] = kwargs.get("headers", [])
        return self.get("/", assert_status=assert_status, **kwargs)

    def enumerate(self, assert_status: int | list[int] = 200, **kwargs) -> Response:
        return self.get("/actions", assert_status=assert_status, **kwargs)

    def run(
        self,
        payload: t.Dict[str, t.Any] | None = None,
        assert_status: int | list[int] = 202,
        **kwargs,
    ) -> Response:
        if payload is None:
            payload = {"request_id": "0", "body": {"echo_string": "This is a test"}}

        route = "/actions" if self._api_version == "1.1" else "/run"
        return self.post(route, assert_status=assert_status, json=payload, **kwargs)

    def status(
        self, action_id: str, assert_status: int | list[int] = 200, **kwargs
    ) -> Response:
        route = f"/{action_id}/status"
        if self._api_version == "1.1":
            route = f"/actions/{action_id}"

        return self.get(route, assert_status=assert_status, **kwargs)

    def log(
        self, action_id: str, assert_status: int | list[int] = 200, **kwargs
    ) -> Response:
        route = f"/{action_id}/log"
        if self._api_version == "1.1":
            route = f"/actions/{action_id}/log"

        return self.get(route, assert_status=assert_status, **kwargs)

    def cancel(
        self, action_id: str, assert_status: int | list[int] = 200, **kwargs
    ) -> Response:
        route = f"/{action_id}/cancel"
        if self._api_version == "1.1":
            route = f"/actions/{action_id}/cancel"

        return self.post(route, assert_status=assert_status, **kwargs)

    def release(
        self, action_id: str, assert_status: int | list[int] = 200, **kwargs
    ) -> Response:
        if self._api_version == "1.1":
            return self.delete(
                f"/actions/{action_id}", assert_status=assert_status, **kwargs
            )
        else:
            return self.post(
                f"/{action_id}/release", assert_status=assert_status, **kwargs
            )

    def get(
        self, path: str, assert_status: int | list[int], *args, **kwargs
    ) -> Response:
        return self.request(path, "GET", assert_status, *args, **kwargs)

    def post(
        self, path: str, assert_status: int | list[int], *args, **kwargs
    ) -> Response:
        return self.request(path, "POST", assert_status, *args, **kwargs)

    def put(
        self, path: str, assert_status: int | list[int], *args, **kwargs
    ) -> Response:
        return self.request(path, "PUT", assert_status, *args, **kwargs)

    def delete(
        self, path: str, assert_status: int | list[int], *args, **kwargs
    ) -> Response:
        return self.request(path, "DELETE", assert_status, *args, **kwargs)

    def request(
        self, path: str, method: str, assert_status: int | list[int], *args, **kwargs
    ) -> Response:
        headers = kwargs.pop("headers", _BEARER_AUTHORIZATION)
        path = f"{self._url_prefix}{path}"
        resp = self._client.open(path, *args, method=method, headers=headers, **kwargs)

        if isinstance(assert_status, int):
            if resp.status_code != assert_status:
                pytest.fail(
                    f"expected HTTP {assert_status} but got HTTP {resp.status_code} "
                    f"instead\n {str(resp.json)}"
                )
        elif resp.status_code not in assert_status:
            statuses = [f"HTTP {s}" for s in assert_status]
            pytest.fail(
                f"expected one of {statuses} but got HTTP {resp.status_code} instead\n"
                f"{str(resp.json)}"
            )
        return resp
