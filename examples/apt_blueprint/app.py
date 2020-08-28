import logging

import config
from blueprint import aptb
from flask import Flask

app = Flask(__name__)
app.config.from_object("config")
app.register_blueprint(aptb)
app.logger.setLevel(logging.INFO)
app.run(debug=True)
