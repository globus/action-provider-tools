import logging
import sys

from flask import Flask

from examples.apt_blueprint import config
from examples.apt_blueprint.blueprint import aptb


def create_app():
    init_logging()
    app = Flask(__name__)
    app.config.from_object(config)
    app.register_blueprint(aptb)
    app.logger.setLevel(logging.INFO)
    return app


def init_logging():
    logging.basicConfig(
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        level=logging.DEBUG,
        stream=sys.stdout,
    )


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
