VIRTUAL_ENV ?= .venv
SHELL := /bin/bash

.PHONY: help install docs redoc clean test

define HELPTEXT
Please use "make <target>" where <target> is one of:

    install:
        Install this project and its dependencies into a virtual environment at $(VIRTUAL_ENV)

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
	python -m venv $(VIRTUAL_ENV)
	$(VIRTUAL_ENV)/bin/python -m pip install --upgrade pip setuptools wheel
	$(VIRTUAL_ENV)/bin/python -m pip install --upgrade -rrequirements/test/requirements.txt
	$(VIRTUAL_ENV)/bin/python -m pip install --editable .[flask]

	# Ensure that pre-commit and tox are available.
	# The "source && <command> --version" syntax allows commands
	# to be installed either globally or locally.
	source $(VIRTUAL_ENV)/bin/activate && pre-commit --version || $(VIRTUAL_ENV)/bin/python -m pip install pre-commit
	source $(VIRTUAL_ENV)/bin/activate && tox --version || $(VIRTUAL_ENV)/bin/python -m pip install tox

	# Install pre-commit as a git hook.
	source $(VIRTUAL_ENV)/bin/activate && pre-commit install

docs:
	source $(VIRTUAL_ENV)/bin/activate
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
	source $(VIRTUAL_ENV)/bin/activate
	tox run-parallel
