#!/usr/bin/env python

from unittest import TestCase, main

from cli_command_parser.nargs import Nargs


class NargsTest(TestCase):
    # region Normal Input Tests

    def test_int(self):
        for n in range(11):
            with self.subTest(n=n):
                nargs = Nargs(n)
                self.assertIs(nargs.range, None)
                self.assertEqual(nargs.min, nargs.max)
                self.assertEqual(nargs.min, n)
                self.assertEqual(nargs.allowed, (n,))
                self.assertFalse(nargs.variable)
                self.assertIn(str(n), repr(nargs))
                self.assertEqual(str(nargs), str(n))
                self.assertEqual(nargs, Nargs((n, n)))
                self.assertEqual(nargs, n)
                self.assertIn(n, nargs)
                self.assertFalse(nargs.satisfied(-1))
                self.assertTrue(nargs.satisfied(n))
                self.assertFalse(nargs.satisfied(n - 1))
                self.assertFalse(nargs.satisfied(n + 1))

    def test_question(self):
        nargs = Nargs('?')
        self.assertIs(nargs.range, None)
        self.assertEqual(nargs.min, 0)
        self.assertEqual(nargs.max, 1)
        self.assertEqual(nargs.allowed, (0, 1))
        self.assertTrue(nargs.variable)
        self.assertIn('?', repr(nargs))
        self.assertEqual(str(nargs), '0 ~ 1')
        self.assertEqual(nargs, Nargs((0, 1)))
        self.assertNotIn(-1, nargs)
        self.assertIn(0, nargs)
        self.assertIn(1, nargs)
        self.assertNotIn(2, nargs)
        self.assertFalse(nargs.satisfied(-1))
        self.assertTrue(nargs.satisfied(0))
        self.assertTrue(nargs.satisfied(1))
        self.assertFalse(nargs.satisfied(2))
        self.assertFalse(nargs.satisfied(100))

    def test_star(self):
        nargs = Nargs('*')
        self.assertIs(nargs.range, None)
        self.assertEqual(nargs.min, 0)
        self.assertIs(nargs.max, None)
        self.assertEqual(nargs.allowed, (0, None))
        self.assertTrue(nargs.variable)
        self.assertIn('*', repr(nargs))
        self.assertEqual(str(nargs), '0 or more')
        self.assertEqual(nargs, Nargs('*'))
        self.assertNotIn(-1, nargs)
        self.assertIn(0, nargs)
        self.assertIn(1, nargs)
        self.assertIn(2, nargs)
        self.assertFalse(nargs.satisfied(-1))
        self.assertTrue(nargs.satisfied(0))
        self.assertTrue(nargs.satisfied(1))
        self.assertTrue(nargs.satisfied(2))
        self.assertTrue(nargs.satisfied(100))

    def test_plus(self):
        nargs = Nargs('+')
        self.assertIs(nargs.range, None)
        self.assertEqual(nargs.min, 1)
        self.assertIs(nargs.max, None)
        self.assertEqual(nargs.allowed, (1, None))
        self.assertTrue(nargs.variable)
        self.assertIn('+', repr(nargs))
        self.assertEqual(str(nargs), '1 or more')
        self.assertEqual(nargs, Nargs('+'))
        self.assertNotIn(-1, nargs)
        self.assertNotIn(0, nargs)
        self.assertIn(1, nargs)
        self.assertIn(2, nargs)
        self.assertFalse(nargs.satisfied(-1))
        self.assertFalse(nargs.satisfied(0))
        self.assertTrue(nargs.satisfied(1))
        self.assertTrue(nargs.satisfied(2))
        self.assertTrue(nargs.satisfied(100))

    def test_tuple_static(self):
        for n in range(11):
            with self.subTest(n=n):
                case = (n, n)
                nargs = Nargs(case)
                self.assertIs(nargs.range, None)
                self.assertEqual(nargs.min, nargs.max)
                self.assertEqual(nargs.min, n)
                self.assertEqual(nargs.allowed, case)
                self.assertFalse(nargs.variable)
                self.assertIn(str(case), repr(nargs))
                self.assertEqual(str(nargs), str(n))
                self.assertEqual(nargs, Nargs(n))
                self.assertNotIn(-1, nargs)
                self.assertIn(n, nargs)
                self.assertNotIn(n - 1, nargs)
                self.assertNotIn(n + 1, nargs)
                self.assertFalse(nargs.satisfied(-1))
                self.assertTrue(nargs.satisfied(n))
                self.assertFalse(nargs.satisfied(n - 1))
                self.assertFalse(nargs.satisfied(n + 1))

    def test_seq_range(self):
        for a in range(5):
            for b in range(a, 11):
                for case in (a, b), [a, b]:
                    with self.subTest(case=case):
                        nargs = Nargs(case)
                        self.assertIs(nargs.range, None)
                        self.assertEqual(nargs.min, a)
                        self.assertEqual(nargs.max, b)
                        self.assertEqual(nargs.allowed, case)
                        self.assertEqual(nargs.variable, a != b)
                        self.assertIn(str(case), repr(nargs))
                        self.assertEqual(str(nargs), str(a) if a == b else f'{a} ~ {b}')
                        self.assertEqual(nargs, Nargs(range(a, b + 1)))
                        self.assertNotIn(-1, nargs)
                        self.assertIn(a, nargs)
                        self.assertIn(b, nargs)
                        self.assertNotIn(a - 1, nargs)
                        self.assertNotIn(b + 1, nargs)
                        self.assertFalse(nargs.satisfied(-1))
                        self.assertTrue(nargs.satisfied(a))
                        self.assertTrue(nargs.satisfied(b))
                        self.assertFalse(nargs.satisfied(a - 1))
                        self.assertFalse(nargs.satisfied(b + 1))

    def test_range(self):
        for a in range(5):
            for b in range(a + 1, 11):
                case = range(a, b)
                with self.subTest(case=case):
                    nargs = Nargs(case)
                    self.assertEqual(nargs.range, case)
                    self.assertEqual(nargs.min, a)
                    self.assertEqual(nargs.max, b - 1)
                    self.assertEqual(nargs.allowed, case)
                    self.assertEqual(nargs.variable, a != (b - 1))
                    self.assertIn(str(case), repr(nargs))
                    self.assertEqual(str(nargs), f'{case.start} ~ {case.stop}')
                    self.assertEqual(nargs, Nargs((a, b - 1)))
                    self.assertNotIn(-1, nargs)
                    if a != b:
                        self.assertIn(a, nargs)
                        self.assertTrue(nargs.satisfied(a))
                        self.assertTrue(nargs.satisfied(b - 1))
                    self.assertNotIn(b, nargs)
                    self.assertNotIn(a - 1, nargs)
                    self.assertNotIn(b + 1, nargs)
                    self.assertFalse(nargs.satisfied(-1))
                    self.assertFalse(nargs.satisfied(a - 1))
                    self.assertFalse(nargs.satisfied(b + 1))

    def test_range_step(self):
        for a in range(5):
            for b in range(a + 1, 11):
                case = range(a, b, 2)
                with self.subTest(case=case):
                    nargs = Nargs(case)
                    self.assertEqual(nargs.range, case)
                    self.assertEqual(nargs.min, a)
                    last = (b - 2) if a % 2 == b % 2 else (b - 1)
                    self.assertEqual(nargs.max, last)
                    self.assertEqual(nargs.allowed, case)
                    self.assertEqual(nargs.variable, a != last)
                    self.assertIn(str(case), repr(nargs))
                    self.assertEqual(str(nargs), f'{case.start} ~ {case.stop} (step={case.step})')
                    self.assertEqual(nargs, Nargs(range(a, b, 2)))
                    self.assertNotIn(-1, nargs)
                    if a != b:
                        self.assertIn(a, nargs)
                        self.assertTrue(nargs.satisfied(a))
                    self.assertNotIn(a + 1, nargs)
                    self.assertNotIn(a - 1, nargs)
                    self.assertNotIn(b + 1, nargs)
                    self.assertFalse(nargs.satisfied(-1))
                    if b - a > 2:
                        self.assertTrue(nargs.satisfied(a + 2))
                    self.assertFalse(nargs.satisfied(a - 1))
                    self.assertFalse(nargs.satisfied(b + 1))

    def test_set_single(self):
        for n in range(5):
            with self.subTest(n=n):
                nargs = Nargs({n})
                self.assertEqual(nargs.min, n)
                self.assertEqual(nargs.max, n)
                self.assertEqual(nargs.allowed, {n})
                self.assertFalse(nargs.variable)
                self.assertIn(f'{n}', str(nargs))
                self.assertNotIn(-1, nargs)
                self.assertNotIn(n - 1, nargs)
                self.assertNotIn(None, nargs)
                self.assertIn(n, nargs)
                self.assertNotIn(n + 1, nargs)
                self.assertFalse(nargs.satisfied(-1))
                self.assertFalse(nargs.satisfied(n - 1))
                self.assertTrue(nargs.satisfied(n))
                self.assertFalse(nargs.satisfied(n + 1))
                self.assertEqual(nargs, n)
                self.assertEqual(nargs, Nargs(n))
                self.assertEqual(nargs, Nargs((n, n)))
                self.assertNotEqual(nargs, n - 1)
                self.assertNotEqual(nargs, n + 1)
                if n:
                    self.assertNotEqual(nargs, Nargs(n - 1))
                self.assertNotEqual(nargs, Nargs(n + 1))
                self.assertEqual(nargs, Nargs(range(n, n + 1)))
                self.assertNotEqual(nargs, Nargs(range(n + 2)))
                self.assertNotEqual(nargs, Nargs('+'))

    def test_tup_no_max(self):
        nargs = Nargs((3, None))
        self.assertNotEqual(nargs, Nargs('+'))
        self.assertNotEqual(nargs, Nargs('*'))
        self.assertIs(nargs.max, None)
        self.assertNotIn(0, nargs)
        self.assertNotIn(2, nargs)
        self.assertIn(3, nargs)
        self.assertIn(4, nargs)
        self.assertIn(100, nargs)

    # endregion

    # region Input Validation Tests

    def test_bad_set(self):
        for case in (set(), {-1}):
            with self.subTest(case=case), self.assertRaises(ValueError):
                Nargs(case)

        for case in (None, '', 'foo', 1.5, range(2)):
            with self.subTest(case=case), self.assertRaises(TypeError):
                Nargs({case})  # noqa

    def test_int_negative(self):
        for n in range(1, 11):
            with self.subTest(n=n), self.assertRaises(ValueError):
                Nargs(-n)

    def test_bad_types(self):
        cases = {'float': 1.5, 'seq_of_non_int': (1, 1.5), 'seq_of_str': ('a', 'b'), 'dict': {1: 2}}
        for case, value in cases.items():
            with self.subTest(case=case), self.assertRaises(TypeError):
                Nargs(value)

    def test_bad_str_values(self):
        for case in ('??', '**', '++', '?*', '*+', 'foo'):
            with self.subTest(case=case), self.assertRaises(ValueError):
                Nargs(case)

    def test_bad_seq_values(self):
        for case in ((2, 1), (-1, 2), (2, -1), (1, 0), (-1, 0)):
            for value in (case, range(*case)):
                with self.subTest(value=value), self.assertRaises(ValueError):
                    Nargs(value)

    def test_bad_seq_len(self):
        with self.assertRaises(ValueError):
            Nargs((1, 2, 3))

    def test_bad_step(self):
        with self.assertRaises(ValueError):
            Nargs(range(1, 2, -1))

    # endregion

    # region Misc Tests

    def test_range_step_contains(self):
        case = range(0, 6, 2)
        nargs = Nargs(case)
        self.assertNotIn(-1, nargs)
        self.assertIn(0, nargs)
        self.assertNotIn(1, nargs)
        self.assertIn(2, nargs)
        self.assertNotIn(3, nargs)
        self.assertIn(4, nargs)
        self.assertNotIn(7, nargs)
        self.assertNotIn(8, nargs)

    def test_eq_other(self):
        self.assertNotEqual(Nargs('+'), 'foo')

    def test_hashable(self):
        self.assertEqual(2, len({Nargs(1), Nargs(1), Nargs(2)}))

    def test_range_steps_not_equal(self):
        a = Nargs(range(1, 2, 3))
        b = Nargs(range(1, 3))
        c = Nargs(1)
        self.assertNotEqual(a, b)
        self.assertNotEqual(b, a)
        self.assertNotEqual(a, c)
        self.assertNotEqual(b, c)
        self.assertNotEqual(c, b)
        self.assertNotEqual(c, a)

    def test_set_str(self):
        nargs = Nargs({5, 9, 2})
        self.assertIn('{2,5,9}', str(nargs))

    def test_range_set_compare(self):
        a = Nargs({0, 1, 2, 3})
        b = Nargs(range(4))
        self.assertEqual(a, b)
        self.assertEqual(b, a)

        c = Nargs(range(5))
        self.assertNotEqual(a, c)
        self.assertNotEqual(b, c)
        self.assertNotEqual(c, a)
        self.assertNotEqual(c, b)

    # endregion


if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    try:
        main(verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
