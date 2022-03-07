#!/usr/bin/env python

from datetime import datetime
from subprocess import check_output, check_call

from cli_command_parser import Command, Flag


class TagUpdater(Command):
    dry_run = Flag('-D', help='Print the actions that would be taken instead of taking them')
    force_suffix = Flag(
        '-S', help='Always include a suffix (default: only when multiple versions are created on the same day)'
    )

    def main(self):
        latest = get_latest_tag()
        next_version = get_next_version(latest, self.force_suffix)

        if self.dry_run:
            print(f'[DRY RUN] Would create tag: {next_version}')
        else:
            print(f'Creating tag: {next_version}')
            check_call(['git', 'tag', next_version])
            check_call(['git', 'push', '--tags'])


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
        old_suffix = ''

    old_date = datetime.strptime(old_date_str, '%Y.%m.%d').date()
    today = datetime.now().date()
    today_str = today.strftime('%Y.%m.%d')
    if old_date < today and not force_suffix:
        return today_str
    else:
        new_suffix = 1 + (int(old_suffix) if old_suffix else 0)
        return f'{today_str}-{new_suffix}'


if __name__ == '__main__':
    TagUpdater.parse_and_run()
