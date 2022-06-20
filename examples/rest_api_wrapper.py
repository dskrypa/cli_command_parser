#!/usr/bin/env python

import logging
from fnmatch import fnmatch

from cli_command_parser import Command, Positional, SubCommand, Flag, Option, Counter, ParamGroup, main

log = logging.getLogger(__name__)


class ApiWrapper(Command):
    sub_cmd = SubCommand(help='The command to run')
    with ParamGroup('Common'):
        verbose = Counter('-v', help='Increase logging verbosity (can specify multiple times)')
        env = Option('-e', choices=('dev', 'qa', 'uat', 'prod'), default='prod', help='Environment to connect to')

    def _before_main_(self):
        super()._before_main_()
        log_fmt = '%(asctime)s %(levelname)s %(name)s %(lineno)d %(message)s' if self.verbose > 1 else '%(message)s'
        level = logging.DEBUG if self.verbose else logging.INFO
        logging.basicConfig(level=level, format=log_fmt)


class Show(ApiWrapper, help='Show an object'):
    type = Positional(choices=('foo', 'bar', 'baz'), help='The type of object to show')
    ids = Option('-i', nargs='+', help='The IDs of the objects to show')

    def main(self):
        log.info(f'Would show {self.type} objects: {self.ids}')


class Sync(ApiWrapper, help='Sync group members'):
    dry_run = Flag('-D', help='Print the actions that would be taken instead of taking them')
    with ParamGroup(mutually_exclusive=True, required=True):
        all = Flag('-a', help='Sync all groups')
        with ParamGroup():  # --role and --group can be combined, but neither can be combined with --all
            role = Option('-r', default='all', choices=('all', 'admin', 'user'), help='Sync members with this role')
            group = Option('-g', help='Sync members for this group')

    def main(self):
        prefix = '[DRY RUN] Would sync' if self.dry_run else 'Syncing'
        roles = ['admin', 'user'] if self.role == 'all' else [self.role]
        groups = [self.group] if self.group else ['foo', 'bar', 'baz']
        for group in groups:
            for role in roles:
                log.info(f'{prefix} group={group} members with role={role}')


# region Find subcommands


class Find(ApiWrapper, help='Find objects'):
    sub_cmd = SubCommand(help='What to find')
    limit: int = Option('-L', default=10, help='The number of results to show')

    def main(self):
        for obj in self.find_objects():
            print(obj)

    def find_objects(self):
        raise NotImplementedError


class FindFoo(Find, choice='foo', help='Find foo objects'):
    query = Positional(help='Find foo objects that match the specified query')

    def find_objects(self):
        log.debug(f'Would have run query={self.query!r} in env={self.env}, returning fake results')
        return ['a', 'b', 'c']


class FindBar(Find, choice='bar', help='Find bar objects'):
    pattern = Option('-p', help='Pattern to find')
    show_all = Flag('--all', '-a', help='Show all (default: only even)')

    def find_objects(self):
        objects = {chr(i): i % 2 == 0 for i in range(97, 123)}
        if not self.show_all:
            objects = {c: even for c, even in objects.items() if even}
        if self.pattern:
            objects = {c: even for c, even in objects.items() if fnmatch(c, self.pattern)}
        return objects


class FindBaz(Find, choice='baz', help='Find baz objects'):
    with ParamGroup(description='Filter Choices', mutually_exclusive=True, required=True):
        foo = Option('-f', metavar='NAME', help='Find baz objects related to the foo object with the specified name')
        bar: int = Option('-b', metavar='ID', help='Find baz objects related to the bar object with the specified ID')

    def find_objects(self):
        if self.foo:
            return ['a', 'b', 'c']
        else:
            return [chr(self.bar)]


# endregion


if __name__ == '__main__':
    main()
