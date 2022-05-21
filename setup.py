#!/usr/bin/env python

from pathlib import Path
from setuptools import setup, find_packages

project_root = Path(__file__).resolve().parent
long_description = project_root.joinpath('readme.rst').read_text('utf-8')
about = {}
exec(project_root.joinpath('lib', 'cli_command_parser', '__version__.py').read_text('utf-8'), about)


setup(
    name=about['__title__'],
    version=about['__version__'],
    author=about['__author__'],
    author_email=about['__author_email__'],
    description=about['__description__'],
    long_description=long_description,
    url=about['__url__'],
    project_urls={'Source': about['__url__']},
    packages=find_packages('lib'),
    package_dir={'': 'lib'},
    license=about['__license__'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
    ],
    python_requires='~=3.7',
    install_requires=[],
    tests_require=[],
    extras_require={
        'dev': ['pre-commit', 'ipython', 'sphinx', 'sphinx_rtd_theme', 'sphinx-paramlinks', 'testtools', 'coverage'],
        'docs': ['sphinx', 'sphinx_rtd_theme', 'sphinx-paramlinks'],
    },
)
