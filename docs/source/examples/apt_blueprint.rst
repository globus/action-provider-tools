Flask Blueprint
===============

``globus-action-provider-tools`` provides a custom
`Flask Blueprint <https://flask.palletsprojects.com/tutorial/views/>`_ object
with decorators for registering functions which implement Action Provider
interfaces.

.. include:: ../../../examples/apt_blueprint/README.rst

Action Provider Implementation
------------------------------

.. literalinclude:: ../../../examples/apt_blueprint/config.py
   :language: python
   :caption: Configuring the Flask Application: `config.py`

.. literalinclude:: ../../../examples/apt_blueprint/app.py
   :language: python
   :name: APT Blueprint
   :caption: Creating the Flask Application: `app.py`

.. literalinclude:: ../../../examples/apt_blueprint/blueprint.py
   :language: python
   :caption: Creating the ActionProviderBlueprint: `blueprint.py`
