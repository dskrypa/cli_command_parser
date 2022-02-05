#!/usr/bin/env python

from distutils.cmd import Command
from distutils.errors import DistutilsExecError
from pathlib import Path
from setuptools import setup

project_root = Path(__file__).resolve().parent
long_description = project_root.joinpath('readme.rst').read_text('utf-8')
about = {}
exec(project_root.joinpath('lib', 'command_parser', '__version__.py').read_text('utf-8'), about)


class BuildDocsCmd(Command):
    long_description = 'Build documentation using Sphinx'
    user_options = [('clean', 'c', 'Clean the docs directory before building docs')]
    boolean_options = ['clean']

    def initialize_options(self):
        self.clean = False  # noqa

    def finalize_options(self):
        pass

    def run(self):
        import shutil
        from distutils import log
        from subprocess import check_call, CalledProcessError

        if self.clean:
            self.announce('Removing old docs dir before re-building docs', log.INFO)
            docs_path = project_root.joinpath('docs')
            if docs_path.exists():
                shutil.rmtree(docs_path)
            docs_path.mkdir()
            docs_path.joinpath('.nojekyll').touch()

        # fmt: off
        cmd = [
            'sphinx-build', 'docs_src', 'docs', '-b', 'html', '-d', 'docs/_build', '-j', '8', '-T', '-E',
            '-q',
            # '-vvvv',
        ]
        # fmt: on
        self.announce(f'Running: {cmd}', log.DEBUG)
        try:
            check_call(cmd)
        except CalledProcessError as e:
            raise DistutilsExecError(str(e)) from e


setup(
    name=about['__title__'],
    version=about['__version__'],
    author=about['__author__'],
    author_email=about['__author_email__'],
    description=about['__description__'],
    long_description=long_description,
    url=about['__url__'],
    project_urls={'Source': about['__url__']},
    packages=['command_parser'],
    license=about['__license__'],
    classifiers=[
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
    ],
    python_requires='~=3.9',
    install_requires=[],
    extras_require={
        'dev': ['pre-commit', 'ipython', 'sphinx', 'sphinx_rtd_theme'],
    },
    cmdclass={'docs': BuildDocsCmd},
)
