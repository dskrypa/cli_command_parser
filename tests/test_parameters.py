#!/usr/bin/env python

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Collection, Sequence, Iterable, Union
from unittest import TestCase, main
from unittest.mock import Mock

from command_parser import Command, Counter, Option, Flag
from command_parser.exceptions import (
    NoSuchOption,
    UsageError,
    ParameterDefinitionError,
    CommandDefinitionError,
    ParamUsageError,
    MissingArgument,
    BadArgument,
)
from command_parser.parameters import parameter_action, PassThru, Positional
from command_parser.args import Args


class PositionalTest(TestCase):
    def test_extra_positional_deferred(self):
        class Foo(Command):
            bar = Positional()

        with self.assertRaises(NoSuchOption):
            Foo.parse(['bar', 'baz'])

        foo = Foo.parse(['bar', 'baz'], allow_unknown=True)
        self.assertEqual(foo.args.remaining, ['baz'])


class OptionTest(TestCase):
    def test_choice_ok(self):
        class Foo(Command):
            foo = Option('-f', choices=('a', 'b'))

        self.assertEqual(Foo.parse(['-f', 'a']).foo, 'a')
        self.assertEqual(Foo.parse(['-f', 'b']).foo, 'b')
        self.assertEqual(Foo.parse(['--foo', 'a']).foo, 'a')
        self.assertEqual(Foo.parse(['--foo', 'b']).foo, 'b')

    def test_choice_bad(self):
        class Foo(Command):
            foo = Option('-f', choices=('a', 'b'))

        with self.assertRaises(UsageError):
            Foo.parse(['-f', 'c'])

    def test_instance_values(self):
        class Foo(Command):
            foo = Option('-f', choices=('a', 'b'))

        a = Foo.parse(['-f', 'a'])
        b = Foo.parse(['-f', 'b'])
        self.assertEqual(a.foo, 'a')
        self.assertEqual(b.foo, 'b')

    def test_triple_dash_rejected(self):
        class Foo(Command):
            bar = Flag()

        for case in (['---'], ['---bar'], ['--bar', '---'], ['--bar', '---bar']):
            with self.subTest(case=case), self.assertRaises(NoSuchOption):
                Foo.parse(case)

    def test_misc_dash_rejected(self):
        class Foo(Command):
            bar = Flag()

        for case in (['----'], ['----bar'], ['--bar', '----'], ['--bar', '----bar'], ['-'], ['--bar', '-']):
            with self.subTest(case=case), self.assertRaises(NoSuchOption):
                Foo.parse(case)

    def test_extra_long_option_deferred(self):
        class Foo(Command):
            bar = Positional()

        with self.assertRaises(NoSuchOption):
            Foo.parse(['bar', '--baz'])

        foo = Foo.parse(['bar', '--baz'], allow_unknown=True)
        self.assertEqual(foo.args.remaining, ['--baz'])

        with self.assertRaises(NoSuchOption):
            Foo.parse(['bar', '--baz', 'a'])

        foo = Foo.parse(['bar', '--baz', 'a'], allow_unknown=True)
        self.assertEqual(foo.args.remaining, ['--baz', 'a'])

    def test_extra_short_option_deferred(self):
        class Foo(Command):
            bar = Positional()

        with self.assertRaises(NoSuchOption):
            Foo.parse(['bar', '-b'])

        foo = Foo.parse(['bar', '-b'], allow_unknown=True)
        self.assertEqual(foo.args.remaining, ['-b'])

        with self.assertRaises(NoSuchOption):
            Foo.parse(['bar', '-b', 'a'])

        foo = Foo.parse(['bar', '-b', 'a'], allow_unknown=True)
        self.assertEqual(foo.args.remaining, ['-b', 'a'])

        with self.assertRaises(NoSuchOption):
            Foo.parse(['bar', '-b=a'])

        foo = Foo.parse(['bar', '-b=a'], allow_unknown=True)
        self.assertEqual(foo.args.remaining, ['-b=a'])

    def test_value_missing(self):
        class Foo(Command):
            foo = Flag('-f')
            bar = Option()

        cases = (['--foo', '--bar'], ['--bar', '--foo'], ['-f', '--bar'], ['--bar', '-f'])
        for case in cases:
            with self.subTest(case=case), self.assertRaises(MissingArgument):
                Foo.parse(case)

        self.assertTrue(Foo.parse(['--foo']).foo)

    def test_short_value_invalid(self):
        class Foo(Command):
            foo = Flag()
            bar = Option()

        with self.assertRaises(NoSuchOption):
            Foo.parse(['--bar', '-f'])

    def test_invalid_value(self):
        class Foo(Command):
            bar = Option(type=Mock(side_effect=TypeError))

        with self.assertRaises(BadArgument):
            Foo.parse(['--bar', '1'])


class CounterTest(TestCase):
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


class PassThruTest(TestCase):
    def test_pass_thru(self):
        class Foo(Command):
            bar = Flag()
            baz = PassThru()

        foo = Foo.parse(['--bar', '--', 'test', 'one', 'two', 'three'])
        self.assertTrue(foo.bar)
        self.assertEqual(foo.baz, ['test', 'one', 'two', 'three'])

        foo = Foo.parse(['--', '--bar', '--', 'test', 'one', 'two', 'three'])
        self.assertFalse(foo.bar)
        self.assertEqual(foo.baz, ['--bar', '--', 'test', 'one', 'two', 'three'])

        foo = Foo.parse(['--bar', '--'])
        self.assertTrue(foo.bar)
        self.assertEqual(foo.baz, [])

        foo = Foo.parse(['--bar'])
        self.assertTrue(foo.bar)
        self.assertIs(foo.baz, None)

    def test_pass_thru_missing(self):
        class Foo(Command):
            bar = Flag()
            baz = PassThru(required=True)

        with self.assertRaises(MissingArgument):
            Foo.parse([])

    def test_multiple_rejected(self):
        class Foo(Command):
            bar = PassThru()
            baz = PassThru()

        with self.assertRaises(CommandDefinitionError):
            Foo.parser  # noqa

    def test_double_dash_without_pass_thru_rejected(self):
        class Foo(Command):
            bar = Flag()

        with self.assertRaises(NoSuchOption):
            Foo.parse(['--'])

    def test_parser_has_pass_thru(self):
        class Foo(Command):
            pt = PassThru()

        class Bar(Foo):
            pass

        self.assertTrue((Bar.parser.has_pass_thru()))


class MiscParameterTest(TestCase):
    def test_param_knows_command(self):
        class Foo(Command):
            foo = Option('-f', choices=('a', 'b'))

        self.assertIs(Foo.foo.command, Foo)

    def test_unregistered_action_rejected(self):
        with self.assertRaises(ParameterDefinitionError):
            Flag(action='foo')

    def test_empty_choices(self):
        with self.assertRaises(ParameterDefinitionError):
            Option(choices=())

    def test_action_is_parameter_action(self):
        self.assertIsInstance(Flag.store_const, parameter_action)

    def test_re_assign_rejected(self):
        option = Option(action='store')
        args = Args([])
        option.take_action(args, 'foo')
        with self.assertRaises(ParamUsageError):
            option.take_action(args, 'foo')

    def test_too_many_rejected(self):
        option = Option(action='append', nargs=1)
        args = Args([])
        option.take_action(args, 'foo')
        with self.assertRaises(ParamUsageError):
            option.take_action(args, 'foo')

    def test_non_none_rejected(self):
        flag = Flag()
        with self.assertRaises(ParamUsageError):
            flag.take_action(Args([]), 'foo')


class TypeCastTest(TestCase):
    def test_type_cast_single_1(self):
        class Foo(Command):
            num: int = Positional()

        self.assertEqual(5, Foo.parse(['5']).num)

    def test_type_cast_single_2(self):
        class Foo(Command):
            num: Optional[int] = Positional()

        self.assertEqual(5, Foo.parse(['5']).num)

    def test_type_cast_single_3(self):
        class Foo(Command):
            num: Union[int, str] = Positional()

        self.assertEqual('5', Foo.parse(['5']).num)

    def test_type_cast_single_4(self):
        class Foo(Command):
            num: Union[int] = Positional()

        self.assertEqual(5, Foo.parse(['5']).num)

    def test_type_cast_single_5(self):
        class Foo(Command):
            num: Union[int, str, None] = Positional()

        self.assertEqual('5', Foo.parse(['5']).num)

    def test_type_cast_single_6(self):
        class Foo(Command):
            num: _C = Positional()

        self.assertEqual(_C('5'), Foo.parse(['5']).num)

    def test_type_cast_single_7(self):
        class Foo(Command):
            paths: _resolved_path = Positional()  # Not a proper annotation

        self.assertEqual('test_parameters.py', Foo.parse(['test_parameters.py']).paths)

    def test_type_cast_single_8(self):
        class Foo(Command):
            paths: Union[_resolved_path] = Positional()  # Not a proper annotation

        self.assertEqual('test_parameters.py', Foo.parse(['test_parameters.py']).paths)

    def test_type_cast_single_9(self):
        class Foo(Command):
            paths: Optional[_resolved_path] = Positional()  # Not a proper annotation

        self.assertEqual('test_parameters.py', Foo.parse(['test_parameters.py']).paths)

    def test_type_cast_single_10(self):
        class Foo(Command):
            num: Union[str, _C] = Positional()

        self.assertEqual('5', Foo.parse(['5']).num)

    def test_type_cast_multi_1(self):
        class Foo(Command):
            num: list[int] = Positional(nargs='+')

        self.assertListEqual([1, 2], Foo.parse(['1', '2']).num)

    def test_type_cast_multi_2(self):
        for wrapper in (Optional, Union):
            with self.subTest(wrapper=wrapper):

                class Foo(Command):
                    num: list[wrapper[int]] = Positional(nargs='+')

                self.assertListEqual([1, 2], Foo.parse(['1', '2']).num)

    def test_type_cast_multi_3(self):
        class Foo(Command):
            num: Optional[list[int]] = Positional(nargs='+')

        self.assertListEqual([1, 2], Foo.parse(['1', '2']).num)

    def test_type_cast_multi_4(self):
        class Foo(Command):
            num: tuple[int, ...] = Positional(nargs='+')

        self.assertListEqual([1, 2], Foo.parse(['1', '2']).num)

    def test_type_cast_multi_generics(self):
        for generic in (Sequence, Collection, Iterable, Union):
            with self.subTest(generic=generic):

                class Foo(Command):
                    num: generic[int] = Positional(nargs='+')  # noqa

                self.assertListEqual([1, 2], Foo.parse(['1', '2']).num)

    def test_type_cast_multi_5(self):
        class Foo(Command):
            num: list = Positional(nargs='+')

        self.assertListEqual([['1', '2'], ['3']], Foo.parse(['12', '3']).num)

    def test_type_cast_multi_6(self):
        class Foo(Command):
            num: list[Union[int, str, None]] = Positional(nargs='+')

        self.assertListEqual(['12', '3'], Foo.parse(['12', '3']).num)

    def test_type_cast_multi_7(self):
        class Foo(Command):
            num: tuple[int, str, None] = Positional(nargs='+')

        self.assertListEqual(['12', '3'], Foo.parse(['12', '3']).num)

    def test_type_cast_multi_8(self):
        class Foo(Command):
            num: list[_C] = Positional(nargs='+')

        self.assertEqual([_C('1'), _C('2')], Foo.parse(['1', '2']).num)

    def test_type_cast_multi_9(self):
        class Foo(Command):
            paths: list[_resolved_path] = Positional(nargs='+')  # Not a proper annotation

        expected = ['test_parameters.py', 'test_commands.py']
        self.assertEqual(expected, Foo.parse(['test_parameters.py', 'test_commands.py']).paths)


def _resolved_path(path):
    return Path(path).resolve()


@dataclass
class _C:
    x: str


if __name__ == '__main__':
    try:
        main(warnings='ignore', verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
