import logging

from flask import Flask

import config
from blueprint import aptb

app = Flask(__name__)
app.config.from_object("config")
app.register_blueprint(aptb)
app.logger.setLevel(logging.INFO)
app.run(debug=True)
