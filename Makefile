VIRTUAL_ENV ?= .venv

.PHONY: help install docs redoc clean test

define HELPTEXT
Please use "make <target>" where <target> is one of:

    install:
        Install this project and its dependencies into a virtual
        environment at $(VIRTUAL_ENV)

    docs:
        Build this project's documentation locally in docs/build

	redoc:
        Build the ActionProvider OpenAPI Redoc Spec

    clean:
        Remove any built artifacts or environments

    test:
        Run the full suite of tests

    poetry.lock:
        Generate this project's poetry.lock file

endef
export HELPTEXT

help:
	@echo "$$HELPTEXT"

install:
	poetry install

docs:
	tox run -e docs

redoc:
	npx @redocly/cli build-docs --output index.html actions_spec.openapi.yaml

clean:
	rm -rf $(VIRTUAL_ENV)
	find . -name "*.pyc" -delete
	rm -rf *.egg-info/
	rm -rf dist/
	rm -f .coverage
	rm -rf .mypy_cache/
	rm -rf .pytest_cache/
	rm -rf .slyp_cache/
	rm -rf docs/build/

test:
	tox run-parallel

poetry.lock:
	poetry lock
