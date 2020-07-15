Examples
========

We provide a few example Action Provider implementations. 

The whattimeisitrightnow Action Provider demonstrates a framework agnostic
implementation that makes use of the Python toolkit. It demonstrates how to
create routes that implement the Action Provider interface, validate tokens via
a TokenChecker instance, and validate requests.

:doc:`Python Helpers Example<examples/whattimeisitrightnow>`


The watchasay Action Provider is a Flask-specific implementation that makes use
of the Globus provided Flask API Helpers toolkit. The Flask Helpers toolkit
implements much of the Action Provider interface, authentication, and
validation. Users of this toolkit need only implement callback functions that
will be used as the Action Provider routes. If possible, it is recommended to
use this Helper.

:doc:`Flask API Helpers Example<examples/watchasay>`


.. toctree::
   :maxdepth: 1
   :hidden:

   examples/whattimeisitrightnow
   examples/watchasay
