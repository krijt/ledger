PYTHON ?= .venv/bin/python
PIP ?= .venv/bin/pip

.PHONY: venv install test lint fmt clean

venv:
	python3 -m venv .venv

install: venv
	$(PIP) install -r requirements-dev.txt

test:
	$(PYTHON) -m pytest

clean:
	rm -rf .venv .pytest_cache __pycache__ */__pycache__
