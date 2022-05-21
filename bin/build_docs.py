#!/usr/bin/env python

import logging
import shutil
import webbrowser
from datetime import datetime
from pathlib import Path
from subprocess import check_call
from typing import Collection

from cli_command_parser import Command, Counter, after_main, before_main, Action, Flag
from cli_command_parser.__version__ import __description__, __title__

log = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SKIP_MODULES = {'cli_command_parser.compat'}
DOCS_AUTO = {
    '_build': True,
    '_modules': True,
    '_sources': True,
    '_src': (True, {'api', 'api.rst'}),
    '_static': (False, {'rtd_custom.css'}),
}

# region Templates

INDEX_TEMPLATE = """
API Documentation
*****************

.. toctree::
   :maxdepth: 2
   :caption: Modules

{mod_list}

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
""".lstrip()

MODULE_TEMPLATE = """
{name} Module
{bar}

.. currentmodule:: {module}

.. automodule:: {module}
   :members:
   :undoc-members:
   :show-inheritance:
""".lstrip()

# endregion


class BuildDocs(Command, description='Build documentation using Sphinx'):
    action = Action()
    verbose = Counter('-v', help='Increase logging verbosity (can specify multiple times)')
    dry_run = Flag('-D', help='Print the actions that would be taken instead of taking them')

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
        prefix = '[DRY RUN] Would run' if self.dry_run else 'Running'
        log.info(f'{prefix}: {cmd}')
        if not self.dry_run:
            check_call(cmd)

    # region Actions

    @before_main('-c', help='Clean the docs directory before building docs', order=1)
    @action(help='Clean the docs directory')
    def clean(self):
        self.backup_rsts()
        docs_dir = PROJECT_ROOT.joinpath('docs')
        prefix = '[DRY RUN] Would delete' if self.dry_run else 'Deleting'
        log.info('Cleaning up old generated files')
        for path in docs_dir.iterdir():
            if path.is_file():
                log.debug(f'{prefix} {path.as_posix()}')
                if not self.dry_run:
                    path.unlink()
                continue

            is_auto = DOCS_AUTO.get(path.name)
            if is_auto:
                try:
                    content_is_auto, content = is_auto
                except TypeError:
                    log.debug(f'{prefix} {path.as_posix()}')
                    if not self.dry_run:
                        shutil.rmtree(path)
                else:
                    for p in path.iterdir():
                        if content_is_auto == (p.name in content):
                            log.debug(f'{prefix} {p.as_posix()}')
                            if not self.dry_run:
                                delete(p)

        if not self.dry_run:
            docs_dir.joinpath('.nojekyll').touch()  # Force GitHub to use the RTD theme instead of their Jekyll theme

    @before_main('-u', help='Update RST files', order=2)
    def update(self):
        if not self._ran_backup:
            self.backup_rsts()
        self._generate_api_rsts()

    @after_main('-o', help='Open the docs in the default web browser after running sphinx-build')
    def open(self):
        index_path = PROJECT_ROOT.joinpath('docs', 'index.html').as_posix()
        if not self.dry_run:
            webbrowser.open(f'file://{index_path}')

    # endregion

    @action('backup', help='Test the RST backup')
    def backup_rsts(self):
        self._ran_backup = True
        rst_paths = list(self.docs_src_path.rglob('*.rst'))
        if not rst_paths:
            return

        auto_generated = DOCS_AUTO['_src'][1]
        backup_dir = PROJECT_ROOT.joinpath('_rst_backup', datetime.now().strftime('%Y-%m-%d_%H.%M.%S'))

        if self.dry_run:
            mv_pre, cp_pre, bk_pre = '[DRY RUN] Would move', '[DRY RUN] Would copy', '[DRY RUN] Would back up'
        else:
            backup_dir.mkdir(parents=True)
            mv_pre, cp_pre, bk_pre = 'Moving', 'Copying', 'Backing up'

        log.info(f'{bk_pre} old RSTs in {backup_dir.as_posix()}')
        for src_path in rst_paths:
            rel_path = src_path.relative_to(self.docs_src_path)
            dst_path = backup_dir.joinpath(rel_path)
            if not dst_path.parent.exists() and not self.dry_run:
                dst_path.parent.mkdir(parents=True)

            if rel_path.parts[0] in auto_generated:
                log.debug(f'{mv_pre} {src_path.as_posix()} -> {dst_path.as_posix()}')
                if not self.dry_run:
                    src_path.rename(dst_path)
            else:
                log.debug(f'{cp_pre} {src_path.as_posix()} -> {dst_path.as_posix()}')
                if not self.dry_run:
                    shutil.copy(src_path, dst_path)

    # region RST Generation

    def _generate_api_rsts(self):
        modules = []
        for path in self.package_path.glob('[a-zA-Z]*.py'):
            name = f'{path.parent.name}.{path.stem}'
            if name in SKIP_MODULES:
                continue
            modules.append(name)
            self._make_module_rst(name)

        self._write_api_index(modules)

    def _write_rst(self, name: str, content: str, subdir: str = None):
        target_dir = self.docs_src_path.joinpath(subdir) if subdir else self.docs_src_path
        if not target_dir.exists() and not self.dry_run:
            target_dir.mkdir(parents=True)

        prefix = '[DRY RUN] Would write' if self.dry_run else 'Writing'
        path = target_dir.joinpath(name + '.rst')
        log.debug(f'{prefix} {path.as_posix()}')
        if not self.dry_run:
            with path.open('w', encoding='utf-8', newline='\n') as f:
                f.write(content)

    def _write_api_index(self, modules: Collection[str]):
        mod_list = '\n'.join(map('   api/{}'.format, sorted(modules)))
        self._write_rst('api', INDEX_TEMPLATE.format(mod_list=mod_list))

    def _make_module_rst(self, module: str):
        name = module.split('.')[-1].title()
        bar = '*' * (len(name) + 7)
        self._write_rst(module, MODULE_TEMPLATE.format(name=name, bar=bar, module=module), 'api')

    # endregion


def delete(path: Path):
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


if __name__ == '__main__':
    BuildDocs.parse_and_run()
