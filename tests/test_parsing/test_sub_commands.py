#!/usr/bin/env python

from unittest import main, skip

from cli_command_parser import Command, Positional, Option, Flag, SubCommand, ParamGroup
from cli_command_parser.testing import ParserTest


class SubCmdParsingTest(ParserTest):
    @skip('Cross-param positional conflict detection needs to be implemented')  # TODO #8
    def test_ambiguous_positional_vs_subcommand_single(self):
        class Base(Command):
            sub_cmd = SubCommand()

        class Show(Base):
            type = Positional(choices=('foo', 'bar'))

        class ShowFooBaz(Base, choice='show foo baz'):
            pass

        success_cases = [
            (['show', 'foo'], {'sub_cmd': 'show', 'type': 'foo'}),
            (['show', 'bar'], {'sub_cmd': 'show', 'type': 'bar'}),
            (['show', 'foo', 'baz'], {'sub_cmd': 'show foo baz'}),
        ]
        self.assert_parse_results_cases(Base, success_cases)

    @skip('Cross-param positional conflict detection needs to be implemented')  # TODO #8
    def test_ambiguous_positional_vs_subcommand_multiple(self):
        class Base(Command):
            sub_cmd = SubCommand()
            a = Flag('-a')

        class Show(Base):
            type = Positional(choices=('foo', 'bar'))
            b = Flag('-b')

        class ShowBaz(Base, choice='show baz'):
            c = Flag('-c')

        class ShowFooBars(Base, choice='show foo bars'):
            d = Flag('-d')

        success_cases = [
            (['show', 'foo'], {'sub_cmd': 'show', 'type': 'foo', 'a': False, 'b': False}),
            (['show', 'bar'], {'sub_cmd': 'show', 'type': 'bar', 'a': False, 'b': False}),
            (['show', 'baz'], {'sub_cmd': 'show baz', 'a': False, 'c': False}),
            (['show', 'foo', 'bars'], {'sub_cmd': 'show foo bars', 'a': False, 'd': False}),
            (['show', 'foo bars'], {'sub_cmd': 'show foo bars', 'a': False, 'd': False}),
            # With flags
            # (['show', '-a', 'foo'], {'sub_cmd': 'show', 'type': 'foo', 'a': True, 'b': False}),
            # (['show', '-a', 'bar'], {'sub_cmd': 'show', 'type': 'bar', 'a': True, 'b': False}),
            # (['show', '-b', 'foo'], {'sub_cmd': 'show', 'type': 'foo', 'a': False, 'b': True}),
            # (['show', '-b', 'bar'], {'sub_cmd': 'show', 'type': 'bar', 'a': False, 'b': True}),
            # (['show', 'foo', '-b'], {'sub_cmd': 'show', 'type': 'foo', 'a': False, 'b': True}),
            # (['show', 'bar', '-b'], {'sub_cmd': 'show', 'type': 'bar', 'a': False, 'b': True}),
            # # Space names
            # (['show', '-a', 'baz'], {'sub_cmd': 'show baz', 'a': True, 'c': False}),
            # (['show', '-c', 'baz'], {'sub_cmd': 'show baz', 'a': False, 'c': True}),
            # (['show', '-a', 'foo', 'bars'], {'sub_cmd': 'show foo bars', 'a': True, 'd': False}),
            # (['show', '-a', 'foo bars'], {'sub_cmd': 'show foo bars', 'a': True, 'd': False}),
            # (['show', '-d', 'foo', 'bars'], {'sub_cmd': 'show foo bars', 'a': False, 'd': True}),
            # (['show', '-d', 'foo bars'], {'sub_cmd': 'show foo bars', 'a': False, 'd': True}),
        ]
        self.assert_parse_results_cases(Base, success_cases)

    def test_ambiguous_positional_vs_subcommand(self):
        class Base(Command):
            sub_cmd = SubCommand()

        class Show(Base):
            type = Positional(choices=('schedule', 'schedules', 'ticket', 'tickets'))
            with ParamGroup(mutually_exclusive=True):
                ids = Option('-i', nargs='+')
                all = Flag('-A')

            format = Option('-f', choices=('table', 'json', 'yaml'), default='yaml')

        class ShowUsers(Base, choices=('show user', 'show users')):
            with ParamGroup(mutually_exclusive=True):
                ids = Option('-i', nargs='+')
                all = Flag('-A')
                groups = Option('-g', nargs='+', help='Show users who are members of the given groups')

            format = Option('-f', choices=('table', 'json', 'yaml'), default='table')

        class ShowGroups(Base, choices=('show group', 'show groups')):
            with ParamGroup(mutually_exclusive=True):
                ids = Option('-i', nargs='+')
                all = Flag('-A')
                names = Option('-n', nargs='+')

            format = Option('-f', choices=('table', 'json', 'yaml'), default='yaml')

        # TODO:
        # class ShowScheduleOverrides(Base, choices=('show schedule override', 'show schedule overrides')):
        #     with ParamGroup(mutually_exclusive=True):
        #         ids = Option('-i', nargs='+')
        #         all = Flag('-A')
        #
        #     format = Option('-f', choices=('table', 'json', 'yaml'), default='yaml')
        #     num: int = Option('-n', default=0)

        base = {'ids': [], 'all': False, 'format': 'yaml'}

        # fmt: off
        success_cases = [
            (['show', 'user', '-i', '12'], {**base, 'sub_cmd': 'show user', 'ids': ['12'], 'groups': [], 'format': 'table'}),
            (['show', 'group', '-i', '34'], {**base, 'sub_cmd': 'show group', 'ids': ['34'], 'names': []}),
            (['show', 'schedule', '-i', '45'], {**base, 'sub_cmd': 'show', 'type': 'schedule', 'ids': ['45']}),
            # (['show', 'schedule override', '-i', '56'], {**base, 'sub_cmd': 'show schedule override', 'ids': ['56'], 'num': 0}),
        ]
        # fmt: on
        self.assert_parse_results_cases(Base, success_cases)

    @skip('Subcommand param override handling needs to be implemented')  # TODO
    def test_subclass_local_and_remote_choices_with_param_overrides(self):
        class Base(Command):
            sub_cmd = SubCommand()

        class Show(Base):
            type = SubCommand(local_choices=('schedule', 'schedules', 'ticket', 'tickets'))
            with ParamGroup(mutually_exclusive=True):
                ids = Option('-i', nargs='+')
                all = Flag('-A')

            format = Option('-f', choices=('table', 'json', 'yaml'), default='yaml')

        class ShowUsers(Show, choices=('user', 'users')):
            with ParamGroup(mutually_exclusive=True):
                ids = Option('-i', nargs='+')
                all = Flag('-A')
                groups = Option('-g', nargs='+', help='Show users who are members of the given groups')

            format = Option('-f', choices=('table', 'json', 'yaml'), default='table')

        class ShowGroups(Show, choices=('group', 'groups')):
            with ParamGroup(mutually_exclusive=True):
                ids = Option('-i', nargs='+')
                all = Flag('-A')
                names = Option('-n', nargs='+')

        class ShowScheduleOverrides(Show, choices=('schedule override', 'schedule overrides')):
            num: int = Option('-n', default=0)

        base = {'sub_cmd': 'show', 'ids': [], 'all': False, 'format': 'yaml'}

        success_cases = [
            (['show', 'user', '-i', '12'], {**base, 'type': 'user', 'ids': ['12'], 'groups': [], 'format': 'table'}),
            (['show', 'group', '-i', '34'], {**base, 'type': 'group', 'ids': ['34'], 'names': []}),
            (['show', 'schedule', '-i', '45'], {**base, 'type': 'schedule', 'ids': ['45']}),
            (['show', 'schedule override', '-i', '56'], {**base, 'type': 'schedule override', 'ids': ['56'], 'num': 0}),
        ]
        self.assert_parse_results_cases(Base, success_cases)


if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    try:
        main(verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
