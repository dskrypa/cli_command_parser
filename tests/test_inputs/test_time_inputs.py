#!/usr/bin/env python

from unittest import main, TestCase

from cli_command_parser import Command, Option
from cli_command_parser.core import get_params
from cli_command_parser.exceptions import UsageError
from cli_command_parser.inputs.time import Day
from cli_command_parser.inputs.exceptions import InvalidChoiceError, InputValidationError
from cli_command_parser.testing import ParserTest


class DayInputTest(TestCase):
    def test_format_required(self):
        with self.assertRaisesRegex(ValueError, 'At least one of .* must be True'):
            Day(full=False, abbreviation=False)

    def test_ko_in_en_out(self):
        self.assertEqual('Monday', Day(locale='ko_kr', out_locale='en_us')('월요일'))

    def test_numeric_input_iso(self):
        day = Day(numeric=True, iso=True, out_locale='en_us')
        self.assertEqual('Monday', day('1'))
        self.assertEqual('Tuesday', day('2'))
        self.assertEqual('Wednesday', day('3'))
        self.assertEqual('Thursday', day('4'))
        self.assertEqual('Friday', day('5'))
        self.assertEqual('Saturday', day('6'))
        self.assertEqual('Sunday', day('7'))

    def test_numeric_input_non_iso(self):
        day = Day(numeric=True, out_locale='en_us')
        self.assertEqual('Monday', day('0'))
        self.assertEqual('Tuesday', day('1'))
        self.assertEqual('Wednesday', day('2'))
        self.assertEqual('Thursday', day('3'))
        self.assertEqual('Friday', day('4'))
        self.assertEqual('Saturday', day('5'))
        self.assertEqual('Sunday', day('6'))

    def test_invalid_numeric(self):
        with self.assertRaisesRegex(InputValidationError, 'Invalid weekday=9'):
            Day(numeric=True).parse_dow('9')


class ParseInputTest(ParserTest):
    pass


if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    try:
        main(verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
