#!/usr/bin/env python

import re
from typing import Match
from unittest import main

from cli_command_parser import Command, Option
from cli_command_parser.exceptions import ParameterDefinitionError
from cli_command_parser.inputs import Glob, InputValidationError, Regex, RegexMode
from cli_command_parser.testing import ParserTest

PAT = re.compile('foo')


class RegexInputTest(ParserTest):
    # region Inputs.__init__ Replacement / Validation

    def test_pattern_type_replaced(self):
        class Foo(Command):
            bar = Option(type=PAT)

        self.assertIsInstance(Foo.bar.type, Regex)

    def test_pattern_choices_rejected(self):
        with self.assertRaisesRegex(ParameterDefinitionError, 'Invalid choices=.* - use type=.* instead'):

            class Foo(Command):
                bar = Option(choices=PAT)  # noqa

    def test_pattern_with_choices_rejected(self):
        with self.assertRaisesRegex(ParameterDefinitionError, 'Cannot combine type=.* with choices='):
            Option(type=PAT, choices=('a', 'b'))
        with self.assertRaisesRegex(ParameterDefinitionError, 'Cannot combine type=.* with choices='):
            Option(type=Regex(PAT), choices=('a', 'b'))

    # endregion

    # region Initialization

    def test_no_patterns(self):
        with self.assert_raises_contains_str(TypeError, 'At least one regex pattern is required'):
            Regex()

    def test_group_and_groups(self):
        with self.assertRaisesRegex(TypeError, 'Invalid combination of group=.*only one may be provided'):
            Regex(PAT, group=1, groups=(1, 2))

    def test_default_modes(self):
        self.assertEqual(RegexMode.STRING, Regex(PAT).mode)
        self.assertEqual(RegexMode.GROUP, Regex(PAT, group=1).mode)
        self.assertEqual(RegexMode.GROUPS, Regex(PAT, groups=(1,)).mode)

    def test_bad_mode_combos(self):
        with self.assertRaisesRegex(ValueError, 'Invalid regex mode=.*only GROUP is supported'):
            Regex(PAT, mode='match', group=1)
        with self.assertRaisesRegex(ValueError, 'Invalid regex mode=.*only GROUPS is supported'):
            Regex(PAT, mode='match', groups=(1,))

    # endregion

    # region Output Mode Tests

    def test_all_groups_result(self):
        self.assertEqual(('foo', 'bar'), Regex('(foo)(bar)', mode='groups')('foobarbaz'))

    def test_specific_groups_result(self):
        self.assertEqual(('foo', 'baz'), Regex('(foo)(bar)(baz)', groups=(1, 3))('foobarbaz'))

    def test_group_dict_result(self):
        self.assertEqual({'foo': 'bar'}, Regex('(?P<foo>bar)', mode='dict')('foobarbaz'))

    def test_specific_group_result(self):
        self.assertEqual('bar', Regex('(foo)(bar)(baz)', group=2)('foobarbaz'))

    def test_default_group_result(self):
        self.assertEqual('foobar', Regex('(foo)(bar)', mode='group')('foobarbaz'))
        self.assertEqual('bar', Regex('bar', mode='group')('barbaz'))
        self.assertEqual('bar', Regex('foo', 'bar', mode='group')('barbaz'))

    def test_string_result(self):
        self.assertEqual('foobarbaz', Regex('(foo)(bar)')('foobarbaz'))

    def test_match_result(self):
        self.assertIsInstance(Regex('(foo)(bar)', mode='match')('foobarbaz'), Match)

    # endregion

    def test_non_match(self):
        with self.assert_raises_contains_str(InputValidationError, 'expected a value matching'):
            Regex(PAT)('barbaz')
        with self.assert_raises_contains_str(InputValidationError, 'expected a value matching'):
            Regex(PAT, 'foobar')('barbaz')

    def test_strings(self):
        r = Regex('foo', 'bar')
        self.assertEqual('bar | foo', r.format_metavar(sort_choices=True))
        self.assertEqual('foo | bar', r.format_metavar())


class GlobInputTest(ParserTest):
    def test_pattern_with_choices_rejected(self):
        with self.assertRaisesRegex(ParameterDefinitionError, 'Cannot combine type=.* with choices='):
            Option(type=Glob('foo'), choices=('a', 'b'))

    def test_no_patterns(self):
        with self.assert_raises_contains_str(TypeError, 'At least one glob/fnmatch pattern is required'):
            Glob()

    def test_strings(self):
        g = Glob('foo', 'bar')
        self.assertEqual('bar | foo', g.format_metavar(sort_choices=True))
        self.assertEqual('foo | bar', g.format_metavar())

    def test_non_match(self):
        with self.assert_raises_contains_str(InputValidationError, 'expected a value matching'):
            Glob('foo')('barbaz')
        with self.assert_raises_contains_str(InputValidationError, 'expected a value matching'):
            Glob('foo', 'foobar')('barbaz')
        with self.assert_raises_contains_str(InputValidationError, 'expected a value matching'):
            Glob('FOO', match_case=True)('foo')

    def test_match(self):
        self.assertEqual('foobarbaz', Glob('foo*')('foobarbaz'))
        self.assertEqual('foobarbaz', Glob('foo*', normcase=True)('foobarbaz'))
        self.assertEqual('barbaz', Glob('foo*', '*bar*')('barbaz'))
        self.assertEqual('foo', Glob('FOO')('foo'))


class ParseInputTest(ParserTest):
    def test_regex_parsing(self):
        class Foo(Command):
            bar = Option('-b', type=Regex(PAT, mode='group'), default='xyz')

        success_cases = [([], {'bar': 'xyz'}), (['-b', 'foobar'], {'bar': 'foo'}), (['-b', 'foo'], {'bar': 'foo'})]
        self.assert_parse_results_cases(Foo, success_cases)
        self.assert_argv_parse_fails_cases(Foo, [['-ba'], ['-b', '-1'], ['-b', 'bar']])


if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    try:
        main(verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
