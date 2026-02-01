#!/usr/bin/env python

from unittest import main

from cli_command_parser import Command, Option
from cli_command_parser.exceptions import BadArgument, ParameterDefinitionError
from cli_command_parser.inputs import Bytes, InputValidationError, NumRange, Range
from cli_command_parser.testing import ParserTest


class NumericInputTest(ParserTest):
    def test_range_replaced(self):
        class Foo(Command):
            bar: int = Option(type=range(10))
            baz: int = Option(choices=range(10))

        self.assertIsInstance(Foo.bar.type, Range)  # noqa
        self.assertIsInstance(Foo.baz.type, Range)  # noqa

    def test_range_with_choices_rejected(self):
        with self.assertRaisesRegex(ParameterDefinitionError, 'Cannot combine type=.* with choices='):
            Option(type=range(10), choices=(1, 2))
        with self.assertRaisesRegex(ParameterDefinitionError, 'Cannot combine type=.* with choices='):
            Option(type=Range(range(10)), choices=(1, 2))

    def test_range_no_snap(self):
        for case in (range(10), range(9, -1, -1)):
            with self.subTest(case=case):
                rng = Range(case)
                for n in range(10):
                    self.assertEqual(n, rng(str(n)))

                for val in ('-1', '10', '11', '1.1'):
                    with self.assertRaises(ValueError):
                        rng(val)

    def test_range_str(self):
        self.assertEqual('{0 <= N <= 9}', Range(range(10)).format_metavar())
        self.assertEqual('{0 <= N <= 9}', Range(range(9, -1, -1)).format_metavar())
        self.assertEqual('{0 <= N <= 8, step=2}', Range(range(0, 10, 2)).format_metavar())
        self.assertEqual('{0 <= N <= 8, step=2}', Range(range(8, -1, -2)).format_metavar())

    def test_range_snap(self):
        for case in (range(10), range(9, -1, -1)):
            with self.subTest(case=case):
                rng = Range(case, snap=True)
                for n in range(10):
                    self.assertEqual(n, rng(str(n)))

                self.assertEqual(0, rng('-1'))
                self.assertEqual(0, rng('-10'))
                self.assertEqual(9, rng('10'))
                self.assertEqual(9, rng('20'))

    def test_range_with_type(self):
        rng = Range(range(10), type=lambda x: int(x))
        for n in range(10):
            self.assertEqual(n, rng(str(n)))

    def test_num_range_str(self):
        self.assertEqual('0 <= N < 10', NumRange(min=0, max=10)._range_str())
        self.assertEqual('0 <= N', NumRange(min=0)._range_str())
        self.assertEqual('N < 10', NumRange(max=10)._range_str())
        self.assertEqual('0 <= N <= 10', NumRange(min=0, max=10, include_max=True)._range_str())
        self.assertEqual('0 < N < 10', NumRange(min=0, max=10, include_min=False)._range_str())
        self.assertEqual('0 < N <= 10', NumRange(min=0, max=10, include_min=False, include_max=True)._range_str())

    def test_num_range_repr(self):
        self.assertEqual("<NumRange(<class 'int'>, snap=False)[0 <= N]>", repr(NumRange(min=0)))

    def test_num_range_requires_min_max(self):
        with self.assert_raises_contains_str(ValueError, 'at least one of min and/or max values'):
            NumRange()

    def test_num_range_requires_min_lt_max(self):
        with self.assert_raises_contains_str(ValueError, 'min must be less than max'):
            NumRange(min=10, max=0)

    def test_num_range_snap_requires_strict_range(self):
        with self.assert_raises_contains_str(ValueError, 'snap would produce invalid values'):
            NumRange(snap=True, min=1, max=2)

    def test_snap_rejects_float(self):
        with self.assert_raises_contains_str(TypeError, 'Unable to snap to extrema with type=float'):
            NumRange(snap=True, type=float, min=1)

    def test_num_range_auto_type(self):
        self.assertIs(int, NumRange(min=1, max=10).type)
        self.assertIs(float, NumRange(min=1.5, max=10).type)
        self.assertIs(float, NumRange(min=1.5, max=10.5).type)

    def test_num_range_snap_incl_min(self):
        rng = NumRange(snap=True, min=0, max=10)
        for n in range(10):
            self.assertEqual(n, rng(str(n)))

        self.assertEqual(0, rng('-1'))
        self.assertEqual(0, rng('-10'))
        self.assertEqual(9, rng('10'))
        self.assertEqual(9, rng('20'))

    def test_num_range_snap_excl_min(self):
        rng = NumRange(snap=True, min=-1, max=10, include_min=False)
        for n in range(10):
            self.assertEqual(n, rng(str(n)))

        self.assertEqual(0, rng('-1'))
        self.assertEqual(0, rng('-10'))
        self.assertEqual(9, rng('10'))
        self.assertEqual(9, rng('20'))

    def test_num_range_snap_incl_max(self):
        rng = NumRange(snap=True, min=0, max=9, include_max=True)
        for n in range(10):
            self.assertEqual(n, rng(str(n)))

        self.assertEqual(0, rng('-1'))
        self.assertEqual(0, rng('-10'))
        self.assertEqual(9, rng('10'))
        self.assertEqual(9, rng('20'))

    def test_num_range_unbound_min(self):
        rng = NumRange(max=10)
        for val in ('10', '20', '100'):
            with self.assertRaises(ValueError):
                rng(val)

        for val in (0, 1, 9, -1, -20, -100):
            self.assertEqual(val, rng(str(val)))

    def test_num_range_unbound_max(self):
        rng = NumRange(min=0)
        for val in ('-1', '-10', '-100'):
            with self.assertRaises(ValueError):
                rng(val)

        for val in (0, 1, 10, 100):
            self.assertEqual(val, rng(str(val)))

    def test_init_from_tuple(self):
        self.assertEqual(range(1, 3), Range((1, 3)).range)


class BytesInputTest(ParserTest):
    def test_invalid_base_rejected(self):
        for case in (1, 3, 5, 'foo', None):
            with self.subTest(case=case), self.assert_raises_contains_str(ValueError, 'Invalid 2-character unit base='):
                Bytes(base=case)  # noqa

    def test_bytes_repr(self):
        self.assertIn('base=10, short=True, fractions=False', repr(Bytes()))

    def test_bytes_valid_type(self):
        cases = {
            '-12.34kb': True,
            '-12.34 kB': True,
            '1234 MiB': True,
            '12GiB': True,
            '5T': True,
            '0 B': True,
            '1234': True,
            '-100': True,
            'G1234': False,
            'foo': False,
            '': False,
        }
        for value, valid in cases.items():
            with self.subTest(value=value, valid=valid):
                self.assertEqual(valid, Bytes.is_valid_type(value))

    def test_bytes_metavar(self):
        self.assertEqual('BYTES[B|KB|MiB|...]', Bytes().format_metavar())

    def test_type_descriptions(self):
        cases = [
            (Bytes(), 'a positive integer byte count/size'),
            (Bytes(negative=True), 'an integer byte count/size'),
            (Bytes(negative=True, fractions=True), 'a byte count/size'),
        ]
        for obj, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(expected, obj._type_desc())

    def test_invalid_bytes_type_error(self):
        self.assertFalse(Bytes.is_valid_type(None))  # noqa

    def test_invalid_bytes_call(self):
        with self.assert_raises_contains_str(InputValidationError, 'with optional unit'):
            Bytes()('')

    def test_invalid_byte_unit_multiplier(self):
        with self.assert_raises_contains_str(InputValidationError, "invalid byte unit='A'"):
            Bytes()._get_multiplier('A')


class ParseInputTest(ParserTest):
    def test_num_range_validation(self):
        class Foo(Command):
            bar = Option('-b', type=NumRange(int, min=-10, max=10))

        success_cases = [
            ([], {'bar': None}),
            (['-b0'], {'bar': 0}),
            (['-b', '-1'], {'bar': -1}),
            (['--bar', '-9'], {'bar': -9}),
            (['--bar', '-10'], {'bar': -10}),
            (['--bar', '9'], {'bar': 9}),
        ]
        self.assert_parse_results_cases(Foo, success_cases)
        self.assert_argv_parse_fails_cases(Foo, [['-ba'], ['-b', '-11'], ['-b', '11']])

    def test_range_type_validation(self):
        class Foo(Command):
            bar = Option('-b', type=Range(range(10)), default='3')

        success_cases = [
            ([], {'bar': 3}),
            (['-b0'], {'bar': 0}),
            (['-b1'], {'bar': 1}),
            (['-b', '5'], {'bar': 5}),
            (['--bar', '9'], {'bar': 9}),
        ]
        self.assert_parse_results_cases(Foo, success_cases)
        self.assert_argv_parse_fails_cases(Foo, [['-ba'], ['-b', '-1'], ['-b', '11']])

    def test_fix_default(self):
        class Foo(Command):
            bar = Option(type=Range(range(10), fix_default=True), default='-10')
            baz = Option(type=Range(range(10), fix_default=False), default='-10')

        with self.assert_raises_contains_str(BadArgument, 'bad default value - expected a value in the range'):
            Foo().bar  # noqa

        self.assertEqual('-10', Foo().baz)

    def test_bytes_validation_base_10(self):
        class Foo(Command):
            bar = Option(type=Bytes(base=10, fractions=True, negative=True))
            baz = Option(type=Bytes(short=False))

        success_cases = [
            ([], {'bar': None, 'baz': None}),
            (['--bar', '-1.2MB'], {'bar': -1_200_000, 'baz': None}),
            (['--bar', '-1.23 KiB'], {'bar': -1_259.52, 'baz': None}),
            (['--bar', '-1.2k'], {'bar': -1_200, 'baz': None}),
            (['--bar', '1.2k'], {'bar': 1_200, 'baz': None}),
            (['--bar', '12kb'], {'bar': 12_000, 'baz': None}),
            (['--bar', '10MiB'], {'bar': 10_485_760, 'baz': None}),
            (['--bar', '12'], {'bar': 12, 'baz': None}),
            (['--baz', '12b'], {'bar': None, 'baz': 12}),
            (['--baz', '0QB'], {'bar': None, 'baz': 0}),
        ]
        fail_cases = [
            ['--baz', '-1.2MB'],
            ['--baz', '-1.23 KiB'],
            ['--baz', '-1.2k'],
            ['--baz', '1.2k'],
            ['--baz', '12k'],
            ['--baz', '-10'],
        ]
        self.assert_parse_results_cases(Foo, success_cases)
        self.assert_argv_parse_fails_cases(Foo, fail_cases)

    def test_bytes_validation_base_2(self):
        class Foo(Command):
            bar = Option(type=Bytes(base=2, fractions=True, negative=True))
            baz = Option(type=Bytes(base=2, short=False))

        success_cases = [
            ([], {'bar': None, 'baz': None}),
            (['--bar', '-1.2MB'], {'bar': -1_258_291.2, 'baz': None}),
            (['--bar', '-1.23 KiB'], {'bar': -1_259.52, 'baz': None}),
            (['--bar', '-1.2k'], {'bar': -1_228.8, 'baz': None}),
            (['--bar', '1.2k'], {'bar': 1_228.8, 'baz': None}),
            (['--bar', '12kb'], {'bar': 12_288, 'baz': None}),
            (['--bar', '10MiB'], {'bar': 10_485_760, 'baz': None}),
            (['--bar', '12'], {'bar': 12, 'baz': None}),
            (['--baz', '12b'], {'bar': None, 'baz': 12}),
            (['--baz', '0QB'], {'bar': None, 'baz': 0}),
        ]
        fail_cases = [
            ['--baz', '-1.2MB'],
            ['--baz', '-1.23 KiB'],
            ['--baz', '-1.2k'],
            ['--baz', '1.2k'],
            ['--baz', '12k'],
            ['--baz', '-10'],
        ]
        self.assert_parse_results_cases(Foo, success_cases)
        self.assert_argv_parse_fails_cases(Foo, fail_cases)


if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    try:
        main(verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
