import uuid


def random_creator_id():
    return "urn:globus:auth:identity:" + str(uuid.uuid4())
