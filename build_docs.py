#!/usr/bin/env python

import logging
import shutil
import webbrowser
from datetime import datetime
from pathlib import Path
from subprocess import check_call
from typing import Optional

from cli_command_parser import Command, Counter, after_main, before_main, Action
from cli_command_parser.__version__ import __description__, __title__

log = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parent


class BuildDocs(Command, description='Build documentation using Sphinx'):
    action = Action()
    verbose = Counter('-v', help='Increase logging verbosity (can specify multiple times)')

    def __init__(self):
        self.title = __description__
        self.package = __title__
        self.package_path = PROJECT_ROOT.joinpath('lib', self.package)
        self.docs_src_path = PROJECT_ROOT.joinpath('docs', '_src')
        self._ran_backup = False
        log_fmt = '%(asctime)s %(levelname)s %(name)s %(lineno)d %(message)s' if self.verbose > 1 else '%(message)s'
        level = logging.DEBUG if self.verbose else logging.INFO
        logging.basicConfig(level=level, format=log_fmt)

    @action(default=True, help='Run sphinx-build')
    def sphinx_build(self):
        cmd = ['sphinx-build', 'docs/_src', 'docs', '-b', 'html', '-d', 'docs/_build', '-j', '8', '-T', '-E', '-q']
        log.info(f'Running: {cmd}')
        check_call(cmd)

    # region Actions

    @before_main('-c', help='Clean the docs directory before building docs', order=1)
    @action(help='Clean the docs directory')
    def clean(self):
        self.backup_rsts()
        log.info('Cleaning up old generated files')
        docs_path = PROJECT_ROOT.joinpath('docs')
        to_clean = [
            (docs_path.joinpath('_static'), {'rtd_custom.css'}),
            (docs_path.joinpath('_src', 'api'), None),
            (docs_path.joinpath('_src', 'api.rst'), None),
            (docs_path, {'_src', '_static', '_templates', '_ext', '.nojekyll'}),
        ]
        for path, exclude in to_clean:
            if not path.exists():
                continue

            clean_path(path, exclude)

        docs_path.joinpath('.nojekyll').touch()  # Force GitHub to use the RTD theme instead of their Jekyll theme

    @before_main('-u', help='Update RST files', order=2)
    def update(self):
        if not self._ran_backup:
            self.backup_rsts()
        self._generate_api_rsts()

    @after_main('-o', help='Open the docs in the default web browser after running sphinx-build')
    def open(self):
        index_path = PROJECT_ROOT.joinpath('docs', 'index.html').as_posix()
        webbrowser.open(f'file://{index_path}')

    # endregion

    @action('backup', help='Test the RST backup')
    def backup_rsts(self):
        self._ran_backup = True
        to_copy = {'index.rst', 'advanced.rst', 'basic.rst'}
        if rst_paths := list(self.docs_src_path.rglob('*.rst')):
            backup_dir = PROJECT_ROOT.joinpath('_rst_backup', datetime.now().strftime('%Y-%m-%d_%H.%M.%S'))
            backup_dir.mkdir(parents=True)
            log.info(f'Backing up old RSTs in {backup_dir.as_posix()}')
            for src_path in rst_paths:
                dst_path = backup_dir.joinpath(src_path.relative_to(self.docs_src_path))
                if not dst_path.parent.exists():
                    dst_path.parent.mkdir(parents=True)
                if src_path.name in to_copy:
                    log.debug(f'Copying {src_path.as_posix()} -> {dst_path.as_posix()}')
                    shutil.copy(src_path, dst_path)
                else:
                    log.debug(f'Moving {src_path.as_posix()} -> {dst_path.as_posix()}')
                    src_path.rename(dst_path)

    # region RST Generation

    def _generate_api_rsts(self):
        modules = []
        for path in self.package_path.glob('[a-zA-Z]*.py'):
            name = f'{path.parent.name}.{path.stem}'
            modules.append(name)
            self._make_module_rst(name)

        self._write_api_index(modules)

    def _write_rst(self, name: str, content: str, subdir: str = None):
        target_dir = self.docs_src_path.joinpath(subdir) if subdir else self.docs_src_path
        if not target_dir.exists():
            target_dir.mkdir(parents=True)
        path = target_dir.joinpath(name + '.rst')
        with path.open('w', encoding='utf-8', newline='\n') as f:
            log.debug(f'Writing {path.as_posix()}')
            f.write(content)

    def _write_api_index(self, modules: list[str]):
        bar = '*' * 17
        head = f'API Documentation\n{bar}\n\n.. toctree::\n   :maxdepth: 2\n   :caption: Modules\n\n'
        foot = '\n\nIndices and tables\n==================\n\n* :ref:`genindex`\n* :ref:`modindex`\n* :ref:`search`\n'
        mod_list = '\n'.join(map('   api/{}'.format, sorted(modules)))
        self._write_rst('api', head + mod_list + foot)

    def _make_module_rst(self, module: str):
        title = '{} Module'.format(module.split('.')[-1].title())
        bar = '*' * len(title)
        attrs = '   :members:\n   :undoc-members:\n   :show-inheritance:\n'
        content = f'{title}\n{bar}\n\n.. currentmodule:: {module}\n\n.. automodule:: {module}\n{attrs}'
        self._write_rst(module, content, 'api')

    # endregion


def clean_path(path: Path, exclude: Optional[set[str]]):
    if exclude is None:
        delete(path)
    else:
        for p in path.iterdir():
            if p.name not in exclude:
                delete(p)


def delete(path: Path):
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


if __name__ == '__main__':
    BuildDocs.parse_and_run()
