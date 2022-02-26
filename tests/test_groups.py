#!/usr/bin/env python

from unittest import main

from command_parser import Command, UsageError, ParameterDefinitionError, CommandDefinitionError
from command_parser.parameters import ParamGroup, Flag, Positional, PassThru, SubCommand, Action, Option
from command_parser.testing import ParserTest


class GroupTest(ParserTest):
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
        self.assertIn('exclusive', ParamGroup('foo', mutually_exclusive=True).format_description())

    def test_required_group(self):
        class Foo(Command):
            with ParamGroup(required=True) as group:
                bar = Flag('-b')
                baz = Flag('-B')

        success_cases = [
            (['-b'], {'bar': True, 'baz': False}),
            (['-B'], {'bar': False, 'baz': True}),
            (['-bB'], {'bar': True, 'baz': True}),
        ]
        self.assert_parse_results_cases(Foo, success_cases)
        fail_cases = [([], UsageError)]
        self.assert_parse_fails_cases(Foo, fail_cases)


class MutuallyExclusiveGroupTest(ParserTest):
    def test_mutually_exclusive(self):
        class Foo(Command):
            with ParamGroup(mutually_exclusive=True) as group:
                bar = Flag('-b')
                baz = Flag('-B')

        success_cases = [
            ([], {'bar': False, 'baz': False}),
            (['-b'], {'bar': True, 'baz': False}),
            (['-B'], {'bar': False, 'baz': True}),
        ]
        self.assert_parse_results_cases(Foo, success_cases)
        fail_cases = [(['-bB'], UsageError), (['-B', '-b'], UsageError, 'mutually exclusive - only one is allowed')]
        self.assert_parse_fails_cases(Foo, fail_cases)

    def test_positional_nargs_qm(self):
        class Foo(Command):
            with ParamGroup(mutually_exclusive=True) as group:
                foo = Positional(nargs='?')
                bar = Flag('-b')

        success_cases = [
            ([], {'foo': None, 'bar': False}),
            (['a'], {'foo': 'a', 'bar': False}),
            (['-b'], {'foo': None, 'bar': True}),
        ]
        self.assert_parse_results_cases(Foo, success_cases)
        self.assert_parse_fails_cases(Foo, [['-b', 'a'], ['a', '-b']], UsageError)

    def test_bad_members_rejected(self):
        fail_cases = [
            (Positional, {}),
            (PassThru, {}),
            (SubCommand, {}),
            (Action, {}),
            (Option, {'required': True}),
        ]
        for param_cls, kwargs in fail_cases:
            with self.subTest(param_cls=param_cls), self.assertRaises(CommandDefinitionError):

                class Foo(Command):
                    with ParamGroup(mutually_exclusive=True) as group:
                        foo = param_cls(**kwargs)
                        bar = Flag('-b')

    def test_me_and_plain_groups(self):
        class Foo(Command):
            with ParamGroup() as a:
                foo = Flag('-f')
            with ParamGroup(mutually_exclusive=True) as b:
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
        self.assert_parse_results_cases(Foo, success_cases)
        fail_cases = [['-bB'], ['-B', '-b'], ['-fbB'], ['-f', '-B', '-b']]
        self.assert_parse_fails_cases(Foo, fail_cases, UsageError)


class MutuallyDependentGroupTest(ParserTest):
    def test_mutually_dependent(self):
        class Foo(Command):
            with ParamGroup(mutually_dependent=True) as group:
                bar = Flag('-b')
                baz = Flag('-B')

        success_cases = [
            ([], {'bar': False, 'baz': False}),
            (['-bB'], {'bar': True, 'baz': True}),
            (['-b', '-B'], {'bar': True, 'baz': True}),
        ]
        self.assert_parse_results_cases(Foo, success_cases)
        fail_cases = [(['-b'], UsageError), (['-B'], UsageError)]
        self.assert_parse_fails_cases(Foo, fail_cases)


class NestedGroupTest(ParserTest):
    def test_nested_me_in_md(self):
        class Foo(Command):
            with ParamGroup(mutually_dependent=True) as outer:
                with ParamGroup(mutually_exclusive=True) as inner:
                    foo = Flag()
                    bar = Flag()
                baz = Flag()

        self.assertIn(Foo.foo, Foo.inner)
        self.assertIn(Foo.bar, Foo.inner)
        self.assertIn(Foo.baz, Foo.outer)
        self.assertNotIn(Foo.foo, Foo.outer)
        self.assertNotIn(Foo.bar, Foo.outer)
        self.assertNotIn(Foo.baz, Foo.inner)
        self.assertIn(Foo.inner, Foo.outer)

        success_cases = [
            (['--foo', '--baz'], {'foo': True, 'bar': False, 'baz': True}),
            (['--bar', '--baz'], {'foo': False, 'bar': True, 'baz': True}),
        ]
        self.assert_parse_results_cases(Foo, success_cases)
        fail_cases = [['--foo', '--bar', '--baz'], ['--foo', '--bar'], ['--foo'], ['--bar'], ['--baz']]
        self.assert_parse_fails_cases(Foo, fail_cases, UsageError)

    def test_nested_me_in_me(self):
        class Foo(Command):
            with ParamGroup(mutually_exclusive=True) as outer:
                with ParamGroup(mutually_exclusive=True) as inner:
                    foo = Flag()
                    bar = Flag()
                baz = Flag()

        success_cases = [
            (['--foo'], {'foo': True, 'bar': False, 'baz': False}),
            (['--bar'], {'foo': False, 'bar': True, 'baz': False}),
            (['--baz'], {'foo': False, 'bar': False, 'baz': True}),
        ]
        self.assert_parse_results_cases(Foo, success_cases)
        fail_cases = [['--foo', '--bar', '--baz'], ['--foo', '--bar'], ['--foo', '--baz'], ['--bar', '--baz']]
        self.assert_parse_fails_cases(Foo, fail_cases, UsageError)

    def test_nested_md_in_me(self):
        class Foo(Command):
            with ParamGroup(mutually_exclusive=True) as outer:
                with ParamGroup(mutually_dependent=True) as inner:
                    foo = Flag()
                    bar = Flag()
                baz = Flag()

        success_cases = [
            (['--foo', '--bar'], {'foo': True, 'bar': True, 'baz': False}),
            (['--baz'], {'foo': False, 'bar': False, 'baz': True}),
        ]
        self.assert_parse_results_cases(Foo, success_cases)
        fail_cases = [['--foo', '--bar', '--baz'], ['--foo', '--baz'], ['--bar', '--baz']]
        self.assert_parse_fails_cases(Foo, fail_cases, UsageError)

    def test_nested_md_in_md(self):
        class Foo(Command):
            with ParamGroup(mutually_dependent=True) as outer:
                with ParamGroup(mutually_dependent=True) as inner:
                    foo = Flag()
                    bar = Flag()
                baz = Flag()

        self.assert_parse_results(Foo, ['--foo', '--bar', '--baz'], {'foo': True, 'bar': True, 'baz': True})
        fail_cases = [['--foo', '--bar'], ['--foo', '--baz'], ['--bar', '--baz'], ['--foo'], ['--bar'], ['--baz']]
        self.assert_parse_fails_cases(Foo, fail_cases, UsageError)

    def test_nested_me_in_me_with_plain(self):
        class Foo(Command):
            with ParamGroup(mutually_exclusive=True) as outer:
                with ParamGroup(mutually_exclusive=True) as inner:
                    a = Flag('-a')
                    b = Flag('-b')
                c = Flag('-c')
            with ParamGroup() as plain:
                d = Flag('-d')

        success_cases = [
            (['-a'], {'a': True, 'b': False, 'c': False, 'd': False}),
            (['-b'], {'a': False, 'b': True, 'c': False, 'd': False}),
            (['-c'], {'a': False, 'b': False, 'c': True, 'd': False}),
            (['-ad'], {'a': True, 'b': False, 'c': False, 'd': True}),
            (['-bd'], {'a': False, 'b': True, 'c': False, 'd': True}),
            (['-cd'], {'a': False, 'b': False, 'c': True, 'd': True}),
        ]
        self.assert_parse_results_cases(Foo, success_cases)
        fail_cases = [['-abc'], ['-ab'], ['-ac'], ['-bc'], ['-abcd'], ['-abd'], ['-acd'], ['-bcd']]
        self.assert_parse_fails_cases(Foo, fail_cases, UsageError)

    def test_non_me_nested_in_me_with_me(self):
        class Foo(Command):
            with ParamGroup(mutually_exclusive=True) as outer:
                with ParamGroup(mutually_exclusive=True) as inner:
                    a = Flag('-a')
                    b = Flag('-b')
                c = Flag('-c')
                with ParamGroup() as plain:
                    d = Flag('-d')
                    e = Flag('-e')

        with self.subTest('group sort test'):
            self.assertIn(Foo.plain, Foo.outer)
            self.assertIn(Foo.inner, Foo.outer)
            self.assertIn(Foo.c, Foo.outer)
            expected = [Foo.inner, Foo.plain, Foo.outer]
            self.assertListEqual(expected, Foo.params.groups)
            self.assertListEqual(expected, sorted([Foo.plain, Foo.outer, Foo.inner]))

        success_cases = [
            (['-a'], {'a': True, 'b': False, 'c': False, 'd': False, 'e': False}),
            (['-b'], {'a': False, 'b': True, 'c': False, 'd': False, 'e': False}),
            (['-c'], {'a': False, 'b': False, 'c': True, 'd': False, 'e': False}),
            (['-d'], {'a': False, 'b': False, 'c': False, 'd': True, 'e': False}),
            (['-e'], {'a': False, 'b': False, 'c': False, 'd': False, 'e': True}),
            (['-de'], {'a': False, 'b': False, 'c': False, 'd': True, 'e': True}),
        ]
        self.assert_parse_results_cases(Foo, success_cases)
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
        self.assert_parse_fails_cases(Foo, fail_cases, UsageError)

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
        self.assertListEqual(expected, Foo.params.groups)

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
        self.assertListEqual(expected, Foo.params.groups)

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
        self.assertListEqual(expected, Foo.params.groups)


if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    try:
        main(warnings='ignore', verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
