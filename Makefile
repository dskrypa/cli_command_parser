init:
	pip install -e .[dev]
	pre-commit install --install-hooks

.PHONY: docs
docs:
	build_docs.py -uco

publish:
	pip install twine
	setup.py sdist bdist_wheel
	twine upload dist/*
	rm -rf build dist lib/cli_command_parser.egg-info

tag:
	tag.py
