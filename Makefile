init:
	pip install -e .[dev]
	pre-commit install --install-hooks

docs:
	docs_src/build_docs.py -uco

publish:
	pip install twine
	setup.py sdist bdist_wheel
	twine upload dist/*
	rm -rf build dist command_parser.egg-info
