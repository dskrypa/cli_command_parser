#!/usr/bin/env python

import logging
import shutil
from datetime import datetime
from pathlib import Path
from subprocess import check_call

from cli_command_parser import Action, Command, Counter, Flag, after_main, before_main, main
from cli_command_parser.__version__ import __description__, __title__
from cli_command_parser.documentation import RstWriter

log = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SKIP_FILES = {'requirements.txt'}
SKIP_MODULES = {'cli_command_parser.compat'}
DOCS_AUTO = {  # values: (content_is_auto, content), where everything else is treated as the opposite
    '_build': True,
    '_images': True,
    '_modules': True,
    '_sources': True,
    '_src': (True, {'api', 'api.rst', 'examples', 'examples.rst'}),
    '_static': (False, {'rtd_custom.css'}),
    'api': True,
    'examples': True,
}


class BuildDocs(Command, description='Build documentation using Sphinx'):
    _ran_backup = False
    action = Action()
    verbose = Counter('-v', help='Increase logging verbosity (can specify multiple times)')
    dry_run = Flag('-D', help='Print the actions that would be taken instead of taking them')

    def _init_command_(self):
        self.title = __description__
        self.package = __title__
        self.package_path = PROJECT_ROOT.joinpath('lib', self.package)
        self.docs_src_path = PROJECT_ROOT.joinpath('docs', '_src')
        self.rst_writer = RstWriter(self.docs_src_path, dry_run=self.dry_run, skip_modules=SKIP_MODULES)
        log_fmt = '%(asctime)s %(levelname)s %(name)s %(lineno)d %(message)s' if self.verbose > 1 else '%(message)s'
        level = logging.DEBUG if self.verbose else logging.INFO
        logging.basicConfig(level=level, format=log_fmt)

    @action(default=True, help='Run sphinx-build')
    def sphinx_build(self):
        # fmt: off
        cmd = [
            'sphinx-build', 'docs/_src', 'docs',
            '-b', 'html',  # builder to use (default: html)
            '-d', 'docs/_build',  # path for the cached environment and doctree files (default: OUTPUTDIR/.doctrees)
            # '-j', '8',  # build in parallel with N processes where possible ("auto" will set N to cpu-count)
            '-j', 'auto',  # Parallel processes to use
            '-T',  # show full traceback on exception
            '-E',  # don't use a saved environment, always read all files
            '-q',  # no output on stdout, just warnings on stderr
        ]
        # fmt: on
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
                if path.name in SKIP_FILES:
                    continue
                log.debug(f'{prefix} {path.as_posix()}')
                if not self.dry_run:
                    path.unlink()
                continue

            if is_auto := DOCS_AUTO.get(path.name):
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

        log.info('Updating auto-generated RST files')
        pkg_path = self.package_path
        self.rst_writer.document_package(pkg_path.name, pkg_path, name='api', header='API Documentation', max_depth=3)

        examples_dir = PROJECT_ROOT.joinpath('examples')
        paths = (examples_dir.joinpath('complex'), *examples_dir.glob('*.py'))
        self.rst_writer.document_scripts(paths, 'examples', index_header='Example Scripts')

    @after_main('-o', help='Open the docs in the default web browser after running sphinx-build')
    def open(self):
        import webbrowser

        index_path = PROJECT_ROOT.joinpath('docs', 'index.html').as_posix()
        if not self.dry_run:
            webbrowser.open(f'file://{index_path}')

    # endregion

    @action('backup', help='Test the RST backup')
    def backup_rsts(self):
        self._ran_backup = True
        if not (rst_paths := list(self.docs_src_path.rglob('*.rst'))):
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


def delete(path: Path):
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


if __name__ == '__main__':
    main()
