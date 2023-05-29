init:
	pip install -r requirements-dev.txt --require-virtualenv
	pre-commit install --install-hooks

.PHONY: docs
docs:
	bin/build_docs.py -uco

publish:
	rm -rf dist
	pip install twine build -U --require-virtualenv
	python -m build
	twine upload dist/*
	rm -rf lib/cli_command_parser.egg-info

tag:
	bin/tag.py
