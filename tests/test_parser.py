#!/usr/bin/env python

from contextlib import redirect_stdout
from unittest import main
from unittest.mock import Mock

from command_parser import Command
from command_parser.actions import help_action
from command_parser.args import Args
from command_parser.exceptions import ParamsMissing, CommandDefinitionError, MissingArgument, ParserExit
from command_parser.parameters import Counter, Flag, Positional, SubCommand, Option, Parameter, parameter_action
from command_parser.testing import ParserTest as _ParserTest


class ParserTest(_ParserTest):
    # def setUp(self):
    #     print()
    #
    # def subTest(self, *args, **kwargs):
    #     print()
    #     return super().subTest(*args, **kwargs)

    def test_parser_repr(self):
        class Foo(Command):
            bar = Positional()

        rep = repr(Foo.parser)
        self.assertIn('Foo', rep)
        self.assertIn('positionals=', rep)
        self.assertIn('options=', rep)

    # def test_parser_contains_recursive(self):
    #     class Foo(Command):
    #         cmd = SubCommand()
    #
    #     class Bar(Foo):
    #         bar = Counter('-b')
    #
    #     for cls in (Foo, Bar):
    #         parser = cls.parser
    #         self.assertTrue(parser.contains(Args([]), '-h'))
    #         self.assertFalse(parser.contains(Args([]), '-H'))
    #         self.assertTrue(parser.contains(Args([]), '-b=1'))
    #         self.assertFalse(parser.contains(Args([]), '-B=1'))
    #         self.assertFalse(parser.contains(Args([]), '-ba'))
    #         self.assertTrue(parser.contains(Args([]), '--bar=1'))
    #         self.assertFalse(parser.contains(Args([]), '--baz=1'))
    #         self.assertFalse(parser.contains(Args([]), 'baz'))
    #         self.assertTrue(parser.contains(Args([]), '-b=1'))
    #         self.assertFalse(parser.contains(Args([]), '-B=1'))
    #         self.assertTrue(parser.contains(Args([]), '-bb'))
    #         self.assertFalse(parser.contains(Args([]), '-ab'))
    #
    def test_parser_does_not_contain_triple_dash(self):
        class Foo(Command):
            pass

        self.assertIs(None, Foo.parser.get_params(Args([]), '---'))

    def test_parser_does_not_contain_combined_short(self):
        class Foo(Command):
            test = Flag('-t')

        self.assertIs(None, Foo.parser.get_params(Args([]), '-test'))

    def test_parser_contains_combined_short(self):
        class Foo(Command):
            foo = Flag('-f')
            bar = Flag('-b')

        self.assertIsNot(None, Foo.parser.get_params(Args([]), '-fb'))

    def test_parser_does_not_contain_non_optional(self):
        class Foo(Command):
            foo = Flag('-f')
            bar = Flag('-b')

        self.assertIs(None, Foo.parser.get_params(Args([]), 'f'))

    def test_parser_does_not_contain_long(self):
        class Foo(Command):
            foo = Flag('-f')
            bar = Flag('-b')

        self.assertIs(None, Foo.parser.get_params(Args([]), '--baz'))

    def test_redefined_param_rejected(self):
        class Foo(Command):
            cmd = SubCommand()
            bar = Flag('-b')

        class Bar(Foo):
            bar = Counter('-b')

        with self.assertRaisesRegex(CommandDefinitionError, 'conflict for command=.* between params'):
            Foo.parse(['bar'])

    def test_alt_parent_sub_command_missing_args_1(self):
        class Foo(Command, error_handler=None):
            cmd = SubCommand()

        @Foo.cmd.register
        class Bar(Command, error_handler=None):
            baz = Positional()

        with self.assertRaises(ParamsMissing):
            Foo.parse_and_run(['bar'])
        with self.assertRaises(MissingArgument):
            Foo.parse_and_run([])
        with redirect_stdout(Mock()), self.assertRaises(ParserExit):
            Foo.parse_and_run(['bar', '-h'])
        with redirect_stdout(Mock()), self.assertRaises(ParserExit):
            Foo.parse_and_run(['-h'])

    def test_alt_parent_sub_command_missing_args_2(self):
        class Foo(Command, error_handler=None):
            cmd = SubCommand()
            foo = Option('-f', required=True)

        @Foo.cmd.register
        class Bar(Command, error_handler=None):
            baz = Positional()

        with self.assertRaises(ParamsMissing):
            Foo.parse_and_run(['bar'])
        with self.assertRaises(MissingArgument):
            Foo.parse_and_run([])
        with redirect_stdout(Mock()), self.assertRaises(ParserExit):
            Foo.parse_and_run(['bar', '-h'])
        with redirect_stdout(Mock()), self.assertRaises(ParserExit):
            Foo.parse_and_run(['-h'])

    def test_arg_dict_with_parent(self):
        class Foo(Command):
            pass

        class Bar(Foo):
            pass

        expected = {help_action.name: False}
        self.assertDictEqual(expected, Bar.parser.arg_dict(Args([])))

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

        self.assert_parse_fails(Baz, [], CommandDefinitionError, 'conflict for command=.* between params')
        self.assert_parse_fails(Foo, ['baz'], CommandDefinitionError, 'conflict for command=.* between params')

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
            Foo.parser  # noqa


if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    try:
        main(warnings='ignore', verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
