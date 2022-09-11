#!/usr/bin/env python

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Collection, Sequence, Iterable, Union
from unittest import main, skipIf
from unittest.mock import Mock

from cli_command_parser import Command
from cli_command_parser.context import Context
from cli_command_parser.core import get_params
from cli_command_parser.exceptions import (
    NoSuchOption,
    ParameterDefinitionError,
    CommandDefinitionError,
    ParamUsageError,
    MissingArgument,
    BadArgument,
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

    def test_short_conflict(self):
        class Foo(Command):
            bar = Flag('-b')
            baz = Option('-b')

        with self.assertRaises(CommandDefinitionError):
            Foo.parse([])

    # TODO: Conflict check issues
    # def test_short_conflict_in_subcommand(self):
    #     class A(Command, description='...'):
    #         sub_cmd = SubCommand()
    #         verbose = Counter('-v')
    #         with ParamGroup(description='API Options'):
    #             env = Option('-e', choices=(), default='dev')
    #             limit: int = Option('-L')
    #             max: int = Option('-M')
    #
    #         def __init__(self):
    #             pass
    #
    #     class B(A):
    #         sub_cmd = SubCommand()
    #         format = Option('-f', choices=(), default='')
    #
    #     class C(B):
    #         with ParamGroup(mutually_exclusive=True, required=True):
    #             tag = Option('-t')
    #             baz = Flag('-b')
    #
    #         extra = Flag('-e')  # conflicts with env
    #         # TODO: Earlier conflict check?  currently only happens when using a given subcommand
    #
    #     with self.assertRaises(CommandDefinitionError):
    #         A.parse(['b', 'c'])


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
            (tuple[int, int], ['1', '2'], [1, 2]),
            (Sequence[int], ['1', '2'], [1, 2]),
            (Collection[int], ['1', '2'], [1, 2]),
            (Iterable[int], ['1', '2'], [1, 2]),
            (list[_C], ['1', '2'], [_C('1'), _C('2')]),
            (list, ['12', '3'], [['1', '2'], ['3']]),
            (list[Union[int, str, None]], ['12', '3'], ['12', '3']),
            (tuple[int, str, None], ['12', '3'], ['12', '3']),
            (list[_resolved_path], ['test_parser.py', 'test_commands.py'], ['test_parser.py', 'test_commands.py']),
            (dict[str, int, str], ['1', '2'], ['1', '2']),  # Not really a valid annotation, but it hits a branch
            (list[str, int, str], ['1', '2'], ['1', '2']),  # Not really a valid annotation, but it hits a branch
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
            (Tuple[int, int], ['1', '2'], [1, 2]),
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


def _resolved_path(path):
    return Path(path).resolve()


@dataclass
class _C:
    x: str


if __name__ == '__main__':
    try:
        main(verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
