from os import urandom

import arrow
from base62 import encodebytes as base62


def now_isoformat():
    return str(arrow.utcnow())


def shortish_id() -> str:
    """Generate a random relatively short string of URL safe alphanumeric characters. Value
    space is sufficiently large that the odds of collision are extremely low.
    """
    return base62(urandom(9))


uuid_regex = (
    "([a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12})"
)
principal_urn_regex = f"^urn:globus:(auth:identity|groups:id):{uuid_regex}$"
