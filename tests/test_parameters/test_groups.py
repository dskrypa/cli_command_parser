#!/usr/bin/env python

from typing import Type
from unittest import main

from cli_command_parser import Command, Context
from cli_command_parser.core import get_params
from cli_command_parser.exceptions import (
    UsageError,
    ParameterDefinitionError,
    CommandDefinitionError,
    ParamsMissing,
    ParamConflict,
)
from cli_command_parser.parameters import ParamGroup, Flag, Positional, PassThru, SubCommand, Action, Option
from cli_command_parser.testing import ParserTest


class _GroupTest(ParserTest):
    def assert_cases_for_cmds(self, success_cases, fail_cases, *cmds, exc: Type[Exception] = None):
        for cmd in cmds:
            with self.subTest(cmd=cmd):
                self.assert_parse_results_cases(cmd, success_cases)
                self.assert_parse_fails_cases(cmd, fail_cases, exc)


class GroupTest(_GroupTest):
    def test_plain(self):
        class Foo(Command):
            with ParamGroup() as group:
                bar = Flag('-b')
                baz = Flag('-B')

        success_cases = [
            ([], {'bar': False, 'baz': False}),
            (['-b'], {'bar': True, 'baz': False}),
            (['-B'], {'bar': False, 'baz': True}),
            (['-bB'], {'bar': True, 'baz': True}),
        ]
        self.assert_parse_results_cases(Foo, success_cases)

    def test_params_know_own_group(self):
        class Foo(Command):
            foo = Flag('-f')
            with ParamGroup(mutually_exclusive=True) as group:
                bar = Flag('-b')
                baz = Flag('-B')

        self.assertIs(Foo.foo.group, None)
        self.assertIs(Foo.bar.group, Foo.group)
        self.assertIs(Foo.baz.group, Foo.group)

    def test_reject_double_mutual(self):
        with self.assertRaises(ParameterDefinitionError):
            ParamGroup(mutually_dependent=True, mutually_exclusive=True)

    def test_register_all(self):
        class Foo(Command):
            group = ParamGroup()
            foo = Flag()
            bar = Flag()
            group.register_all([foo, bar])

        self.assertTrue(all(p.group == Foo.group for p in (Foo.foo, Foo.bar)))
        self.assertEqual(2, len(list(Foo.group)))

    def test_repr(self):
        group = ParamGroup('foo', mutually_exclusive=True)
        self.assertIn('m.exclusive=T', repr(group))

    def test_description(self):
        with Context():
            self.assertIn('exclusive', ParamGroup('foo', mutually_exclusive=True).formatter.format_description())

    def test_required_group(self):
        class Foo1(Command):
            with ParamGroup(required=True) as group:
                bar = Flag('-b')
                baz = Flag('-B')

        class Foo2(Command):
            with ParamGroup(required=True):
                bar = Flag('-b')
                baz = Flag('-B')

        success_cases = [
            (['-b'], {'bar': True, 'baz': False}),
            (['-B'], {'bar': False, 'baz': True}),
            (['-bB'], {'bar': True, 'baz': True}),
        ]
        fail_cases = [([], UsageError)]
        self.assert_cases_for_cmds(success_cases, fail_cases, Foo1, Foo2)

    def test_required_param_missing_from_non_required_group(self):
        class Foo(Command):
            with ParamGroup() as group:
                bar = Option('-b', required=True)
                baz = Flag('-B')

        self.assert_parse_fails(Foo, [], ParamsMissing)


class MutuallyExclusiveGroupTest(_GroupTest):
    def test_mutually_exclusive(self):
        class Foo1(Command):
            with ParamGroup(mutually_exclusive=True) as group:
                bar = Flag('-b')
                baz = Flag('-B')

        class Foo2(Command):
            with ParamGroup(mutually_exclusive=True):
                bar = Flag('-b', name='bar')
                baz = Flag('-B', name='baz')

        success_cases = [
            ([], {'bar': False, 'baz': False}),
            (['-b'], {'bar': True, 'baz': False}),
            (['-B'], {'bar': False, 'baz': True}),
        ]
        fail_cases = [(['-bB'], UsageError), (['-B', '-b'], UsageError, 'mutually exclusive - only one is allowed')]
        self.assert_cases_for_cmds(success_cases, fail_cases, Foo1, Foo2)

    def test_positional_nargs_qm(self):
        class Foo1(Command):
            with ParamGroup(mutually_exclusive=True) as group:
                foo = Positional(nargs='?')
                bar = Flag('-b')

        class Foo2(Command):
            with ParamGroup(mutually_exclusive=True):
                foo = Positional(nargs='?')
                bar = Flag('-b')

        success_cases = [
            ([], {'foo': None, 'bar': False}),
            (['a'], {'foo': 'a', 'bar': False}),
            (['-b'], {'foo': None, 'bar': True}),
        ]
        fail_cases = [['-b', 'a'], ['a', '-b']]
        self.assert_cases_for_cmds(success_cases, fail_cases, Foo1, Foo2, exc=UsageError)

    def test_bad_members_rejected(self):
        fail_cases = [
            (Positional, {}),
            (PassThru, {}),
            (SubCommand, {}),
            (Action, {}),
            (Option, {'required': True}),
        ]
        for param_cls, kwargs in fail_cases:
            with self.subTest(param_cls=param_cls, named=True), self.assertRaises(CommandDefinitionError):

                class Foo1(Command):
                    with ParamGroup(mutually_exclusive=True) as group:
                        foo = param_cls(**kwargs)
                        bar = Flag('-b')

            with self.subTest(param_cls=param_cls, named=False), self.assertRaises(CommandDefinitionError):

                class Foo2(Command):
                    with ParamGroup(mutually_exclusive=True):
                        foo = param_cls(**kwargs)
                        bar = Flag('-b')

    def test_me_and_plain_groups(self):
        class Foo1(Command):
            with ParamGroup() as a:
                foo = Flag('-f')
            with ParamGroup(mutually_exclusive=True) as b:
                bar = Flag('-b')
                baz = Flag('-B')

        class Foo2(Command):
            with ParamGroup():
                foo = Flag('-f')
            with ParamGroup(mutually_exclusive=True):
                bar = Flag('-b')
                baz = Flag('-B')

        success_cases = [
            ([], {'foo': False, 'bar': False, 'baz': False}),
            (['-b'], {'foo': False, 'bar': True, 'baz': False}),
            (['-B'], {'foo': False, 'bar': False, 'baz': True}),
            (['-f'], {'foo': True, 'bar': False, 'baz': False}),
            (['-fb'], {'foo': True, 'bar': True, 'baz': False}),
            (['-fB'], {'foo': True, 'bar': False, 'baz': True}),
        ]
        fail_cases = [['-bB'], ['-B', '-b'], ['-fbB'], ['-f', '-B', '-b']]
        self.assert_cases_for_cmds(success_cases, fail_cases, Foo1, Foo2, exc=UsageError)

    def test_required_param_in_nested_groups_doesnt_block_other_group(self):
        class Foo(Command):
            with ParamGroup(mutually_exclusive=True):
                with ParamGroup():
                    a = Option('-a', required=True)
                    b = Option('-b')
                with ParamGroup():
                    c = Option('-c', required=True)
                    d = Option('-d', required=True)
                    e = Option('-e')
                f = Option('-f')

        success_cases = [
            ([], {'a': None, 'b': None, 'c': None, 'd': None, 'e': None, 'f': None}),
            (['-f', '1'], {'a': None, 'b': None, 'c': None, 'd': None, 'e': None, 'f': '1'}),
            (['-a', '1'], {'a': '1', 'b': None, 'c': None, 'd': None, 'e': None, 'f': None}),
            (['-a', '1', '-b', '2'], {'a': '1', 'b': '2', 'c': None, 'd': None, 'e': None, 'f': None}),
            (['-c', '1', '-d', '2'], {'a': None, 'b': None, 'c': '1', 'd': '2', 'e': None, 'f': None}),
            (['-c', '1', '-d', '2', '-e', '3'], {'a': None, 'b': None, 'c': '1', 'd': '2', 'e': '3', 'f': None}),
        ]
        self.assert_parse_results_cases(Foo, success_cases)
        fail_cases = [
            ['-a', '1', '-c', '3'],
            ['-a', '1', '-f', '3'],
            ['-b', '1', '-f', '3'],
            ['-a', '1', '-d', '3'],
            ['-a', '1', '-e', '3'],
            ['-a', '1', '-b', '2', '-c', '3'],
            ['-a', '1', '-b', '2', '-d', '3'],
            ['-a', '1', '-b', '2', '-e', '3'],
            ['-a', '1', '-b', '2', '-f', '3'],
            ['-a', '1', '-b', '2', '-f', '3'],
            ['-a', '1', '-b', '2', '-f', '3'],
            ['-c', '3'],
            ['-d', '3'],
            ['-c', '3', '-e', '5'],
            ['-d', '3', '-e', '5'],
            ['-c', '3', '-d', '5', '-f', '6'],
            ['-d', '3', '-e', '5', '-f', '6'],
            ['-c', '3', '-f', '5'],
            ['-d', '3', '-f', '5'],
        ]
        self.assert_parse_fails_cases(Foo, fail_cases, UsageError)


class MutuallyDependentGroupTest(_GroupTest):
    def test_mutually_dependent(self):
        class Foo1(Command):
            with ParamGroup(mutually_dependent=True) as group:
                bar = Flag('-b')
                baz = Flag('-B')

        class Foo2(Command):
            with ParamGroup(mutually_dependent=True):
                bar = Flag('-b')
                baz = Flag('-B')

        success_cases = [
            ([], {'bar': False, 'baz': False}),
            (['-bB'], {'bar': True, 'baz': True}),
            (['-b', '-B'], {'bar': True, 'baz': True}),
        ]
        fail_cases = [(['-b'], UsageError), (['-B'], UsageError)]
        self.assert_cases_for_cmds(success_cases, fail_cases, Foo1, Foo2)


class NestedGroupTest(_GroupTest):
    def test_nested_me_in_md(self):
        class Foo1(Command):
            with ParamGroup(mutually_dependent=True) as outer:
                with ParamGroup(mutually_exclusive=True) as inner:
                    foo = Flag()
                    bar = Flag()
                baz = Flag()

        class Foo2(Command):
            with ParamGroup(mutually_dependent=True):
                with ParamGroup(mutually_exclusive=True):
                    foo = Flag()
                    bar = Flag()
                baz = Flag()

        self.assertIn(Foo1.foo, Foo1.inner)
        self.assertIn(Foo1.bar, Foo1.inner)
        self.assertIn(Foo1.baz, Foo1.outer)
        self.assertNotIn(Foo1.foo, Foo1.outer)
        self.assertNotIn(Foo1.bar, Foo1.outer)
        self.assertNotIn(Foo1.baz, Foo1.inner)
        self.assertIn(Foo1.inner, Foo1.outer)

        success_cases = [
            (['--foo', '--baz'], {'foo': True, 'bar': False, 'baz': True}),
            (['--bar', '--baz'], {'foo': False, 'bar': True, 'baz': True}),
        ]
        fail_cases = [['--foo', '--bar', '--baz'], ['--foo', '--bar'], ['--foo'], ['--bar'], ['--baz']]
        self.assert_cases_for_cmds(success_cases, fail_cases, Foo1, Foo2, exc=UsageError)

    def test_nested_me_in_me(self):
        class Foo1(Command):
            with ParamGroup(mutually_exclusive=True) as outer:
                with ParamGroup(mutually_exclusive=True) as inner:
                    foo = Flag()
                    bar = Flag()
                baz = Flag()

        class Foo2(Command):
            with ParamGroup(mutually_exclusive=True):
                with ParamGroup(mutually_exclusive=True):
                    foo = Flag()
                    bar = Flag()
                baz = Flag()

        success_cases = [
            (['--foo'], {'foo': True, 'bar': False, 'baz': False}),
            (['--bar'], {'foo': False, 'bar': True, 'baz': False}),
            (['--baz'], {'foo': False, 'bar': False, 'baz': True}),
        ]
        fail_cases = [['--foo', '--bar', '--baz'], ['--foo', '--bar'], ['--foo', '--baz'], ['--bar', '--baz']]
        self.assert_cases_for_cmds(success_cases, fail_cases, Foo1, Foo2, exc=UsageError)

    def test_nested_md_in_me(self):
        class Foo1(Command):
            with ParamGroup(mutually_exclusive=True) as outer:
                with ParamGroup(mutually_dependent=True) as inner:
                    foo = Flag()
                    bar = Flag()
                baz = Flag()

        class Foo2(Command):
            with ParamGroup(mutually_exclusive=True):
                with ParamGroup(mutually_dependent=True):
                    foo = Flag()
                    bar = Flag()
                baz = Flag()

        success_cases = [
            (['--foo', '--bar'], {'foo': True, 'bar': True, 'baz': False}),
            (['--baz'], {'foo': False, 'bar': False, 'baz': True}),
        ]
        fail_cases = [['--foo', '--bar', '--baz'], ['--foo', '--baz'], ['--bar', '--baz']]
        self.assert_cases_for_cmds(success_cases, fail_cases, Foo1, Foo2, exc=UsageError)

    def test_nested_md_in_md(self):
        class Foo1(Command):
            with ParamGroup(mutually_dependent=True) as outer:
                with ParamGroup(mutually_dependent=True) as inner:
                    foo = Flag()
                    bar = Flag()
                baz = Flag()

        class Foo2(Command):
            with ParamGroup(mutually_dependent=True):
                with ParamGroup(mutually_dependent=True):
                    foo = Flag()
                    bar = Flag()
                baz = Flag()

        fail_cases = [['--foo', '--bar'], ['--foo', '--baz'], ['--bar', '--baz'], ['--foo'], ['--bar'], ['--baz']]
        for cmd in (Foo1, Foo2):
            with self.subTest(cmd=cmd):
                self.assert_parse_results(cmd, ['--foo', '--bar', '--baz'], {'foo': True, 'bar': True, 'baz': True})
                self.assert_parse_fails_cases(cmd, fail_cases, UsageError)

    def test_nested_me_in_me_with_plain(self):
        class Foo1(Command):
            with ParamGroup(mutually_exclusive=True) as outer:
                with ParamGroup(mutually_exclusive=True) as inner:
                    a = Flag('-a')
                    b = Flag('-b')
                c = Flag('-c')
            with ParamGroup() as plain:
                d = Flag('-d')

        class Foo2(Command):
            with ParamGroup(mutually_exclusive=True):
                with ParamGroup(mutually_exclusive=True):
                    a = Flag('-a')
                    b = Flag('-b')
                c = Flag('-c')
            with ParamGroup():
                d = Flag('-d')

        success_cases = [
            (['-a'], {'a': True, 'b': False, 'c': False, 'd': False}),
            (['-b'], {'a': False, 'b': True, 'c': False, 'd': False}),
            (['-c'], {'a': False, 'b': False, 'c': True, 'd': False}),
            (['-ad'], {'a': True, 'b': False, 'c': False, 'd': True}),
            (['-bd'], {'a': False, 'b': True, 'c': False, 'd': True}),
            (['-cd'], {'a': False, 'b': False, 'c': True, 'd': True}),
        ]
        fail_cases = [['-abc'], ['-ab'], ['-ac'], ['-bc'], ['-abcd'], ['-abd'], ['-acd'], ['-bcd']]
        self.assert_cases_for_cmds(success_cases, fail_cases, Foo1, Foo2, exc=UsageError)

    def test_non_me_nested_in_me_with_me(self):
        class Foo1(Command):
            with ParamGroup(mutually_exclusive=True) as outer:
                with ParamGroup(mutually_exclusive=True) as inner:
                    a = Flag('-a')
                    b = Flag('-b')
                c = Flag('-c')
                with ParamGroup() as plain:
                    d = Flag('-d')
                    e = Flag('-e')

        class Foo2(Command):
            with ParamGroup(mutually_exclusive=True):
                with ParamGroup(mutually_exclusive=True):
                    a = Flag('-a')
                    b = Flag('-b')
                c = Flag('-c')
                with ParamGroup():
                    d = Flag('-d')
                    e = Flag('-e')

        with self.subTest('group sort test'):
            self.assertIn(Foo1.plain, Foo1.outer)
            self.assertIn(Foo1.inner, Foo1.outer)
            self.assertIn(Foo1.c, Foo1.outer)
            expected = [Foo1.inner, Foo1.plain, Foo1.outer]
            self.assertListEqual(expected, get_params(Foo1).groups)
            self.assertListEqual(expected, sorted([Foo1.plain, Foo1.outer, Foo1.inner]))

        success_cases = [
            (['-a'], {'a': True, 'b': False, 'c': False, 'd': False, 'e': False}),
            (['-b'], {'a': False, 'b': True, 'c': False, 'd': False, 'e': False}),
            (['-c'], {'a': False, 'b': False, 'c': True, 'd': False, 'e': False}),
            (['-d'], {'a': False, 'b': False, 'c': False, 'd': True, 'e': False}),
            (['-e'], {'a': False, 'b': False, 'c': False, 'd': False, 'e': True}),
            (['-de'], {'a': False, 'b': False, 'c': False, 'd': True, 'e': True}),
        ]
        # fmt: off
        fail_cases = [
            ['-abc'], ['-ab'], ['-ac'], ['-bc'],
            ['-abcd'], ['-abd'], ['-acd'], ['-bcd'],
            ['-abce'], ['-abe'], ['-ace'], ['-bce'],
            ['-abcde'], ['-abde'], ['-acde'], ['-bcde'],
            ['-ad'], ['-ae'], ['-ade'],
            ['-bd'], ['-be'], ['-bde'],
            ['-cd'], ['-ce'], ['-cde'],
        ]
        # fmt: on
        self.assert_cases_for_cmds(success_cases, fail_cases, Foo1, Foo2, exc=UsageError)

    def test_nested_group_sorting_1(self):
        class Foo(Command):
            with ParamGroup() as outer:
                with ParamGroup() as inner_1:
                    a = Flag('-a')
                    with ParamGroup() as nested_inner_2:
                        c = Flag('-c')
                with ParamGroup() as inner_2:
                    b = Flag('-b')
                    with ParamGroup() as nested_inner_1:
                        d = Flag('-d')

        expected = [Foo.nested_inner_2, Foo.nested_inner_1, Foo.inner_1, Foo.inner_2, Foo.outer]
        self.assertListEqual(expected, get_params(Foo).groups)

    def test_nested_group_sorting_2(self):
        class Foo(Command):
            with ParamGroup() as outer_1:
                a = Flag('-a')
                with ParamGroup() as inner_2:
                    c = Flag('-c')

            with ParamGroup() as outer_2:
                b = Flag('-b')
                with ParamGroup() as inner_1:
                    d = Flag('-d')

        expected = [Foo.inner_2, Foo.inner_1, Foo.outer_1, Foo.outer_2]
        self.assertListEqual(expected, get_params(Foo).groups)

    def test_nested_group_sorting_3(self):
        class Foo(Command):
            with ParamGroup() as outer_1:
                a = Flag('-a')
                with ParamGroup() as inner_2:
                    c = Flag('-c')
                with ParamGroup() as inner_3:
                    d = Flag('-d')

            with ParamGroup() as outer_2:
                b = Flag('-b')
                with ParamGroup() as inner_1:
                    e = Flag('-e')
                with ParamGroup() as inner_4:
                    f = Flag('-f')
                    with ParamGroup() as nested_inner_1:
                        g = Flag('-g')

        expected = [Foo.nested_inner_1, Foo.inner_2, Foo.inner_3, Foo.inner_1, Foo.inner_4, Foo.outer_1, Foo.outer_2]
        self.assertListEqual(expected, get_params(Foo).groups)

    def test_me_precedence_over_md(self):
        class TestDE(Command, error_handler=None):
            with ParamGroup(mutually_dependent=True):
                a = Flag()
                b = Flag()
                with ParamGroup(mutually_exclusive=True):
                    c = Flag()
                    d = Flag()

        class TestED(Command, error_handler=None):
            with ParamGroup(mutually_exclusive=True):
                a = Flag()
                b = Flag()
                with ParamGroup(mutually_dependent=True):
                    c = Flag()
                    d = Flag()

        cases = [(TestDE, ['--b', '--c', '--d']), (TestED, ['--b', '--c'])]
        for cmd, args in cases:
            with self.subTest(cmd=cmd), self.assertRaises(ParamConflict):
                cmd.parse_and_run(args)


if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    try:
        main(warnings='ignore', verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
