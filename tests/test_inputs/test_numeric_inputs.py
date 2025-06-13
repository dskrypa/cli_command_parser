#!/usr/bin/env python

from unittest import main

from cli_command_parser import Command, Option
from cli_command_parser.exceptions import BadArgument, ParameterDefinitionError
from cli_command_parser.inputs import InputValidationError, NumRange, Range
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


class ParseInputTest(ParserTest):
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


if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    try:
        main(verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
