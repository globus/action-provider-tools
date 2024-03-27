Action Provider Tools Introduction
==================================

This is an experimental toolkit to help developers build Action Providers for
use in Globus Automate including for invocation via Globus Flows.

As this is experimental, no support is implied or provided for any sort of use
of this package. It is published for ease of distribution among those planning
to use it for its intended, experimental, purpose.

Basic Usage
-----------

Install the base toolkit with ``pip install globus_action_provider_tools``

You can then import the toolkit's standalone components from
``globus_action_provider_tools``. This is useful in instances where you want to
use pieces of the library to perform a function (such as token validation via
the TokenChecker or API schema validation via the ActionStatus or ActionRequest)
and plug into other web frameworks.


.. code-block:: python

    from flask import Flask
    from globus_action_provider_tools import ActionProviderDescription

    description = ActionProviderDescription(
        globus_auth_scope="https://auth.globus.org/scopes/00000000-0000-0000-0000-000000000000/action_all",
        title="My Action Provider",
        admin_contact="support@example.org",
        synchronous=True,
        input_schema={
            "$id": "whattimeisitnow.provider.input.schema.json",
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "Example Action Provider",
            "type": "object",
            "properties": {"message": {"type": "string"}},
            "required": ["message"],
            "additionalProperties": False,
        },
        api_version="1.0",
        subtitle="Just an example",
        description="",
        keywords=["example", "testing"],
        visible_to=["public"],
        runnable_by=["all_authenticated_users"],
        administered_by=["support@example.org"],
    )

To install the Flask helpers as well for use specifically in developing Flask
based Action Providers, install this library using ``pip install
globus_action_provider_tools[flask]``

Reporting Issues
----------------

If you're experiencing a problem using globus_action_provider_tools, or have an
idea for how to improve the toolkit, please open an issue in the repository and
share your feedback.

Testing, Development, and Contributing
--------------------------------------

Welcome, and thank you for taking the time to contribute!

To get started, you'll need to clone the repository and run ``make install``
to install the package and its dependencies locally in a virtual environment (``.venv/``).

Next, activate the virtual environment:

..  code-block:: console

    $ source .venv/bin/activate

And that's it, you're ready to dive in and make code changes.
Run ``make test`` to validate there are no breaking changes introduced.
Once you feel your work is ready to be submitted, feel free to create a PR.

Links
-----
| Full Documentation: https://action-provider-tools.readthedocs.io
| Rendered Redoc: https://globus.github.io/action-provider-tools/
| Source Code: https://github.com/globus/action-provider-tools
| Release History + Changelog: https://github.com/globus/action-provider-tools/releases
