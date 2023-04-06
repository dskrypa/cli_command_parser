#!/usr/bin/env python

# from argparse import ArgumentParser as _ArgumentParser
from textwrap import dedent
from unittest import TestCase, main

from cli_command_parser.conversion.argparse_ast import Script, AstArgumentParser
from cli_command_parser.conversion.argparse_utils import ArgumentParser, SubParsersAction
from cli_command_parser.conversion.command_builder import convert_script
from cli_command_parser.conversion.utils import get_name_repr
from cli_command_parser.conversion.visitor import ScriptVisitor
from cli_command_parser.testing import ParserTest

DISCLAIMER = '# This is an automatically generated name that should probably be updated'
IMPORT_LINE = (
    'from cli_command_parser import Command, SubCommand, ParamGroup, Positional, Option, Flag, Counter, PassThru, main'
)


class ArgparseConversionTest(ParserTest):
    def test_argparse_typing_helpers(self):
        parser = ArgumentParser()
        parser.register('action', 'parsers', SubParsersAction)
        sp_action = parser.add_subparsers(dest='action', prog='')
        self.assertIsInstance(sp_action, SubParsersAction)
        sub_parser = sp_action.add_parser('test')
        self.assertIsNotNone(sub_parser.add_mutually_exclusive_group())
        self.assertIsNotNone(sub_parser.add_argument_group('test'))

    def test_get_name_repr_bad_type(self):
        with self.assertRaises(TypeError):
            get_name_repr('foo')  # noqa

    def test_renamed_import_and_remainder(self):
        code = """
from argparse import ArgumentParser as ArgParser, REMAINDER
parser = ArgParser()
parser.add_argument('test', nargs=REMAINDER)
        """
        expected = f'{IMPORT_LINE}\n\n\nclass Command0(Command):  {DISCLAIMER}\n    test = PassThru()'
        self.assertEqual(expected, convert_script(Script(code)))

    def test_sub_parser_args_in_loop(self):
        code = """
import argparse
parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers(dest='action')
sp1 = subparsers.add_parser('one', help='Command one')
sp1.add_argument('--foo-bar', '-f', action='store_true', help='Do foo bar')
sp2 = subparsers.add_parser('two', description='Command two')
sp2.add_argument('--baz', '-b', nargs='+', help='What to baz')
for sp in (sp1, sp2):
    group = sp.add_argument_group('Common options')
    group.add_argument('--verbose', '-v', action='count', default=0, help='Increase logging verbosity')
    group.add_argument('--dry-run', '-D', action='store_true', help='Perform a dry run with no side effects')
        """
        expected_base = (
            f"{IMPORT_LINE}\n\n\nclass Command0(Command, option_name_mode='-'):  {DISCLAIMER}\n"
            '    action = SubCommand()'
        )
        common = (
            "\n    with ParamGroup(description='Common options'):\n"
            "        verbose = Counter('-v', help='Increase logging verbosity')\n"
            "        dry_run = Flag('-D', help='Perform a dry run with no side effects')"
        )
        expected_smart = f"""{expected_base}\n{common}
\n
class One(Command0, help='Command one'):
    foo_bar = Flag('-f', help='Do foo bar')
\n
class Two(Command0, description='Command two'):
    baz = Option('-b', nargs='+', help='What to baz')
        """.rstrip()
        expected_split = f"""{expected_base}
\n
class One(Command0, help='Command one'):
    foo_bar = Flag('-f', help='Do foo bar')
{common}
\n
class Two(Command0, description='Command two'):
    baz = Option('-b', nargs='+', help='What to baz')
{common}
        """.rstrip()
        with self.subTest(smart_loop_handling=True):
            self.assert_strings_equal(expected_smart, convert_script(Script(code)))
        with self.subTest(smart_loop_handling=False):
            self.assert_strings_equal(expected_split, convert_script(Script(code, False)))


if __name__ == '__main__':
    try:
        main(verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
