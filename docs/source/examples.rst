Examples
========

We demonstrate how to use the different components in the toolkit by providing a
few sample Action Provider implementations. Each implementation leverages a
different part of the toolkit to implement a Globus Automate-compatible Action
Provider.

Flask Decorators
^^^^^^^^^^^^^^^^

`Flask <http://www.python.org/>`__ is a popular framework for creating APIs. This
toolkit provides a custom `Flask Blueprint
<https://flask.palletsprojects.com/en/1.1.x/tutorial/views/>`_ object that
provides decorators for registering functions that will implement the operations
for the Action Provider Interface and also perform most of the authentication and
validation. All the developer needs to do is create a series of
functions that will execute as the Action Provider's endpoints and register the
Blueprint with a Flask application.

:doc:`Flask Decorators Example<examples/apt_blueprint>`

Flask API Helpers
^^^^^^^^^^^^^^^^^

Another `Flask <http://www.python.org/>`__ targetted helper, this part of the
toolkit provides a different way of creating an Action Provider which also
implements most of the authentication and validation required. Users of this
helper need only implement callback functions that will be used as the Action
Provider routes.

:doc:`Flask API Helpers Example<examples/watchasay>`


Framework Agnostic Tools
^^^^^^^^^^^^^^^^^^^^^^^^

Finally, if you  would like to use your own Python microservice framework, you
can use the toolkit's components individually. The `Flask
<http://www.python.org/>`_ based components of the toolkit are good examples of
how you can compose the individual components. We also provide an example
implementation demonstrating how you can create routes implementing the Action
Provider interface, how you can create a TokenChecker instance to validate
tokens, how to create validation objects to validate incoming ActionRequests and
more.

:doc:`Python Helpers Example<examples/whattimeisitrightnow>`


.. toctree::
   :maxdepth: 1
   :hidden:

   examples/whattimeisitrightnow
   examples/watchasay
   examples/apt_blueprint
