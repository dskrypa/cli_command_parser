#!/usr/bin/env python

from unittest import main, skip

from cli_command_parser import Command, Positional, SubCommand
from cli_command_parser.exceptions import AmbiguousParseTree
from cli_command_parser.testing import ParserTest


@skip('Implementation is incomplete and not working yet')
class ParseTreeTestOk(ParserTest):
    def test_sub_cmd_choices_overlap_ok(self):
        class Show(Command):
            sub_cmd = SubCommand()

        class ShowFoo(Show, choice='foo'):
            pass

        class ShowFooBar(Show, choice='foo bar'):
            pass

        cases = [(['foo'], ShowFoo), (['foo', 'bar'], ShowFooBar), (['foo bar'], ShowFooBar)]
        for argv, exp_cls in cases:
            with self.subTest(argv=argv, exp_cls=exp_cls):
                self.assertIsInstance(Show.parse(argv), exp_cls)

    def test_sub_cmd_choices_with_inner_pos_overlap_ok(self):
        class Show(Command):
            sub_cmd = SubCommand()

        class ShowFoo(Show, choice='foo'):
            type = Positional(choices=('a', 'b', 'c'))

        class ShowFooBar(Show, choice='foo bar'):
            pass

        cases = [(['foo'], ShowFoo), (['foo', 'bar'], ShowFooBar), (['foo bar'], ShowFooBar)]
        for argv, exp_cls in cases:
            with self.subTest(argv=argv, exp_cls=exp_cls):
                self.assertIsInstance(Show.parse(argv), exp_cls)

    def test_nested_sub_cmd_choices_overlap_ok(self):
        class Show(Command):
            sub_cmd = SubCommand()

        class ShowFoo(Show, choice='foo'):
            type = SubCommand()

        class ShowFooBar(ShowFoo, choice='bar'):
            pass

        class ShowFooBarBaz(Show, choice='foo bar baz'):
            pass

        cases = [
            (['foo'], ShowFoo),
            (['foo', 'bar'], ShowFooBar),
            (['foo bar'], ShowFooBar),
            (['foo', 'bar', 'baz'], ShowFooBarBaz),
            (['foo bar', 'baz'], ShowFooBarBaz),
            (['foo', 'bar baz'], ShowFooBarBaz),
            (['foo bar baz'], ShowFooBarBaz),
        ]
        for argv, exp_cls in cases:
            with self.subTest(argv=argv, exp_cls=exp_cls):
                self.assertIsInstance(Show.parse(argv), exp_cls)

    def test_nested_pos_choices_partial_overlap_ok(self):
        class Base(Command):
            sub_cmd = SubCommand()

        class Show(Base):
            type = Positional(choices=('foo', 'bar'))

        class ShowFooBaz(Base, choice='show foo baz'):
            pass

        success_cases = [
            (['show', 'foo'], {'sub_cmd': 'show', 'type': 'foo'}),
            (['show', 'bar'], {'sub_cmd': 'show', 'type': 'bar'}),
            (['show', 'foo', 'baz'], {'sub_cmd': 'show foo baz'}),
        ]
        self.assert_parse_results_cases(Base, success_cases)


class ParseTreeTestBad(ParserTest):
    def test_overlap_choice_conflict_bad(self):
        class Show(Command):
            sub_cmd = SubCommand()

        class ShowFoo(Show, choice='foo'):
            type = Positional(choices=('bar', 'baz'))

        class ShowFooBar(Show, choice='foo bar'):
            pass

        with self.assertRaisesRegex(AmbiguousParseTree, 'Conflicting targets'):
            Show.parse([])

    def test_overlap_choice_open_bad(self):
        class Show(Command):
            sub_cmd = SubCommand()

        class ShowFoo(Show, choice='foo'):
            type = Positional()

        class ShowFooBar(Show, choice='foo bar'):
            pass

        with self.assertRaisesRegex(AmbiguousParseTree, 'Conflicting choices'):
            Show.parse([])

    def test_overlap_deep_choice_conflict_bad(self):
        class Show(Command):
            sub_cmd = SubCommand()

        class ShowA(Show, choice='a'):
            sub_cmd = SubCommand()

        class ShowAB(ShowA, choice='b'):
            letter = Positional(choices=('c', 'd'))

        class ShowABC(Show, choice='a b c'):
            pass

        with self.assertRaises(AmbiguousParseTree):
            Show.parse([])

    def test_overlap_deep_choice_open_bad(self):
        class Show(Command):
            sub_cmd = SubCommand()

        class ShowA(Show, choice='a'):
            sub_cmd = SubCommand()

        class ShowAB(ShowA, choice='b'):
            letter = Positional()

        class ShowABC(Show, choice='a b c'):
            pass

        with self.assertRaises(AmbiguousParseTree):
            Show.parse([])

    def test_overlap_deep_choice_open_unbound_bad(self):
        class Show(Command):
            sub_cmd = SubCommand()

        class ShowA(Show, choice='a'):
            letters = Positional(nargs='+')

        class ShowABC(Show, choice='a b c'):
            pass

        with self.assertRaises(AmbiguousParseTree):
            Show.parse([])

    def test_overlap_deep_choice_open_bound_bad(self):
        class Show(Command):
            sub_cmd = SubCommand()

        class ShowA(Show, choice='a'):
            letters = Positional(nargs=2)

        class ShowABC(Show, choice='a b c'):
            pass

        with self.assertRaises(AmbiguousParseTree):
            Show.parse([])

    def test_nested_pos_choice_conflict_bad(self):
        class Base(Command):
            sub_cmd = SubCommand()

        class Show(Base):
            type = Positional(choices=('foo', 'foo bar'))

        class ShowFooBar(Base, choice='show foo bar'):
            pass

        with self.assertRaises(AmbiguousParseTree):
            Base.parse([])


if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    try:
        main(verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
