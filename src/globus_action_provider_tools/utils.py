import datetime


def now_isoformat():
    return str(datetime.datetime.now(datetime.timezone.utc).isoformat())


uuid_regex = (
    "([a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12})"
)
principal_urn_regex = f"^urn:globus:(auth:identity|groups:id):{uuid_regex}$"
