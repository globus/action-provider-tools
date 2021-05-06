Action Provider Tools Introduction
==================================

.. image:: https://github.com/globus/action-provider-tools/workflows/Action%20Provider%20Tools%20CI/badge.svg
   :target: https://github.com/globus/action-provider-tools/workflows/Action%20Provider%20Tools%20CI/badge.svg
   :alt: CI Status

.. image:: https://readthedocs.org/projects/action-provider-tools/badge/?version=latest
   :target: https://action-provider-tools.readthedocs.io/en/latest/?badge=latest
   :alt: Documentation Status

.. image:: https://badge.fury.io/py/globus-action-provider-tools.svg
    :target: https://badge.fury.io/py/globus-action-provider-tools
    :alt: PyPi Package

.. image:: https://img.shields.io/pypi/pyversions/globus-action-provider-tools
    :target: https://pypi.org/project/globus-action-provider-tools/
    :alt: Compatible Python Versions

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/globus/action-provider-tools/workflows/Action%20Provider%20Tools%20CI/badge.svg
    :alt: Code Style

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
            "title": "Exmaple Action Provider",
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

Welcome and thank you for taking the time to contribute! 

The ``globus_action_provider_tools`` package is developed using poetry so to get
started you'll need to install `poetry <https://python-poetry.org/>`_. Once
installed, clone the repository and run ``make install`` to install the package
and its dependencies locally in a virtual environment (typically ``.venv``).

And that's it, you're ready to dive in and make code changes. Once you're
satisfied with your changes, be sure to run ``make autoformat`` to run the
project's autoformatters on your changes and ``make test`` to validate there
are no breaking changes introduced. Both these steps must be run for us to
accept incoming changes. Once you feel your work is ready to be submitted, feel
free to create a PR.

PyPi Releases
-------------

Please follow the steps below when creating a new release of the toolkit:

- Create a new release branch
    - git checkout -b release/X.Y.Z
- Update the project's dependencies
    - poetry update
- Update the project version (follow semantic versioning) in pyproject.toml
    - poetry version patch|minor|major
- Update the project version in `globus_action_provider_tools/__init__.py`
- Create a pull request into the main branch, wait for CI tests to complete
- Merge the passing pull request
- Create and publish a git tag for the new release
    - git tag v$(poetry version -s)
    - git push --tags
- Create a new GH release that references the recently created tag. Provide
  release notes with information on the changeset. Once the release is created,
  there's a GH workflow that will build the toolkit and publish it to pypi. 

Links
-----
| Full Documentation: https://action-provider-tools.readthedocs.io
| Rendered Redoc: https://globus.github.io/action-provider-tools/
| Source Code: https://github.com/globus/action-provider-tools
| Release History + Changelog: https://github.com/globus/action-provider-tools/releases
