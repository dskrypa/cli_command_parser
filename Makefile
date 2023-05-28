init:
	pip install -r requirements-dev.txt --require-virtualenv
	pre-commit install --install-hooks

.PHONY: docs
docs:
	bin/build_docs.py -uco

publish:
	pip install twine build -U --require-virtualenv
	python -m build
	twine upload dist/*
	rm -rf dist lib/cli_command_parser.egg-info

tag:
	bin/tag.py
