#!/usr/bin/env python

import logging
import re
from datetime import datetime
from pathlib import Path
from subprocess import check_output, check_call
from tempfile import TemporaryDirectory
from typing import Optional

from cli_command_parser import Command, Flag, Option, Counter

log = logging.getLogger(__name__)
DEFAULT_PATH = Path('lib/cli_command_parser/__version__.py')


class TagUpdater(Command):
    version_file_path: Path = Option(
        '-p', metavar='PATH', default=DEFAULT_PATH, help='Path to the __version__.py file to update'
    )
    verbose = Counter('-v', help='Increase logging verbosity (can specify multiple times)')
    dry_run = Flag('-D', help='Print the actions that would be taken instead of taking them')
    force_suffix = Flag(
        '-S', help='Always include a suffix (default: only when multiple versions are created on the same day)'
    )

    def main(self):
        log_fmt = '%(asctime)s %(levelname)s %(name)s %(lineno)d %(message)s' if self.verbose > 1 else '%(message)s'
        logging.basicConfig(level=logging.DEBUG if self.verbose else logging.INFO, format=log_fmt)

        # latest = get_latest_tag()
        # next_version = get_next_version(latest, self.force_suffix)
        next_version = self.update_version()

        if self.dry_run:
            log.info(f'[DRY RUN] Would commit version file: {self.version_file_path.as_posix()}')
            log.info(f'[DRY RUN] Would create tag: {next_version}')
        else:
            log.info(f'Committing version file: {self.version_file_path.as_posix()}')
            check_call(['git', 'add', self.version_file_path.as_posix()])
            check_call(['git', 'commit', '-m', f'updated version to {next_version}'])
            check_call(['git', 'push'])

            log.info(f'Creating tag: {next_version}')
            check_call(['git', 'tag', next_version])
            check_call(['git', 'push', '--tags'])

    def update_version(self) -> Optional[str]:
        version_pat = re.compile(r'^(\s*__version__\s?=\s?)(["\'])(\d{4}\.\d{2}\.\d{2}(?:-\d+)?)\2$')
        path = self.version_file_path
        found = False
        new_ver = None
        with TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir).joinpath('tmp.txt')
            log.debug(f'Writing updated file to temp file={tmp_path}')
            with path.open('r', encoding='utf-8') as f_in, tmp_path.open('w', encoding='utf-8', newline='\n') as f_out:
                for line in f_in:
                    if found:
                        f_out.write(line)
                    elif m := version_pat.match(line):
                        found = True
                        new_ver, new_line = self._updated_version_line(m.groups())
                        f_out.write(new_line)
                    else:
                        f_out.write(line)

            if found:
                if self.dry_run:
                    log.info(f'[DRY RUN] Would replace original file={path.as_posix()} with modified version')
                else:
                    log.info(f'Replacing original file={path.as_posix()} with modified version')
                    tmp_path.replace(path)
            else:
                raise RuntimeError(f'No valid version was found in {path.as_posix()}')

        return new_ver

    def _updated_version_line(self, groups):
        var, quote, old_ver = groups
        new_ver = get_next_version(old_ver, self.force_suffix)
        prefix = '[DRY RUN] Would replace' if self.dry_run else 'Replacing'
        log.info(f'{prefix} old version={old_ver} with new={new_ver}')
        new_line = f'{var}{quote}{new_ver}{quote}\n'
        return new_ver, new_line


def get_latest_tag():
    stdout: str = check_output(['git', 'tag', '--list'], text=True)

    versions = []
    for line in stdout.splitlines():
        try:
            date, suffix = line.split('-')
        except ValueError:
            date = line
            suffix = 0
        else:
            suffix = int(suffix)
        versions.append((date, suffix))

    date, suffix = max(versions)
    return f'{date}-{suffix}'


def get_next_version(old_ver: str, force_suffix: bool = False):
    try:
        old_date_str, old_suffix = old_ver.split('-')
    except ValueError:
        old_date_str = old_ver
        new_suffix = 1
    else:
        new_suffix = int(old_suffix) + 1

    old_date = datetime.strptime(old_date_str, '%Y.%m.%d').date()
    today = datetime.utcnow().date()
    today_str = today.strftime('%Y.%m.%d')
    if old_date < today and not force_suffix:
        return today_str
    else:
        return f'{today_str}-{new_suffix}'


if __name__ == '__main__':
    TagUpdater.parse_and_run()
