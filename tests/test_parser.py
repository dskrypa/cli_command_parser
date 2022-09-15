#!/usr/bin/env python

from unittest import main
from unittest.mock import Mock

from cli_command_parser import Command
from cli_command_parser.actions import help_action
from cli_command_parser.context import Context
from cli_command_parser.core import get_params
from cli_command_parser.exceptions import ParamsMissing, CommandDefinitionError, MissingArgument, ParserExit
from cli_command_parser.parameters.base import parameter_action, Parameter
from cli_command_parser.parameters import Counter, Flag, Positional, SubCommand, Option
from cli_command_parser.testing import RedirectStreams, ParserTest as _ParserTest


class ParserTest(_ParserTest):
    def test_reprs(self):
        class Foo(Command):
            bar = Positional()

        rep = repr(get_params(Foo))
        self.assertIn('Foo', rep)
        self.assertIn('positionals=', rep)
        self.assertIn('options=', rep)

    def test_params_contains_long(self):
        class Foo(Command):
            bar = Option()

        self.assertIs(Foo.bar, get_params(Foo).get_option_param_value_pairs('--bar')[0])

    def test_params_find_option_rejects_non_option(self):
        class Foo(Command):
            pass

        with self.assertRaises(ValueError):
            get_params(Foo).find_option_that_accepts_values('bar')

    def test_parser_does_not_contain_triple_dash(self):
        class Foo(Command):
            pass

        self.assertIs(None, get_params(Foo).get_option_param_value_pairs('---'))

    def test_parser_does_not_contain_combined_short(self):
        class Foo(Command):
            test = Flag('-t')

        with Context():
            self.assertIs(None, get_params(Foo).get_option_param_value_pairs('-test'))

    def test_parser_contains_combined_short(self):
        class Foo(Command):
            foo = Flag('-f')
            bar = Flag('-b')

        with Context():
            self.assertIsNot(None, get_params(Foo).get_option_param_value_pairs('-fb'))

    def test_parser_does_not_contain_non_optional(self):
        class Foo(Command):
            foo = Flag('-f')
            bar = Flag('-b')

        self.assertIs(None, get_params(Foo).get_option_param_value_pairs('f'))

    def test_parser_does_not_contain_long(self):
        class Foo(Command):
            foo = Flag('-f')
            bar = Flag('-b')

        self.assertIs(None, get_params(Foo).get_option_param_value_pairs('--baz'))

    def test_redefined_param_rejected(self):
        class Foo(Command):
            cmd = SubCommand()
            bar = Flag('-b')

        class Bar(Foo):
            bar = Counter('-b')

        with self.assertRaisesRegex(CommandDefinitionError, 'conflict for command=.* between'):
            Foo.parse(['bar'])

    def test_alt_parent_sub_command_missing_args(self):
        for with_option in (False, True):
            with self.subTest(with_option=with_option):

                class Foo(Command, error_handler=None):
                    cmd = SubCommand()
                    if with_option:
                        foo = Option('-f', required=True)

                @Foo.cmd.register
                class Bar(Command, error_handler=None):
                    baz = Positional()

                with self.assertRaises(ParamsMissing):
                    Foo.parse_and_run(['bar'])
                with self.assertRaises(MissingArgument):
                    Foo.parse_and_run([])
                with RedirectStreams():
                    with self.assertRaises(ParserExit):
                        Foo.parse_and_run(['bar', '-h'])
                    with self.assertRaises(ParserExit):
                        Foo.parse_and_run(['-h'])

    def test_arg_dict_with_parent(self):
        class Foo(Command):
            pass

        class Bar(Foo):
            pass

        expected = {help_action.name: False}
        self.assertDictEqual(expected, Bar.parse([]).ctx.get_parsed())

    def test_explicit_name_conflict_before(self):
        class Foo(Command):
            bar = Option(name='baz')
            baz = Option()

        with self.assertRaisesRegex(CommandDefinitionError, 'Name conflict.*bar=Option.*baz=Option'):
            Foo.parse([])

    def test_explicit_name_conflict_after(self):
        class Foo(Command):
            baz = Option()
            bar = Option(name='baz')

        with self.assertRaisesRegex(CommandDefinitionError, 'Name conflict.*baz=Option.*bar=Option'):
            Foo.parse([])

    def test_sub_cmd_param_override_rejected(self):
        class Foo(Command):
            sub_cmd = SubCommand()
            bar = Option()

        class Baz(Foo):
            bar = Option()

        self.assert_parse_fails(Baz, [], CommandDefinitionError, 'conflict for command=.* between')
        self.assert_parse_fails(Foo, ['baz'], CommandDefinitionError, 'conflict for command=.* between')

    def test_sub_cmd_param_name_override_ok(self):
        class Foo(Command):
            sub_cmd = SubCommand()
            bar = Option()

        class Baz(Foo):
            baz = Option(name='bar')

        success_cases = [
            (['baz', '--bar', 'a', '--baz', 'b'], {'sub_cmd': 'baz', 'bar': 'b'}),
            (['baz', '--bar', 'a'], {'sub_cmd': 'baz', 'bar': None}),
            (['baz', '--baz', 'a'], {'sub_cmd': 'baz', 'bar': 'a'}),
        ]
        self.assert_parse_results_cases(Foo, success_cases)

    def test_bad_custom_param_rejected(self):
        class TestParam(Parameter):
            test = parameter_action(Mock())

        class Foo(Command):
            bar = TestParam('test')

        with self.assertRaisesRegex(CommandDefinitionError, 'custom parameters must extend'):
            Foo.parse([])

    def test_params_parent(self):
        class Foo(Command):
            sub_cmd = SubCommand()

        class Baz(Foo):
            pass

        self.assertIs(get_params(Baz).parent, get_params(Foo))


if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    try:
        main(verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
