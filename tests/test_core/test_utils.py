#!/usr/bin/env python

from unittest import main
from unittest.mock import patch

from cli_command_parser.utils import camel_to_snake_case, Terminal, short_repr, FixedFlag
from cli_command_parser.formatting.utils import _description_start_line, _normalize_column_width, _single_line_strs
from cli_command_parser.formatting.utils import combine_and_wrap
from cli_command_parser.testing import ParserTest


class UtilsTest(ParserTest):
    def test_camel_to_snake(self):
        self.assertEqual('foo_bar', camel_to_snake_case('FooBar'))
        self.assertEqual('foo bar', camel_to_snake_case('FooBar', ' '))
        self.assertEqual('foo', camel_to_snake_case('Foo'))

    def test_terminal_width_refresh(self):
        with patch('cli_command_parser.utils.get_terminal_size', return_value=(123, 1)):
            term = Terminal(0.01)
            self.assertEqual(123, term.width)

    def test_descr_start_middle(self):
        usage = ['a' * 10, 'a' * 15, 'a' * 5]
        self.assertEqual(2, _description_start_line(usage, 5))

    def test_descr_start_no_usage(self):
        self.assertEqual(0, _description_start_line((), -5))

    def test_normalize_column_uneven(self):
        result = _normalize_column_width(('a' * 10, 'b' * 3), 5)
        self.assertListEqual(['aaaaa', 'aaaaa', 'bbb'], result)  # noqa

    def test_single_line_strs_split(self):
        self.assertListEqual(['a', 'b'], _single_line_strs('a\nb'))
        self.assertListEqual(['a', 'b'], _single_line_strs(['a\nb']))
        self.assertListEqual(['a', 'b'], _single_line_strs(['a', 'b']))
        self.assertListEqual(['a', 'b', 'c'], _single_line_strs(['a', 'b\nc']))

    def test_short_repr(self):
        for case in (20, 97, 98):
            with self.subTest(len=case):
                text = 'x' * case
                self.assertEqual(repr(text), short_repr(text))

        expected = repr('x' * 47 + '...' + 'x' * 47)
        for case in (99, 200):
            with self.subTest(len=case):
                self.assertEqual(expected, short_repr('x' * case))

    def test_combine_and_wrap(self):
        parts = [f'--{chr(c) * 3}' for c in range(97, 123)]  # --aaa ~ --zzz
        expected_43_5 = """
--aaa, --bbb, --ccc, --ddd, --eee, --fff,
     --ggg, --hhh, --iii, --jjj, --kkk,
     --lll, --mmm, --nnn, --ooo, --ppp,
     --qqq, --rrr, --sss, --ttt, --uuu,
     --vvv, --www, --xxx, --yyy, --zzz
        """
        expected_40_5 = """
--aaa, --bbb, --ccc, --ddd, --eee,
     --fff, --ggg, --hhh, --iii, --jjj,
     --kkk, --lll, --mmm, --nnn, --ooo,
     --ppp, --qqq, --rrr, --sss, --ttt,
     --uuu, --vvv, --www, --xxx, --yyy,
     --zzz
        """
        expected_80 = """
--aaa, --bbb, --ccc, --ddd, --eee, --fff, --ggg, --hhh, --iii, --jjj, --kkk,
--lll, --mmm, --nnn, --ooo, --ppp, --qqq, --rrr, --sss, --ttt, --uuu, --vvv,
--www, --xxx, --yyy, --zzz
        """
        expected_full = """
--aaa, --bbb, --ccc, --ddd, --eee, --fff, --ggg, --hhh, --iii, --jjj, --kkk, --lll, --mmm, --nnn, --ooo, --ppp, --qqq, --rrr, --sss, --ttt, --uuu, --vvv, --www, --xxx, --yyy, --zzz
        """
        cases = [(43, 5, expected_43_5), (40, 5, expected_40_5), (80, 0, expected_80), (183, 0, expected_full)]
        for width, indent, expected in cases:
            with self.subTest(width=width, indent=indent):
                self.assert_strings_equal(expected.strip(), '\n'.join(combine_and_wrap(parts, width, indent)))

    def test_fixed_flag_no_conform(self):
        # This test is purely for coverage in 3.11 where this would always be set
        with patch('cli_command_parser.utils.CONFORM', None):

            class Foo(FixedFlag):
                BAR = 1

            with self.assertRaises(TypeError):
                Foo(None)

    def test_fixed_flag_with_conform(self):
        # This test is purely for coverage in Python < 3.11 where this would never be set
        with patch('cli_command_parser.utils.CONFORM', 1), self.assertRaises(TypeError):

            class Foo(FixedFlag):
                def __new__(cls, *args, **kwargs):
                    # This allows the test to pass on 3.11, while the TypeError will be raised due to the boundary
                    # argument being passed in 3.7-3.10
                    raise TypeError

                BAR = 1


if __name__ == '__main__':
    try:
        main(verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
