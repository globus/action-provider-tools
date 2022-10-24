import pytest

import globus_action_provider_tools.flask.helpers as helpers


@pytest.mark.parametrize(
    "version, expected",
    (
        ("2.2.3b1", (2, 2, 3)),
        ("2.2.3b", (2, 2, 3)),
        ("2.2.3", (2, 2, 3)),
        ("2.2.", (2, 2)),
        ("2.2", (2, 2)),
        ("2.", (2,)),
        ("2", (2,)),
        ("", ()),
        ("bogus", ()),
    ),
)
def test_get_flask_version(version, expected):
    assert helpers.get_flask_version(version) == expected
