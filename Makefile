VIRTUAL_ENV ?= .venv
PYTHON_VERSION ?= python3.6
POETRY ?= poetry
MIN_TEST_COVERAGE ?= 40

.PHONY: help docs test install

define HELPTEXT
Please use "make <target>" where <target> is one of
 docs:   to build the project's documentation
 lint:   to run autoformatters and linters
 clean:  to remove any built artifacts or environments
 test:   to run the full suite of tests
 test-toolkit:
	to run the toolkit's source code tests
 test-examples:
 	to run the example Action Providers' tests
 poetry.lock:
	to generate this project's poetry.lock file
 requirements.txt:
	to generate this project's requirements.txt file
 install | venv | $(VIRTUAL_ENV):
	to install this project and its dependencies into a virtual 
	environment at $(VIRTUAL_ENV)
endef
export HELPTEXT

help:
	@echo "$$HELPTEXT"

#specdoc: docs/action_provider_api.html

# Generates human-friendly HTML from OpenAPI spec yaml
#docs/action_provider_api.html:
#	<globus_action_provider_tools/actions_spec.openapi.yaml docs/swagger-yaml-to-html.py > docs/actions_api.html

poetry.lock: pyproject.toml
	$(POETRY) lock

requirements.txt: poetry.lock
	poetry export --format requirements.txt -o requirements.txt

$(VIRTUAL_ENV): poetry.lock
	poetry install 

venv: $(VIRTUAL_ENV)

install: $(VIRTUAL_ENV)

clean:
	rm -rf $(VIRTUAL_ENV)
	rm -rf .make_install_flag
	find . -name "*.pyc" -delete
	rm -rf *.egg-info
	rm -f *.tar.gz
	rm -rf tar-source
	rm -rf dist
	rm -rf .coverage
	rm -rf .mypy_cache
	rm -rf .pytest_cache
	rm -rf docs/build/*

lint:
	poetry run black --check \
		globus_action_provider_tools/ \
		tests/ \
		examples/
	poetry run isort --check-only --diff \
		globus_action_provider_tools/ \
		tests/ \
		examples/
	poetry run mypy --ignore-missing-imports \
		globus_action_provider_tools/ \
		tests/
	poetry run mypy --ignore-missing-imports \
		examples/watchasay
	poetry run mypy --ignore-missing-imports \
		examples/whattimeisitrightnow
	poetry run mypy --ignore-missing-imports \
		examples/apt_blueprint

test: test-toolkit test-examples

test-toolkit:
	poetry run pytest -n auto \
		--cov=globus_action_provider_tools \
		--cov-report= \
		--cov-fail-under=${MIN_TEST_COVERAGE} tests/

test-examples:
	poetry run pytest -n auto \
		--cov=examples/watchasay \
		--cov-report= \
		--cov-fail-under=${MIN_TEST_COVERAGE} \
		examples/watchasay
	poetry run pytest \
		--cov=examples/whattimeisitrightnow \
		--cov-report= \
		--cov-fail-under=${MIN_TEST_COVERAGE} \
		examples/whattimeisitrightnow
	poetry run pytest \
		--cov=examples/apt_blueprint \
		--cov-report= \
		--cov-fail-under=${MIN_TEST_COVERAGE} \
		examples/apt_blueprint

docs:
	poetry run make --directory=docs html
