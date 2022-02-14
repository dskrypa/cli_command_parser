#!/usr/bin/env python

import logging
import shutil
from datetime import datetime
from pathlib import Path
from subprocess import check_call

from command_parser import Command, Counter, action_flag
from command_parser.__version__ import __description__

log = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
PACKAGE = 'lib/command_parser'


class BuildDocs(Command, description='Build documentation using Sphinx', allow_multiple_action_flags=True):
    verbose = Counter('-v', help='Increase logging verbosity (can specify multiple times)')

    def __init__(self, args):
        log_fmt = '%(asctime)s %(levelname)s %(name)s %(lineno)d %(message)s' if self.verbose > 1 else '%(message)s'
        level = logging.DEBUG if self.verbose else logging.INFO
        logging.basicConfig(level=level, format=log_fmt)

    def main(self, *args, **kwargs):
        super().main(*args, **kwargs)
        cmd = ['sphinx-build', 'docs_src', 'docs', '-b', 'html', '-d', 'docs/_build', '-j', '8', '-T', '-E', '-q']
        log.debug(f'Running: {cmd}')
        check_call(cmd)

    @action_flag('-c', help='Clean the docs directory before building docs', order=1)
    def clean(self):
        log.info('Removing old docs dir before re-building docs')
        docs_path = PROJECT_ROOT.joinpath('docs')
        if docs_path.exists():
            shutil.rmtree(docs_path)
        docs_path.mkdir()
        docs_path.joinpath('.nojekyll').touch()

    @action_flag('-u', help='Update RST files', order=2)
    def update(self):
        self._backup_rsts()
        self._generate_rsts()

    def _backup_rsts(self):
        docs_src_dir = PROJECT_ROOT.joinpath('docs_src')
        if rst_paths := list(docs_src_dir.glob('*.rst')):
            backup_dir = PROJECT_ROOT.joinpath('_rst_backup', datetime.now().strftime('%Y-%m-%d_%H.%M.%S'))
            backup_dir.mkdir(parents=True)
            for src_path in rst_paths:
                dst_path = backup_dir.joinpath(src_path.name)
                log.debug(f'Moving {src_path.as_posix()} -> {dst_path.as_posix()}')
                src_path.rename(dst_path)

    def _generate_rsts(self):
        modules = []
        for path in PROJECT_ROOT.joinpath(PACKAGE).glob('[a-zA-Z]*.py'):
            name = f'{path.parent.name}.{path.stem}'
            modules.append(name)
            self._make_module_rst(name)

        self._write_index(modules)

    def _write_index(self, modules: list[str]):
        title = __description__
        bar = '*' * len(title)
        head = f'{title}\n{bar}\n\n.. toctree::\n   :maxdepth: 1\n   :caption: Modules\n   :hidden:\n\n'
        foot = '\n\nIndices and tables\n==================\n\n* :ref:`genindex`\n* :ref:`modindex`\n* :ref:`search`\n'
        mod_list = '\n'.join(map('   {}'.format, modules))
        content = head + mod_list + foot
        with PROJECT_ROOT.joinpath('docs_src', 'index.rst').open('w', encoding='utf-8', newline='\n') as f:
            log.info(f'Writing {f.name}')
            f.write(content)

    def _make_module_rst(self, module: str):
        title = '{} Module'.format(module.split('.')[-1].title())
        bar = '*' * len(title)
        # attrs = '   :members:\n   :private-members:\n   :undoc-members:\n   :show-inheritance:\n'
        attrs = '   :members:\n   :undoc-members:\n   :show-inheritance:\n'
        content = f'{title}\n{bar}\n\n.. currentmodule:: {module}\n\n.. automodule:: {module}\n{attrs}'
        with PROJECT_ROOT.joinpath('docs_src', f'{module}.rst').open('w', encoding='utf-8', newline='\n') as f:
            log.info(f'Writing {f.name}')
            f.write(content)


if __name__ == '__main__':
    BuildDocs.parse_and_run()
