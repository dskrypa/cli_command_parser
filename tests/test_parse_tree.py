#!/usr/bin/env python

import sys
from unittest import main, skip
from unittest.mock import patch

from cli_command_parser import Command, Positional, SubCommand, AmbiguousParseTree
from cli_command_parser.core import get_config
from cli_command_parser.nargs import Nargs
from cli_command_parser.parse_tree import PosNode, AnyWord
from cli_command_parser.testing import ParserTest, RedirectStreams


@patch('cli_command_parser.config.CommandConfig.reject_ambiguous_pos_combos.default', True)
class TestPosNode(ParserTest):
    def test_get_link_params(self):
        class Foo(Command):
            foo = Positional()
            bar = Positional()

        node = PosNode.build_tree(Foo)
        self.assertEqual({Foo.foo}, node.link_params())
        self.assertEqual({Foo.foo, Foo.bar}, node.link_params(True))

    # region Nargs Tests

    def test_nargs_min_max_unbound(self):
        class Foo(Command):
            foo = Positional(nargs=2)
            bar = Positional(nargs='+')

        node = PosNode.build_tree(Foo)
        self.assertEqual(3, node.nargs_min())
        self.assertEqual(float('inf'), node.nargs_max())

    def test_nargs_variable_then_fixed(self):
        # Note: Positionals accepting any value with variable nargs can't be followed by ones with a fixed # of args
        class Foo(Command):
            foo = Positional(nargs=range(1, 5), choices=('a', 'b'))
            bar = Positional()

        node = PosNode.build_tree(Foo)
        self.assertEqual(2, node.nargs_min())
        self.assertEqual(5, node.nargs_max())

    @skip('This case needs to be handled')
    def test_nargs_pair_extreme(self):
        class Foo(Command):
            foo = Positional(nargs=sys.maxsize)
            bar = Positional(nargs='+')

        node = PosNode.build_tree(Foo)
        self.assertEqual(sys.maxsize, node.nargs_min())
        self.assertEqual(float('inf'), node.nargs_max())

    def test_nargs_min_max_bound(self):
        class Foo(Command):
            foo = Positional(choices=('a', 'b'))
            bar = Positional()

        node = PosNode.build_tree(Foo)
        self.assertEqual(2, node.nargs_min())
        self.assertEqual(2, node.nargs_max())

    # endregion

    def test_repr(self):
        class Foo(Command):
            sub_cmd = SubCommand()

        class Bar(Foo):
            baz = Positional()

        self.assertNotIn('param=target=', repr(PosNode.build_tree(Foo)['bar']))
        self.assertIn('param=target=', repr(PosNode.build_tree(Bar)['a']))

    def test_equality(self):
        class Foo(Command):
            bar = Positional()

        class Bar(Foo):
            baz = Positional()

        foo = PosNode.build_tree(Foo)
        bar = PosNode.build_tree(Bar)
        self.assertNotEqual(foo, bar)
        self.assertEqual(foo, foo)

    def test_bool(self):
        class Foo(Command):
            bar = Positional(choices=('a', 'b'))

        node = PosNode.build_tree(Foo)
        self.assertTrue(node)
        self.assertFalse(node['a'])

    def test_contains(self):
        class Foo(Command):
            bar = Positional(choices=('a', 'b'))
            baz = Positional(nargs='+')

        root = PosNode.build_tree(Foo)
        self.assertIn('a', root)
        self.assertNotIn('c', root)
        node = root['a']
        self.assertNotIn('a', node)
        self.assertIn(node.any_word, node)
        self.assertNotIn(node.any_word + 1, node)

    def test_invalid_any_word(self):
        class Foo(Command):
            bar = Positional(nargs='+')

        root = PosNode.build_tree(Foo)
        with self.assertRaisesRegex(KeyError, r'=>.*? cannot replace') as ctx:
            root['a'][AnyWord(Nargs(1))] = root
        self.assertEqual(1, str(ctx.exception).count('=>'))
        with self.assertRaisesRegex(KeyError, r'=>.*? cannot replace') as ctx:
            root[AnyWord(Nargs(1))] = root
        self.assertEqual(2, str(ctx.exception).count('=>'))

    def test_delete_key(self):
        class Foo(Command):
            bar = Positional(choices=('a', 'b'))
            baz = Positional(nargs='+')

        root = PosNode.build_tree(Foo)
        self.assertIn('a', root)
        del root['a']
        self.assertNotIn('a', root)

        node = root['b']
        with self.assertRaises(KeyError):
            del node['a']
        with self.assertRaises(KeyError):
            del node[AnyWord(Nargs(1))]

        word = node.any_word
        self.assertIn(word, node)
        del node[word]
        self.assertNotIn(word, node)
        with self.assertRaises(KeyError):
            del node[word]

    def test_print_tree(self):
        class Foo(Command):
            bar = Positional(choices=('a', 'b'))
            baz = Positional(nargs='+')

        with RedirectStreams() as streams:
            PosNode.build_tree(Foo).print_tree()

        expected = """
- <PosNode[None, links: 2, target=Foo]>
  - <PosNode['a', links: 1, target=Positional('bar', action='store', type=<Choices[case_sensitive=True, choices=('a','b')]>, required=True)]>
    - <PosNode[AnyWord(Nargs('+'), remaining=inf, n=1), links: 1, target=Positional('baz', action='append', required=True)]>
  - <PosNode['b', links: 1, target=Positional('bar', action='store', type=<Choices[case_sensitive=True, choices=('a','b')]>, required=True)]>
    - <PosNode[AnyWord(Nargs('+'), remaining=inf, n=1), links: 1, target=Positional('baz', action='append', required=True)]>
        """.strip()
        self.assert_strings_equal(expected, streams.stdout.strip())

    def test_intentional_bad_addition(self):
        class Foo(Command):
            bar = Positional(nargs='+')

        node = PosNode.build_tree(Foo)
        with self.assertRaises(AmbiguousParseTree):
            node._update_any(AnyWord(Nargs('+')), Foo.bar, None)


@patch('cli_command_parser.config.CommandConfig.reject_ambiguous_pos_combos.default', True)
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

    @skip('Implementation is incomplete and not working yet')
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

    @skip('Implementation is incomplete and not working yet')
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

    @skip('Implementation is incomplete and not working yet')
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


@patch('cli_command_parser.config.CommandConfig.reject_ambiguous_pos_combos.default', True)
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

        get_config(Show).reject_ambiguous_pos_combos = False
        self.assertEqual('baz', Show.parse(['foo', 'baz']).type)

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
