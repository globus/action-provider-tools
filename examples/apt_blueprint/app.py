import logging

from flask import Flask

from examples.apt_blueprint import config
from examples.apt_blueprint.blueprint import aptb


def create_app():
    app = Flask(__name__)
    app.logger.setLevel(logging.DEBUG)
    app.config.from_object(config)
    app.register_blueprint(aptb)
    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
