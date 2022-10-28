"""
This module tests some of the shared utility functions in the Flask helpers.
"""

import pytest
from flask import Flask

from globus_action_provider_tools.data_types import ActionStatusValue
from globus_action_provider_tools.flask.helpers import (
    parse_query_args,
    query_args_to_enum,
)


def test_query_args_to_enum():
    """
    Validates that valid query args are correctly transformed into Enum fields
    and that invalid query args are dropped.
    """
    valid_query_args = [e.name.title() for e in ActionStatusValue]
    invalid_query_args = ["RUNNING", "activate", "STOPPED"]

    result = query_args_to_enum(
        valid_query_args + invalid_query_args, ActionStatusValue
    )
    assert len(result) == len(valid_query_args)


@pytest.mark.parametrize(
    "query_string, expected_statuses, expected_roles",
    [
        (
            "/?status=active,succeeded",
            {"active", "succeeded"},
            {"creator_id"},
        ),
        (
            "/?roles=",
            {"active"},
            {"creator_id"},
        ),
        (
            "/?roles=monitor_by&status=INACTIVE",
            {"inactive"},
            {"monitor_by"},
        ),
    ],
)
def test_parse_query_args(query_string, expected_statuses, expected_roles):
    """
    Validates that valid query args and their defaults can be parsed from the
    Flask request's string.
    """
    app = Flask(__name__)
    valid_statuses = set(e.name.casefold() for e in ActionStatusValue)

    with app.test_request_context(query_string) as req:
        statuses = parse_query_args(
            req.request,
            arg_name="status",
            default_value="active",
            valid_vals=valid_statuses,
        )
        roles = parse_query_args(
            req.request,
            arg_name="roles",
            default_value="creator_id",
            valid_vals={"creator_id", "monitor_by", "manage_by"},
        )

        assert statuses == expected_statuses
        assert roles == expected_roles
