#!/usr/bin/env python

from unittest import main

from cli_command_parser import Command, Counter, Flag
from cli_command_parser.exceptions import NoSuchOption, ParameterDefinitionError, BadArgument
from cli_command_parser.testing import ParserTest


class CounterTest(ParserTest):
    def test_counter_default(self):
        class Foo(Command):
            verbose: int = Counter('-v')

        self.assertEqual(Foo.parse([]).verbose, 0)

    def test_counter_1(self):
        class Foo(Command):
            verbose: int = Counter('-v')

        self.assertEqual(Foo.parse(['-v']).verbose, 1)
        self.assertEqual(Foo.parse(['--verbose']).verbose, 1)
        with self.assertRaises(NoSuchOption):
            Foo.parse(['-verbose'])

    def test_counter_multi(self):
        class Foo(Command):
            verbose: int = Counter('-v')

        for n in range(1, 11):
            with self.subTest(n=n):
                self.assertEqual(Foo.parse(['-{}'.format('v' * n)]).verbose, n)
                self.assertEqual(Foo.parse(['--verbose'] * n).verbose, n)

    def test_counter_num_no_space(self):
        class Foo(Command):
            verbose: int = Counter('-v')

        for n in range(-10, 11):
            with self.subTest(n=n):
                self.assertEqual(Foo.parse([f'-v{n}']).verbose, n)

    def test_counter_num_space(self):
        class Foo(Command):
            verbose: int = Counter('-v')

        for n in range(-10, 11):
            with self.subTest(n=n):
                self.assertEqual(Foo.parse(['-v', str(n)]).verbose, n)
                self.assertEqual(Foo.parse(['--verbose', str(n)]).verbose, n)

    def test_counter_num_eq(self):
        class Foo(Command):
            verbose: int = Counter('-v')

        for n in range(-10, 11):
            with self.subTest(n=n):
                self.assertEqual(Foo.parse([f'-v={n}']).verbose, n)
                self.assertEqual(Foo.parse([f'--verbose={n}']).verbose, n)

    def test_combined_counters(self):
        class Foo(Command):
            foo = Counter('-f')
            bar = Counter('-b')

        cases = {
            '-ffbb': (2, 2),
            '-fbfb': (2, 2),
            '-ffb': (2, 1),
            '-fbf': (2, 1),
            '-fbb': (1, 2),
            '-bfb': (1, 2),
            '-bb': (0, 2),
            '-ff': (2, 0),
            ('-fb', '3'): (1, 3),
        }
        for case, (f, b) in cases.items():
            foo = Foo.parse([case] if isinstance(case, str) else case)
            self.assertEqual(foo.foo, f)
            self.assertEqual(foo.bar, b)

    def test_counter_flag_combo(self):
        class Foo(Command):
            foo = Flag('-f')
            bar = Counter('-b')

        cases = {
            '-ffbb': (True, 2),
            '-fbfb': (True, 2),
            '-ffb': (True, 1),
            '-fbf': (True, 1),
            '-fbb': (True, 2),
            '-bfb': (True, 2),
            '-bb': (False, 2),
            '-ff': (True, 0),
            ('-fb', '3'): (True, 3),
        }
        for case, (f, b) in cases.items():
            foo = Foo.parse([case] if isinstance(case, str) else case)
            self.assertEqual(foo.foo, f)
            self.assertEqual(foo.bar, b)

    def test_bad_default(self):
        with self.assertRaises(ParameterDefinitionError):
            Counter(default=1.5)  # noqa

    def test_prepare_value(self):
        self.assertEqual(1, Counter().prepare_value(None))

    def test_validate(self):
        self.assertTrue(Counter().is_valid_arg('1'))
        self.assertFalse(Counter().is_valid_arg('1.5'))

    # region Unsupported Kwargs

    def test_nargs_not_allowed(self):
        with self.assertRaises(TypeError):
            Counter(nargs='+')

    def test_type_not_allowed(self):
        with self.assertRaises(TypeError):
            Counter(type=int)

    def test_choices_not_allowed(self):
        with self.assertRaises(TypeError):
            Counter(choices=(1, 2))

    def test_allow_leading_dash_not_allowed(self):
        with self.assertRaises(TypeError):
            Counter(allow_leading_dash=True)

    # endregion

    # region Env Var Handling

    def test_env_var(self):
        class Foo(Command):
            bar = Counter('-b', env_var='BAR')

        cases = [
            ([], {}, {'bar': 0}),
            (['-b'], {'BAR': '0'}, {'bar': 1}),
            ([], {'BAR': '0'}, {'bar': 0}),
            ([], {'BAR': '1'}, {'bar': 1}),
            ([], {'BAR': '12'}, {'bar': 12}),
        ]
        self.assert_env_parse_results_cases(Foo, cases)

        with self.env_vars('invalid value', BAR='foo'):
            # TODO: Improve this error so it indicates which env var had a bad value
            with self.assertRaisesRegex(BadArgument, "bad counter value='foo'"):
                Foo.parse([])

    # endregion


if __name__ == '__main__':
    try:
        main(verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
