#!/usr/bin/env python

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Collection, Sequence, Iterable, Union
from unittest import TestCase, main
from unittest.mock import Mock

from command_parser import Command, Counter, Option, Flag
from command_parser.args import Args
from command_parser.exceptions import (
    NoSuchOption,
    UsageError,
    ParameterDefinitionError,
    CommandDefinitionError,
    ParamUsageError,
    MissingArgument,
    BadArgument,
    InvalidChoice,
)
from command_parser.parameters import parameter_action, PassThru, Positional, SubCommand, ParamGroup, ActionFlag
from command_parser.testing import ParserTest


class PositionalTest(TestCase):
    pass


class OptionTest(ParserTest):
    def test_choice_ok(self):
        class Foo(Command):
            foo = Option('-f', choices=('a', 'b'))

        self.assertEqual(Foo.parse(['-f', 'a']).foo, 'a')
        self.assertEqual(Foo.parse(['-f', 'b']).foo, 'b')
        self.assertEqual(Foo.parse(['--foo', 'a']).foo, 'a')
        self.assertEqual(Foo.parse(['--foo', 'b']).foo, 'b')

    def test_choice_bad(self):
        class Foo(Command):
            foo = Option('-f', choices=('a', 'b'))

        with self.assertRaises(UsageError):
            Foo.parse(['-f', 'c'])

    def test_instance_values(self):
        class Foo(Command):
            foo = Option('-f', choices=('a', 'b'))

        a = Foo.parse(['-f', 'a'])
        b = Foo.parse(['-f', 'b'])
        self.assertEqual(a.foo, 'a')
        self.assertEqual(b.foo, 'b')

    def test_value_missing(self):
        class Foo(Command):
            foo = Flag('-f')
            bar = Option('-b')

        cases = (
            ['--foo', '--bar'],
            ['--foo', '-b'],
            ['--bar', '--foo'],
            ['-b', '--foo'],
            ['-f', '--bar'],
            ['-f', '-b'],
            ['--bar', '-f'],
            ['-b', '-f'],
            ['-b'],
            ['--bar'],
        )
        for case in cases:
            with self.subTest(case=case), self.assertRaises(MissingArgument):
                Foo.parse(case)

        self.assertTrue(Foo.parse(['--foo']).foo)

    def test_invalid_value(self):
        class Foo(Command):
            bar = Option(type=Mock(side_effect=TypeError))

        with self.assertRaises(BadArgument):
            Foo.parse(['--bar', '1'])

    def test_nargs_0_rejected(self):
        fail_cases = [
            ({'nargs': '?'}, ParameterDefinitionError, 'use Flag or Counter for Options with 0 args'),
            ({'nargs': 0}, ParameterDefinitionError),
            ({'nargs': (0, 2)}, ParameterDefinitionError),
            ({'nargs': range(2)}, ParameterDefinitionError),
        ]
        self.assert_call_fails_cases(Option, fail_cases)

    def test_bad_option_strs_rejected(self):
        fail_cases = ['---foo', '-f-', '-foo--', '--foo-', '--foo=', '-f=', '-foo=', '=', '-', '--', '---', '-=', '--=']
        for option_str in fail_cases:
            with self.subTest(option_str=option_str), self.assertRaises(ParameterDefinitionError):
                Option(option_str)


class FlagTest(ParserTest):
    def test_default_consts(self):
        cases = [(True, False), (False, True)]
        for default, expected in cases:
            with self.subTest(default=default, expected=expected):
                self.assertEqual(expected, Flag(default=default).const)

        self.assert_call_fails(
            Flag, {'default': 42}, ParameterDefinitionError, "Missing parameter='const' for Flag with default=42"
        )

    def test_default_defaults(self):
        cases = [(True, False), (False, True), (42, None)]
        for const, expected in cases:
            with self.subTest(const=const, expected=expected):
                self.assertEqual(expected, Flag(const=const).default)

    def test_annotation_ignored(self):
        for annotation in (bool, int, str, None):
            with self.subTest(annotation=annotation):

                class Foo(Command):
                    bar: annotation = Flag()

                self.assert_parse_results_cases(Foo, [(['--bar'], {'bar': True}), ([], {'bar': False})])

    def test_store_false(self):
        class Foo(Command):
            bar = Flag(default=True)

        self.assert_parse_results_cases(Foo, [(['--bar'], {'bar': False}), ([], {'bar': True})])

    def test_store_const(self):
        class Foo(Command):
            bar = Flag('-b', const=42)

        self.assert_parse_results_cases(Foo, [(['--bar'], {'bar': 42}), ([], {'bar': None}), (['-bb'], {'bar': 42})])

    def test_append_default(self):
        class Foo(Command):
            bar = Flag('-b', action='append_const')

        success_cases = [(['--bar'], {'bar': [True]}), ([], {'bar': []}), (['-bb'], {'bar': [True, True]})]
        self.assert_parse_results_cases(Foo, success_cases)

    def test_append_const(self):
        class Foo(Command):
            bar = Flag('-b', const=42, action='append_const')

        success_cases = [(['--bar'], {'bar': [42]}), ([], {'bar': []}), (['-bb'], {'bar': [42, 42]})]
        self.assert_parse_results_cases(Foo, success_cases)


class CounterTest(ParserTest):
    def test_counter_default(self):
        class Foo(Command):
            verbose: int = Counter('-v')

        self.assertEqual(Foo.parse([]).verbose, 0)

    def test_counter_1(self):
        class Foo(Command):
            verbose: int = Counter('-v')

        self.assertEqual(Foo.parse(['-v']).verbose, 1)
        self.assertEqual(Foo.parse(['--verbose']).verbose, 1)
        with self.assertRaises(NoSuchOption):
            Foo.parse(['-verbose'])

    def test_counter_multi(self):
        class Foo(Command):
            verbose: int = Counter('-v')

        for n in range(1, 11):
            with self.subTest(n=n):
                self.assertEqual(Foo.parse(['-{}'.format('v' * n)]).verbose, n)
                self.assertEqual(Foo.parse(['--verbose'] * n).verbose, n)

    def test_counter_num_no_space(self):
        class Foo(Command):
            verbose: int = Counter('-v')

        for n in range(-10, 11):
            with self.subTest(n=n):
                self.assertEqual(Foo.parse([f'-v{n}']).verbose, n)

    def test_counter_num_space(self):
        class Foo(Command):
            verbose: int = Counter('-v')

        for n in range(-10, 11):
            with self.subTest(n=n):
                self.assertEqual(Foo.parse(['-v', str(n)]).verbose, n)
                self.assertEqual(Foo.parse(['--verbose', str(n)]).verbose, n)

    def test_counter_num_eq(self):
        class Foo(Command):
            verbose: int = Counter('-v')

        for n in range(-10, 11):
            with self.subTest(n=n):
                self.assertEqual(Foo.parse([f'-v={n}']).verbose, n)
                self.assertEqual(Foo.parse([f'--verbose={n}']).verbose, n)

    def test_combined_counters(self):
        class Foo(Command):
            foo = Counter('-f')
            bar = Counter('-b')

        cases = {
            '-ffbb': (2, 2),
            '-fbfb': (2, 2),
            '-ffb': (2, 1),
            '-fbf': (2, 1),
            '-fbb': (1, 2),
            '-bfb': (1, 2),
            '-bb': (0, 2),
            '-ff': (2, 0),
            ('-fb', '3'): (1, 3),
        }
        for case, (f, b) in cases.items():
            foo = Foo.parse([case] if isinstance(case, str) else case)
            self.assertEqual(foo.foo, f)
            self.assertEqual(foo.bar, b)

    def test_counter_flag_combo(self):
        class Foo(Command):
            foo = Flag('-f')
            bar = Counter('-b')

        cases = {
            '-ffbb': (True, 2),
            '-fbfb': (True, 2),
            '-ffb': (True, 1),
            '-fbf': (True, 1),
            '-fbb': (True, 2),
            '-bfb': (True, 2),
            '-bb': (False, 2),
            '-ff': (True, 0),
            ('-fb', '3'): (True, 3),
        }
        for case, (f, b) in cases.items():
            foo = Foo.parse([case] if isinstance(case, str) else case)
            self.assertEqual(foo.foo, f)
            self.assertEqual(foo.bar, b)


class PassThruTest(ParserTest):
    def test_pass_thru(self):
        class Foo(Command):
            bar = Flag()
            baz = PassThru()

        success_cases = [
            (['--bar', '--', 'a', 'b', 'c'], {'bar': True, 'baz': ['a', 'b', 'c']}),
            (['--', '--bar', '--', 'a', 'b', 'c'], {'bar': False, 'baz': ['--bar', '--', 'a', 'b', 'c']}),
            (['--bar', '--'], {'bar': True, 'baz': []}),
            (['--', '--bar'], {'bar': False, 'baz': ['--bar']}),
            (['--'], {'bar': False, 'baz': []}),
            (['--bar'], {'bar': True, 'baz': None}),
        ]
        self.assert_parse_results_cases(Foo, success_cases)

    def test_pass_thru_missing(self):
        class Foo(Command):
            bar = Flag()
            baz = PassThru(required=True)

        with self.assertRaises(MissingArgument):
            Foo.parse([])

    def test_multiple_rejected(self):
        class Foo(Command):
            bar = PassThru()
            baz = PassThru()

        with self.assertRaises(CommandDefinitionError):
            Foo.parser  # noqa

    def test_double_dash_without_pass_thru_rejected(self):
        class Foo(Command):
            bar = Flag()

        with self.assertRaises(NoSuchOption):
            Foo.parse(['--'])

    def test_parser_has_pass_thru(self):
        class Foo(Command):
            pt = PassThru()

        class Bar(Foo):
            pass

        self.assertTrue((Bar.parser.has_pass_thru()))

    def test_sub_cmd_multiple_rejected(self):
        class Foo(Command):
            sub = SubCommand()
            pt1 = PassThru()

        class Bar(Foo):
            pt2 = PassThru()

        with self.assertRaises(CommandDefinitionError):
            Bar.parser  # noqa


class MiscParameterTest(ParserTest):
    def test_param_knows_command(self):
        class Foo(Command):
            foo = Option('-f', choices=('a', 'b'))

        self.assertIs(Foo.foo.command, Foo)

    def test_unregistered_action_rejected(self):
        with self.assertRaises(ParameterDefinitionError):
            Flag(action='foo')

    def test_empty_choices(self):
        with self.assertRaises(ParameterDefinitionError):
            Option(choices=())

    def test_action_is_parameter_action(self):
        self.assertIsInstance(Flag.store_const, parameter_action)

    def test_re_assign_rejected(self):
        option = Option(action='store')
        args = Args([])
        option.take_action(args, 'foo')
        with self.assertRaises(ParamUsageError):
            option.take_action(args, 'foo')

    def test_too_many_rejected(self):
        option = Option(action='append', nargs=1)
        args = Args([])
        option.take_action(args, 'foo')
        with self.assertRaises(ParamUsageError):
            option.take_action(args, 'foo')

    def test_non_none_rejected(self):
        flag = Flag()
        with self.assertRaises(ParamUsageError):
            flag.take_action(Args([]), 'foo')

    def test_explicit_name(self):
        class Foo(Command):
            bar = Option(name='foo')

        self.assert_parse_results(Foo, ['--bar', 'a'], {'foo': 'a'})
        self.assert_parse_fails(Foo, ['--foo', 'a'], expected_pattern='unrecognized arguments:')

    def test_sort_mixed_types(self):
        sort_cases = [
            (ParamGroup(), Flag(), ActionFlag()),
            (Flag(), ActionFlag(), ParamGroup()),
            (ActionFlag(), ParamGroup(), Flag()),
            ('foo', ParamGroup(), Flag(), ActionFlag()),
            ('foo', Flag(), ActionFlag(), ParamGroup()),
            ('foo', ActionFlag(), ParamGroup(), Flag()),
        ]
        for group in sort_cases:
            with self.subTest(group=group), self.assertRaises(TypeError):
                sorted(group)

    def test_late_param_addition(self):
        class Foo(Command):
            pass

        Foo.bar = Flag('--bar', '-b')
        key = f'Flag#{id(Foo.bar)}'
        success_cases = [([], {key: False}), (['--bar'], {key: True}), (['-b'], {key: True})]
        self.assert_parse_results_cases(Foo, success_cases)
        for argv, expected in success_cases:
            with self.subTest(argv=argv):
                self.assertEqual(expected[key], Foo.parse(argv).bar)

    def test_unexpected_prep_value_error(self):
        class Foo(Command):
            bar = Positional(type=Mock(side_effect=OSError))

        self.assert_parse_fails(Foo, ['a'], BadArgument, 'unable to cast value=.* to type=')

    def test_none_invalid(self):
        with self.assertRaises(MissingArgument):
            Option().validate(Args([]), None)

    def test_none_valid(self):
        self.assertIs(None, Flag().validate(Args([]), None))

    def test_value_invalid(self):
        with self.assertRaises(BadArgument):
            Flag().validate(Args([]), 1)

    def test_missing_required_value_single(self):
        class Foo(Command, allow_missing=True):
            bar = Option(required=True)

        with self.assertRaises(MissingArgument):
            Foo.parse([]).bar  # noqa

    def test_missing_required_value_multi(self):
        class Foo(Command, allow_missing=True):
            bar = Option(nargs='+', required=True)

        with self.assertRaises(MissingArgument):
            Foo.parse([]).bar  # noqa

    def test_too_few_values(self):
        class Foo(Command):
            bar = Option(nargs=2)

        args = Args(['--bar', 'a'])
        foo = Foo(args)  # This is NOT the recommended way of initializing a Command
        with self.assertRaises(BadArgument):
            foo.parser.parse_args(args)
        with self.assertRaisesRegex(BadArgument, r'expected nargs=.* values but found \d+'):
            foo.bar  # noqa

    def test_bad_choice(self):
        class Foo(Command):
            bar = Option(choices=('a', 'b', 'c'))

        foo = Foo.parse(['--bar', 'c'])
        Foo.bar.choices = ('a', 'b')
        with self.assertRaises(InvalidChoice):
            foo.bar  # noqa

    def test_bad_choices(self):
        class Foo(Command):
            bar = Option(nargs='+', choices=('a', 'b', 'c'))

        foo = Foo.parse(['--bar', 'c'])
        Foo.bar.choices = ('a', 'b')
        with self.assertRaises(InvalidChoice):
            foo.bar  # noqa


class TypeCastTest(ParserTest):
    def test_type_cast_singles(self):
        cases = [
            (int, '5', 5),
            (Optional[int], '5', 5),
            (Union[int], '5', 5),  # results in just int
            (Union[int, str], '5', '5'),
            (Union[int, str, None], '5', '5'),
            (_C, '5', _C('5')),
            (Union[int, _C], '5', '5'),
            (_resolved_path, 'test_parameters.py', 'test_parameters.py'),  # Not a proper annotation
            (Optional[_resolved_path], 'test_parameters.py', 'test_parameters.py'),  # Not a proper annotation
        ]
        for annotation, arg, expected in cases:
            with self.subTest(annotation=annotation):

                class Foo(Command):
                    bar: annotation = Positional()

                self.assertEqual(expected, Foo.parse([arg]).bar)

    def test_type_cast_multiples(self):
        cases = [
            (list[int], ['1', '2'], [1, 2]),
            (list[Optional[int]], ['1', '2'], [1, 2]),
            (Optional[list[int]], ['1', '2'], [1, 2]),
            (tuple[int, ...], ['1', '2'], [1, 2]),
            (Sequence[int], ['1', '2'], [1, 2]),
            (Collection[int], ['1', '2'], [1, 2]),
            (Iterable[int], ['1', '2'], [1, 2]),
            (list[_C], ['1', '2'], [_C('1'), _C('2')]),
            (list, ['12', '3'], [['1', '2'], ['3']]),
            (list[Union[int, str, None]], ['12', '3'], ['12', '3']),
            (tuple[int, str, None], ['12', '3'], ['12', '3']),
            (list[_resolved_path], ['test_parser.py', 'test_commands.py'], ['test_parser.py', 'test_commands.py']),
        ]
        for annotation, argv, expected in cases:
            with self.subTest(annotation=annotation):

                class Foo(Command):
                    bar: annotation = Positional(nargs='+')

                self.assertEqual(expected, Foo.parse(argv).bar)

    def test_type_overrules_annotation(self):
        cases = [(str, int, ['--bar', '5'], 5), (int, str, ['--bar', '5'], '5')]
        for annotation, type_val, argv, expected in cases:

            class Foo(Command):
                bar: annotation = Option(type=type_val)

            self.assertEqual(expected, Foo.parse(argv).bar)


def _resolved_path(path):
    return Path(path).resolve()


@dataclass
class _C:
    x: str


if __name__ == '__main__':
    try:
        main(warnings='ignore', verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
