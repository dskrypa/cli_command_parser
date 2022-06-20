#!/usr/bin/env python

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Collection, Sequence, Iterable, Union
from unittest import TestCase, main, skipIf
from unittest.mock import Mock

from cli_command_parser import Command
from cli_command_parser.context import Context
from cli_command_parser.core import get_params
from cli_command_parser.exceptions import (
    NoSuchOption,
    UsageError,
    ParameterDefinitionError,
    CommandDefinitionError,
    ParamUsageError,
    MissingArgument,
    BadArgument,
    InvalidChoice,
    UnsupportedAction,
    ParamsMissing,
)
from cli_command_parser.formatting.params import (
    ParamHelpFormatter,
    PositionalHelpFormatter,
    OptionHelpFormatter,
    ChoiceMapHelpFormatter,
    PassThruHelpFormatter,
    GroupHelpFormatter,
)
from cli_command_parser.parameters.base import parameter_action, Parameter, BaseOption, BasePositional
from cli_command_parser.parameters.choice_map import ChoiceMap, SubCommand, Action
from cli_command_parser.parameters import PassThru, Positional, ParamGroup, ActionFlag, Counter, Flag, Option
from cli_command_parser.parser import CommandParser
from cli_command_parser.testing import ParserTest


class PositionalTest(ParserTest):
    def test_required_rejected(self):
        with self.assertRaises(ParameterDefinitionError):
            Positional(required=False)

    def test_default_rejected(self):
        with self.assertRaises(ParameterDefinitionError):
            Positional(default=None)

    def test_custom_default_rejected(self):
        class CustomPositional(BasePositional):
            foo = parameter_action(Mock())

        with self.assertRaises(ParameterDefinitionError):
            CustomPositional(default=None, action='foo')

    def test_nargs_0_rejected(self):
        with self.assertRaises(ParameterDefinitionError):
            Positional(nargs=0)

    def test_action_nargs_mismatch_rejected(self):
        with self.assertRaises(ParameterDefinitionError):
            Positional(nargs=2, action='store')

        self.assertEqual(1, Positional(action='store').nargs)

    def test_nargs_star_empty_list(self):
        class Foo(Command):
            bar = Positional(nargs='*')

        success_cases = [([], {'bar': []}), (['a'], {'bar': ['a']}), (['a', 'b'], {'bar': ['a', 'b']})]
        self.assert_parse_results_cases(Foo, success_cases)

    def test_nargs_star_defaults(self):
        for default in ('a', ['a']):
            with self.subTest(default=default):

                class Foo(Command):
                    bar = Positional(nargs='*', default=default)

                success_cases = [([], {'bar': ['a']}), (['b'], {'bar': ['b']}), (['a', 'b'], {'bar': ['a', 'b']})]
                self.assert_parse_results_cases(Foo, success_cases)

    def test_pos_after_nargs_star_rejected(self):
        class Foo(Command):
            bar = Positional(nargs='*')
            baz = Positional()

        with self.assertRaises(CommandDefinitionError):
            Foo.parse([])


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
        # fmt: off
        fail_cases = [
            '---foo', '-f-', '-foo--', '--foo-', '--foo=', '-f=', '-foo=', '=', '-', '--', '---', '-=', '--=', '-a-a'
        ]
        # fmt: on
        for option_str in fail_cases:
            with self.subTest(option_str=option_str), self.assertRaises(ParameterDefinitionError):
                Option(option_str)

    def test_re_assign_rejected(self):
        class Foo(Command):
            bar = Option('-b')

        self.assert_parse_fails(Foo, ['-b', 'a', '-b', 'b'], ParamUsageError)

    def test_too_many_rejected(self):
        class Foo(Command):
            bar = Option('-b', nargs=2)

        self.assert_parse_results(Foo, ['-b', 'a', 'b'], {'bar': ['a', 'b']})
        self.assert_parse_fails(Foo, ['-b', 'a', 'b', '-b', 'b'], ParamUsageError)

    def test_explicit_long_opt(self):
        class Foo(Command):
            foo = Option('--bar', '-b')

        self.assertNotIn('--foo', Foo.foo.long_opts)

    def test_action_nargs_mismatch_rejected(self):
        with self.assertRaises(ParameterDefinitionError):
            Option(nargs=2, action='store')

        self.assertEqual(1, Option(action='store').nargs)

    def test_usage(self):
        self.assertEqual('--foo', Option('--foo').format_usage())
        self.assertEqual('[--foo bar]', Option('--foo', metavar='bar', required=False).formatter.format_basic_usage())
        self.assertEqual('--foo bar', Option('--foo', metavar='bar', required=True).formatter.format_basic_usage())

    def test_not_required_nargs_plus_default(self):
        class Foo(Command):
            bar = Option('-b', nargs='+')

        foo = Foo.parse_and_run([])
        self.assertFalse(foo.bar)
        self.assertEqual([], foo.bar)

    def test_required_default_rejected(self):
        cases = (None, 1, 'test')
        for case in cases:
            with self.subTest(case=case):
                with self.assertRaises(ParameterDefinitionError):
                    Option(required=True, default=case)


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

    def test_nargs_not_allowed(self):
        with self.assertRaises(TypeError):
            Flag(nargs='+')

    def test_type_not_allowed(self):
        with self.assertRaises(TypeError):
            Flag(type=int)

    def test_choices_not_allowed(self):
        with self.assertRaises(TypeError):
            Flag(choices=(1, 2))


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

    def test_bad_default(self):
        with self.assertRaises(ParameterDefinitionError):
            Counter(default=1.5)  # noqa

    def test_prepare_value(self):
        self.assertEqual(1, Counter().prepare_value(None))

    def test_validate(self):
        self.assertTrue(Counter().is_valid_arg('1'))
        self.assertFalse(Counter().is_valid_arg('1.5'))

    def test_nargs_not_allowed(self):
        with self.assertRaises(TypeError):
            Counter(nargs='+')

    def test_type_not_allowed(self):
        with self.assertRaises(TypeError):
            Counter(type=int)

    def test_choices_not_allowed(self):
        with self.assertRaises(TypeError):
            Counter(choices=(1, 2))


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

        self.assertTrue(Foo.baz.default is not None)
        foo = Foo()
        with self.assertRaisesRegex(ParamsMissing, "missing pass thru args separated from others with '--'"):
            foo.parse([])
        with self.assertRaises(MissingArgument):
            foo.baz  # noqa

    def test_multiple_rejected(self):
        class Foo(Command):
            bar = PassThru()
            baz = PassThru()

        with self.assertRaises(CommandDefinitionError):
            Foo.parse([])

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

        self.assertTrue(get_params(Bar).pass_thru)

    def test_sub_cmd_multiple_rejected(self):
        class Foo(Command):
            sub = SubCommand()
            pt1 = PassThru()

        class Bar(Foo):
            pt2 = PassThru()

        with self.assertRaises(CommandDefinitionError):
            Bar.parse([])

    def test_extra_rejected(self):
        with Context():
            pt = PassThru()
            pt.take_action(['a'])
            with self.assertRaises(ParamUsageError):
                pt.take_action(['a'])

    def test_usage(self):
        self.assertEqual('[-- FOO]', PassThru(name='foo', required=False).formatter.format_basic_usage())
        self.assertEqual('-- FOO', PassThru(name='foo', required=True).formatter.format_basic_usage())

    def test_nargs_not_allowed(self):
        with self.assertRaises(TypeError):
            PassThru(nargs='+')

    def test_type_not_allowed(self):
        with self.assertRaises(TypeError):
            PassThru(type=int)

    def test_choices_not_allowed(self):
        with self.assertRaises(TypeError):
            PassThru(choices=(1, 2))


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

    def test_explicit_name(self):
        class Foo(Command):
            bar = Option(name='foo')

        self.assert_parse_results(Foo, ['--bar', 'a'], {'foo': 'a'})
        self.assert_parse_fails(Foo, ['--foo', 'a'], expected_pattern='unrecognized arguments:')

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

    def test_formatter_class(self):
        param_fmt_cls_map = {
            Parameter: ParamHelpFormatter,
            PassThru: PassThruHelpFormatter,
            BasePositional: PositionalHelpFormatter,
            Positional: PositionalHelpFormatter,
            ChoiceMap: ChoiceMapHelpFormatter,
            SubCommand: ChoiceMapHelpFormatter,
            Action: ChoiceMapHelpFormatter,
            BaseOption: OptionHelpFormatter,
            Option: OptionHelpFormatter,
            Flag: OptionHelpFormatter,
            Counter: OptionHelpFormatter,
            ActionFlag: OptionHelpFormatter,
            ParamGroup: GroupHelpFormatter,
        }
        for param_cls, expected_cls in param_fmt_cls_map.items():
            with self.subTest(param_cls=param_cls):
                self.assertIs(expected_cls, ParamHelpFormatter.for_param_cls(param_cls))


class UnlikelyToBeReachedParameterTest(ParserTest):
    def test_too_many_rejected(self):
        option = Option(action='append', nargs=1)
        with Context():
            option.take_action('foo')
            with self.assertRaises(ParamUsageError):
                option.take_action('foo')

    def test_non_none_rejected(self):
        flag = Flag()
        with self.assertRaises(ParamUsageError), Context():
            flag.take_action('foo')

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

    def test_none_invalid(self):
        with self.assertRaises(MissingArgument), Context():
            Option().validate(None)

    def test_none_valid(self):
        with Context():
            self.assertIs(None, Flag().validate(None))

    def test_value_invalid(self):
        with self.assertRaises(BadArgument), Context():
            Flag().validate(1)

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

        with Context(['--bar', 'a'], Foo) as ctx:
            foo = Foo()  # This is NOT the recommended way of initializing a Command
            with self.assertRaises(BadArgument):
                CommandParser.parse_args(ctx)
            with self.assertRaisesRegex(BadArgument, r'expected nargs=.* values but found \d+'):
                foo.bar  # noqa

    def test_flag_pop_last(self):
        with self.assertRaises(UnsupportedAction):
            Flag().pop_last()

    def test_empty_reset(self):
        class Foo(Command):
            bar = Positional(nargs='+')

        with Context():
            self.assertEqual([], Foo.bar._reset())

    def test_unsupported_pop(self):
        class Foo(Command):
            bar = Positional()

        with Context(), self.assertRaises(UnsupportedAction):
            Foo.bar.pop_last()


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

    @skipIf(sys.version_info < (3, 9), 'stdlib collections are not subscriptable for annotations before 3.9')
    def test_type_cast_multiples_39(self):
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

    def test_type_cast_multiples(self):
        from typing import List, Tuple

        cases = [
            (List[int], ['1', '2'], [1, 2]),
            (List[Optional[int]], ['1', '2'], [1, 2]),
            (Optional[List[int]], ['1', '2'], [1, 2]),
            (Tuple[int, ...], ['1', '2'], [1, 2]),
            (Sequence[int], ['1', '2'], [1, 2]),
            (Collection[int], ['1', '2'], [1, 2]),
            (Iterable[int], ['1', '2'], [1, 2]),
            (List[_C], ['1', '2'], [_C('1'), _C('2')]),
            (List, ['12', '3'], [['1', '2'], ['3']]),
            (List[Union[int, str, None]], ['12', '3'], ['12', '3']),
            (Tuple[int, str, None], ['12', '3'], ['12', '3']),
            (List[_resolved_path], ['test_parser.py', 'test_commands.py'], ['test_parser.py', 'test_commands.py']),
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


class ChoiceMapTest(ParserTest):
    def test_reassign_choice_rejected(self):
        with self.assertRaises(CommandDefinitionError):

            class Foo(Command):
                action = Action()
                action('foo')(Mock())
                action('foo')(Mock())

    def test_bad_choice_append_rejected(self):
        class Foo(Command):
            action = Action()
            action('foo bar')(Mock())

        with Context():
            Foo.action.take_action('foo')
            with self.assertRaises(InvalidChoice):
                Foo.action.append('baz')

    def test_missing_action_target(self):
        class Foo(Command):
            action = Action()

        self.assert_parse_fails(Foo, [], CommandDefinitionError)

    def test_missing_action_target_forced(self):
        class Foo(Command):
            action = Action()

        with Context():
            with self.assertRaises(BadArgument):
                Foo.action.validate('-foo')
            self.assertIs(None, Foo.action.validate('foo'))

    def test_choice_map_too_many(self):
        class Foo(Command):
            action = Action()
            action('foo')(Mock())

        with Context():
            Foo.action.take_action('foo')
            with self.assertRaises(BadArgument):
                Foo.action.validate('bar')

    def test_no_choices_result_forced(self):
        class Foo(Command):
            action = Action()
            action('foo')(Mock())

        with self.assertRaises(CommandDefinitionError):
            foo = Foo.parse([])
            del Foo.action.choices['foo']
            foo.action  # noqa

    def test_unexpected_nargs(self):
        class Foo(Command):
            action = Action()
            action('foo bar')(Mock())

        with Context():
            Foo.action.take_action('foo')
            with self.assertRaises(BadArgument):
                Foo.action.result()

    def test_unexpected_choice(self):
        class Foo(Command):
            action = Action()
            action('foo bar')(Mock())
            action('foo baz')(Mock())

        with Context():
            Foo.action.take_action('foo bar')
            del Foo.action.choices['foo bar']
            with self.assertRaises(BadArgument):
                Foo.action.result()

    def test_reassign_sub_command_rejected(self):
        class Foo(Command):
            sub = SubCommand()

        Foo.sub.register(Mock(__name__='bar'))
        with self.assertRaises(CommandDefinitionError):
            Foo.sub.register(Mock(__name__='bar'))

    def test_redundant_sub_cmd_choice_rejected(self):
        class Foo(Command):
            sub = SubCommand()

        with self.assertRaises(CommandDefinitionError):
            Foo.sub.register('foo', choice='foo')

    def test_custom_action_choice(self):
        class Foo(Command):
            action = Action()
            action(choice='foo')(Mock(__name__='bar'))

        self.assertIn('foo', Foo.action.choices)

    def test_nargs_not_allowed_sub_cmd(self):
        with self.assertRaises(TypeError):
            SubCommand(nargs='+')

    def test_type_not_allowed_sub_cmd(self):
        with self.assertRaises(TypeError):
            SubCommand(type=int)

    def test_choices_not_allowed_sub_cmd(self):
        with self.assertRaises(ParameterDefinitionError):
            SubCommand(choices=(1, 2))

    def test_nargs_not_allowed_action(self):
        with self.assertRaises(TypeError):
            Action(nargs='+')

    def test_type_not_allowed_action(self):
        with self.assertRaises(TypeError):
            Action(type=int)

    def test_choices_not_allowed_action(self):
        with self.assertRaises(ParameterDefinitionError):
            Action(choices=(1, 2))


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
