Development
###########


Dependency management
=====================

Dependencies are separated by purpose:

*   Direct project dependencies are managed in ``/pyproject.toml``.
*   Development dependencies (like "test" or "docs" dependencies)
    are managed in ``pyproject.toml`` files in ``/requirements/`` subdirectories.

This isolates resolution of project and development dependency versions.


Updating all dependencies
-------------------------

The command below will update all dependencies,
including pre-commit hook versions:

..  code-block::

    tox -m update


Adding a new dependency
-----------------------

You can edit the desired ``pyproject.toml`` file manually,
or run a command at the root of the repository like:

..  code-block::

    poetry add --lock --directory requirements/$CLOSURE "$PACKAGE==*"

After modifying the ``pyproject.toml`` file, run:

..  code-block::

    tox -m update
