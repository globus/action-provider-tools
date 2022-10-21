VIRTUAL_ENV ?= .venv
MIN_TEST_COVERAGE ?= 40
LINT_PATHS = globus_action_provider_tools/ tests/ examples/

.PHONY: help install docs redoc lint clean test poetry.lock requirements.txt

define HELPTEXT
Please use "make <target>" where <target> is one of:

    install:
        Install this project and its dependencies into a virtual 
        environment at $(VIRTUAL_ENV)

    docs:
        Build this project's documentation locally in docs/build

	redoc:
        Build the ActionProvider OpenAPI Redoc Spec

    lint:
        Run autoformatters and linters in check-only mode
    
    clean:  
        Remove any built artifacts or environments
    
    test:
        Run the full suite of tests
    
    test-toolkit:
        Run the toolkit's source code tests
    
    test-examples:
        Run the example Action Providers' tests
    
    poetry.lock:
        Generate this project's poetry.lock file
    
    requirements.txt:
        Generate this project's requirements.txt file

endef
export HELPTEXT

help:
	@echo "$$HELPTEXT"

install:
	poetry install

docs:
	poetry run make --directory=docs html

redoc:
	npx redoc-cli bundle --output index.html actions_spec.openapi.yaml

lint:
	poetry run mypy --ignore-missing-imports \
		globus_action_provider_tools/ \
		tests/
	poetry run mypy --ignore-missing-imports \
		examples/watchasay
	poetry run mypy --ignore-missing-imports \
		examples/whattimeisitrightnow
	poetry run mypy --ignore-missing-imports \
		examples/apt_blueprint

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

test:
	poetry run pytest \
		--cov=globus_action_provider_tools \
		--cov-report= \
		--cov-fail-under=${MIN_TEST_COVERAGE} \
		tests/ examples/

poetry.lock: 
	poetry lock

requirements.txt:
	poetry export --format requirements.txt -o requirements.txt
