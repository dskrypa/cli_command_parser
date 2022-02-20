#!/usr/bin/env python

from contextlib import redirect_stdout
from unittest import TestCase, main
from unittest.mock import Mock

from command_parser import Command, Counter, Flag, Positional, SubCommand, Option
from command_parser.exceptions import ParamsMissing, CommandDefinitionError, MissingArgument, ParserExit
from command_parser.args import Args


class ParserTest(TestCase):
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

    def test_parser_contains_recursive(self):
        class Foo(Command):
            cmd = SubCommand()

        class Bar(Foo):
            bar = Counter('-b')

        for cls in (Foo, Bar):
            parser = cls.parser
            self.assertTrue(parser.contains(Args([]), '-h'))
            self.assertFalse(parser.contains(Args([]), '-H'))
            self.assertTrue(parser.contains(Args([]), '-b=1'))
            self.assertFalse(parser.contains(Args([]), '-B=1'))
            self.assertFalse(parser.contains(Args([]), '-ba'))
            self.assertTrue(parser.contains(Args([]), '--bar=1'))
            self.assertFalse(parser.contains(Args([]), '--baz=1'))
            self.assertFalse(parser.contains(Args([]), 'baz'))
            self.assertTrue(parser.contains(Args([]), '-b=1'))
            self.assertFalse(parser.contains(Args([]), '-B=1'))
            self.assertTrue(parser.contains(Args([]), '-bb'))
            self.assertFalse(parser.contains(Args([]), '-ab'))

    def test_parser_does_not_contain_triple_dash(self):
        class Foo(Command):
            pass

        self.assertFalse(Foo.parser.contains(Args([]), '---'))

    def test_parser_does_not_contain_combined_short(self):
        class Foo(Command):
            test = Flag('-t')

        self.assertFalse(Foo.parser.contains(Args([]), '-test'))

    def test_parser_contains_combined_short(self):
        class Foo(Command):
            foo = Flag('-f')
            bar = Flag('-b')

        self.assertTrue(Foo.parser.contains(Args([]), '-fb'))

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


if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    try:
        main(warnings='ignore', verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
