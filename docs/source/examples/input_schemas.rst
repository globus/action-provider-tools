Action Provider Input Schemas
=============================

We support user-written JSONSchema and Pydantic_ based schema defintions. In
this document we demonstrate how either defintion can be created and loaded into
an ActionProvider to provide input documentation and validation. In many cases,
it's easier to work with Pydantic models to define JSON input.

JSONSchema
^^^^^^^^^^

A typical schema definition may look like:

.. code-block:: JSON

    {
        "$id": "https://automate.globus.org/skeleton_action_provider.input.schema.json",
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Skeleton Action Provider Input Schema",
        "type": "object",
        "properties": {
            "input_string": {
                "description": "A string to be replayed back to the user",
                "type": "string"
            }
        },
        "additionalProperties": false,
        "required": [
            "input_string"
        ]
    }

Best practice is to store this JSON file externally to the ActionProvider. On
startup, the file is parsed as a Python object and loaded into the
ActionProvider:

.. code-block:: python

    import json

    from globus_action_provider_tools.data import ActionProviderDescription

    # load the schema definition
    schema = json.load("schema.json)

    # add the schema definition to the ActionProvider description
    provider_description = ActionProviderDescription(
        globus_auth_scope=...,
        title="skeleton_action_provider",
        admin_contact="support@globus.org",
        synchronous=True,
        input_schema=schema,
        log_supported=False,
        visible_to=["public"],
    )

    # go on to use the ActionProvider description to create the ActionProvider
    ...

Pydantic
^^^^^^^^

As a convenience, we allow developers to define their ActionProvider input
schema definitions as Pydantic_ models.

To do so, first define a pydantic model that represents your expected input and
constraints:

.. code-block:: python

    from pydantic import BaseModel, Field

    class ActionProviderPydanticInputSchema(BaseModel):
        echo_string: str = Field(
            ...,
            title="Echo String",
            description="An input value to this ActionProvider to echo back in its response",
        )

        # pydantic lets you display examples of passing input
        class Config:
            schema_extra = {"example": {"echo_string": "hi there"}}

With the model created, pass the **class itself** to the ActionProvider
description and load that into the ActionProvider:

.. code-block:: python

    from globus_action_provider_tools.data import ActionProviderDescription

    provider_description = ActionProviderDescription(
        globus_auth_scope=...,
        title="skeleton_action_provider",
        admin_contact="support@globus.org",
        synchronous=True,
        input_schema=ActionProviderPydanticInputSchema,
        log_supported=False,
        visible_to=["public"],
    )

    # go on to use the ActionProvider description to create the ActionProvider
    ...

.. note::

    The class, not an instance object, is passed as the value to
    ``input_schema``.

When performing input validation, the ActionProvider will now produce detailed
error messages on what went wrong when attempting to parse the input:

.. code-block:: python

    [{'loc': ['echo_string'], 'msg': 'field required', 'type': 'value_error.missing'}]

Pydantic_ provides extensive tools for defining input definition and input
validation. For full and up-to-date documentation, see the official docs.

.. _Pydantic: https://pydantic-docs.helpmanual.io/
