#!/usr/bin/env python

from enum import Enum
from unittest import main

from cli_command_parser import Command, Option
from cli_command_parser.exceptions import UsageError
from cli_command_parser.inputs.choices import ChoiceMap, Choices, EnumChoices
from cli_command_parser.inputs.exceptions import InvalidChoiceError
from cli_command_parser.testing import ParserTest, get_help_text


class EnumExample(Enum):
    FOO = '1'
    Bar = '2'
    baz = '3'


class ChoiceInputTest(ParserTest):
    def test_invalid_choice_multi(self):
        e = InvalidChoiceError(('y', 'z'), ('a', 'b', 'c'))
        self.assertEqual("invalid choices: 'y', 'z' (choose from: 'a', 'b', 'c')", str(e))

    def test_enum_replaced(self):
        class Foo(Command):
            bar = Option(type=EnumExample)

        self.assertIsInstance(Foo.bar.type, EnumChoices)

    def test_enum_with_choices(self):
        class Foo(Command):
            bar = Option(type=EnumExample, choices=(EnumExample.FOO, EnumExample.Bar))

        self.assertIsInstance(Foo.bar.type, Choices)
        self.assertIsInstance(Foo.bar.type.type, EnumChoices)
        self.assertIs(Foo.bar.type.type.type, EnumExample)

    def test_enum_repr(self):
        expected = '<EnumChoices[type=EnumExample, case_sensitive=False, choices=(FOO,Bar,baz)]>'
        self.assertEqual(expected, repr(EnumChoices(EnumExample)))

    def test_enum_help_text(self):
        for sort_choices, expected in ((False, '{FOO|Bar|baz}'), (True, '{Bar|FOO|baz}')):

            class Foo(Command, sort_choices=sort_choices):
                bar = Option('-b', type=EnumExample)

            self.assert_str_contains(expected, get_help_text(Foo))

    def test_enum_case_sensitive(self):
        # fmt: off
        val_exp_map = {
            'FOO': EnumExample.FOO, 'Bar': EnumExample.Bar, 'baz': EnumExample.baz,
            '1': EnumExample.FOO, '2': EnumExample.Bar, '3': EnumExample.baz,
        }
        # fmt: on
        ec = EnumChoices(EnumExample, case_sensitive=True)
        for value, expected in val_exp_map.items():
            self.assertEqual(expected, ec(value))
            self.assertIn(value, ec)

        for val in ('bar', 'test', 'foo', 'BAZ', '0', '4'):
            with self.subTest(val=val):
                self.assertNotIn(val, ec)
                with self.assert_raises_contains_str(InvalidChoiceError, "choose from: 'FOO', 'Bar', 'baz'"):
                    ec(val)

    def test_enum_case_insensitive(self):
        # fmt: off
        val_exp_map = {
            'foo': EnumExample.FOO, 'FOO': EnumExample.FOO, '1': EnumExample.FOO,
            'bar': EnumExample.Bar, 'Bar': EnumExample.Bar, 'BAR': EnumExample.Bar, '2': EnumExample.Bar,
            'baz': EnumExample.baz, 'BAZ': EnumExample.baz, '3': EnumExample.baz,
        }
        # fmt: on
        ec = EnumChoices(EnumExample, case_sensitive=False)
        for value, expected in val_exp_map.items():
            self.assertEqual(expected, ec(value))
            self.assertIn(value, ec)

        for val in ('test', 'BAT', '0', '4'):
            with self.subTest(val=val):
                self.assertNotIn(val, ec)
                with self.assert_raises_contains_str(InvalidChoiceError, "choose from: 'FOO', 'Bar', 'baz'"):
                    ec(val)

    def test_choices_rejects_typed_insensitive(self):
        with self.assert_raises_contains_str(TypeError, 'Cannot combine case_sensitive=False'):
            Choices((1, 2, 3), case_sensitive=False)

    def test_choices_rejects_bad_enum_choices(self):
        with self.assert_raises_contains_str(TypeError, 'Invalid choices='):
            Choices(EnumExample._member_map_, EnumChoices(EnumExample))

    def test_choices_typed_repr(self):
        choices = Choices((1, 2, 3), type=int)
        self.assertEqual('<Choices[type=int, case_sensitive=True, choices=(1,2,3)]>', repr(choices))

    def test_choices_ints(self):
        choices = Choices((1, 2, 3), type=int)
        for n in range(1, 4):
            self.assertEqual(n, choices(str(n)))

        for val in ('-1', '0', '4', '10', 'foo'):
            with self.subTest(val=val):
                with self.assert_raises_contains_str(InvalidChoiceError, 'choose from: 1, 2, 3'):
                    choices(val)

    def test_choices_strs_sensitive(self):
        choices = Choices(('FOO', 'Bar', 'baz'))
        for val in ('FOO', 'Bar', 'baz'):
            self.assertIn(val, choices)

        for val in ('test', 'BAT', '0', '4', 'foo', 'bar', 'BAZ'):
            self.assertNotIn(val, choices)

    def test_choices_strs_insensitive(self):
        choices = Choices(('FOO', 'Bar', 'baz'), case_sensitive=False)
        for val in ('FOO', 'Bar', 'baz', 'foo', 'bar', 'BAZ'):
            self.assertIn(val, choices)

        for val in ('test', 'BAT', '0', '4'):
            self.assertNotIn(val, choices)

    def test_choice_map_sensitive(self):
        val_exp_map = {'FOO': 1, 'Bar': 2, 'baz': 3}
        cm = ChoiceMap({'FOO': 1, 'Bar': 2, 'baz': 3})
        for value, expected in val_exp_map.items():
            self.assertEqual(expected, cm(value))

        for val in ('test', 'BAT', '0', '4', 'foo', 'bar', 'BAZ'):
            self.assertNotIn(val, cm)

    def test_choice_map_insensitive(self):
        val_exp_map = {'FOO': 1, 'Bar': 2, 'baz': 3, 'foo': 1, 'bar': 2, 'BAZ': 3}
        cm = ChoiceMap({'FOO': 1, 'Bar': 2, 'baz': 3}, case_sensitive=False)
        for value, expected in val_exp_map.items():
            self.assertEqual(expected, cm(value))

        for val in ('test', 'BAT', '0', '4'):
            self.assertNotIn(val, cm)


class ParseInputTest(ParserTest):
    def test_int_choices(self):
        class Foo(Command):
            bar: int = Option('-b', choices=(1, 2))
            baz = Option('-B', type=int, choices=(1, 2))

        success_cases = [
            (['-b1', '-B=2'], {'bar': 1, 'baz': 2}),
            (['-b2', '-B=1'], {'bar': 2, 'baz': 1}),
            (['-B=1'], {'bar': None, 'baz': 1}),
        ]
        fail_cases = [['-ba'], ['-b0'], ['-b3'], ['-Ba'], ['-B0'], ['-B3'], ['-b', '-1'], ['-b', '']]
        self.assert_parse_results_cases(Foo, success_cases)
        self.assert_parse_fails_cases(Foo, fail_cases, UsageError)

    def test_choices_with_nargs_plus(self):
        class Foo(Command):
            bar: int = Option('-b', choices=(1, 2), nargs='+')

        success_cases = [
            (['-b1'], {'bar': [1]}),
            (['-b2'], {'bar': [2]}),
            (['-b', '1', '1', '1'], {'bar': [1, 1, 1]}),
            (['--bar', '2'], {'bar': [2]}),
        ]
        fail_cases = [['-ba'], ['-b0'], ['-b', '1', '3'], ['-b', '-1'], ['-b', '11']]
        self.assert_parse_results_cases(Foo, success_cases)
        self.assert_parse_fails_cases(Foo, fail_cases, UsageError)

    def test_enum_type_validation(self):
        class Foo(Command):
            bar = Option('-b', type=EnumExample)

        # fmt: off
        val_exp_map = {
            'foo': EnumExample.FOO, 'FOO': EnumExample.FOO, '1': EnumExample.FOO,
            'bar': EnumExample.Bar, 'Bar': EnumExample.Bar, 'BAR': EnumExample.Bar, '2': EnumExample.Bar,
            'baz': EnumExample.baz, 'BAZ': EnumExample.baz, '3': EnumExample.baz,
        }
        # fmt: on
        success_cases = [(['-b', val], {'bar': exp}) for val, exp in val_exp_map.items()]
        fail_cases = [['-b', val] for val in ('test', 'BAT', '0', '4')]
        self.assert_parse_results_cases(Foo, success_cases)
        self.assert_parse_fails_cases(Foo, fail_cases, UsageError)

    def test_enum_with_choices(self):
        class Foo(Command):
            bar = Option('-b', type=EnumExample, choices=(EnumExample.FOO, EnumExample.Bar))

        # fmt: off
        val_exp_map = {
            'foo': EnumExample.FOO, 'FOO': EnumExample.FOO, '1': EnumExample.FOO,
            'bar': EnumExample.Bar, 'Bar': EnumExample.Bar, 'BAR': EnumExample.Bar, '2': EnumExample.Bar,
        }
        # fmt: on
        success_cases = [(['-b', val], {'bar': exp}) for val, exp in val_exp_map.items()]
        fail_cases = [['-b', val] for val in ('test', 'BAT', '0', '4', 'baz', 'BAZ', '3')]
        self.assert_parse_results_cases(Foo, success_cases)
        self.assert_parse_fails_cases(Foo, fail_cases, UsageError)

    def test_choice_map_default_fixed(self):
        class Foo(Command):
            bar = Option('-b', default='a', type=ChoiceMap({'a': 'ABC', 'x': 'XYZ'}))

        success_cases = [([], {'bar': 'ABC'}), (['-b', 'a'], {'bar': 'ABC'}), (['-b', 'x'], {'bar': 'XYZ'})]
        self.assert_parse_results_cases(Foo, success_cases)

    def test_choice_map_default_in_values(self):
        class Foo(Command):
            bar = Option('-b', default='ABC', type=ChoiceMap({'a': 'ABC', 'x': 'XYZ'}))

        success_cases = [([], {'bar': 'ABC'}), (['-b', 'a'], {'bar': 'ABC'}), (['-b', 'x'], {'bar': 'XYZ'})]
        self.assert_parse_results_cases(Foo, success_cases)

    def test_choice_map_default_not_fixed(self):
        class Foo(Command):
            bar = Option('-b', default='a', type=ChoiceMap({'a': 'ABC', 'x': 'XYZ'}), strict_default=True)

        success_cases = [([], {'bar': 'a'}), (['-b', 'a'], {'bar': 'ABC'}), (['-b', 'x'], {'bar': 'XYZ'})]
        self.assert_parse_results_cases(Foo, success_cases)


if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    try:
        main(verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
