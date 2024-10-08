"""
This 'meta test' module tests fixtures and testing tools.
"""

import pytest
from globus_sdk._testing import RegisteredResponse


def test_freeze_time_two_freezes(freeze_time):
    """Verify that it's impossible to freeze time twice.

    Did you find this test because you added new tests, got an error,
    tried changing some code, and are now seeing this test fail?
    Great! You've come to the right place.

    If you need to freeze time twice, it may be easier to align the time
    in your mocked API response with the time in an existing mocked API response.
    You can do this by changing the time values in your new API response.
    Do not add `metadata["freezegun"]` in your new API response.

    If you *really* need to freeze time twice, go ahead and do so.
    You can change or remove this test completely,
    but please ensure that you are testing the changes you introduced
    in the `freeze_time` fixture (if any).
    """

    response = RegisteredResponse(
        path="does/not/matter",
        metadata={"freezegun": 1000},
    )
    freeze_time(response)
    with pytest.raises(AssertionError):
        freeze_time(response)
