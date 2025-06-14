#!/usr/bin/env python

import pickle
from itertools import count
from unittest import main
from unittest.mock import Mock, seal

from cli_command_parser import Action, ActionFlag, Command, ParamGroup, no_exit_handler
from cli_command_parser.exceptions import CommandDefinitionError, ParamConflict, ParameterDefinitionError
from cli_command_parser.parameters import action_flag, after_main, before_main, help_action
from cli_command_parser.testing import ParserTest, RedirectStreams


class ActionFlagTest(ParserTest):
    def test_help_action(self):
        mock = Mock(__name__='bar')
        seal(mock)

        class Foo(Command, error_handler=no_exit_handler):
            action = Action()
            action.register(mock)

        with RedirectStreams() as streams:
            Foo.parse(['bar', '-h'])()

        self.assertTrue(streams.stdout.startswith('usage: '))
        mock.assert_not_called()

    def test_af_func_missing(self):
        class Foo(Command):
            foo = ActionFlag()

        with self.assert_raises_contains_str(ParameterDefinitionError, 'No function was registered'):
            Foo.parse([])

    def test_af_order_conflict(self):
        class Foo(Command):
            foo = ActionFlag()(Mock())
            bar = ActionFlag()(Mock())

        with self.assert_raises_contains_str(CommandDefinitionError, 'different order values'):
            Foo.parse([])

    def test_af_non_me_group_conflict(self):
        class Foo(Command):
            with ParamGroup() as group:
                foo = ActionFlag()(Mock())
                bar = ActionFlag()(Mock())

        with self.assert_raises_contains_str(CommandDefinitionError, 'different order values'):
            Foo.parse([])

    def test_af_md_group_conflict(self):
        class Foo(Command):
            with ParamGroup(mutually_dependent=True) as group:
                foo = ActionFlag()(Mock())
                bar = ActionFlag()(Mock())

        with self.assert_raises_contains_str(CommandDefinitionError, 'different order values'):
            Foo.parse([])

    def test_af_me_group_ok(self):
        class Foo(Command):
            with ParamGroup(mutually_exclusive=True) as group:
                foo = ActionFlag()(Mock())
                bar = ActionFlag()(Mock())

        self.assert_parse_results(Foo, [], {'foo': False, 'bar': False})

    def test_af_mixed_grouping_rejected(self):
        class Foo(Command):
            with ParamGroup(mutually_exclusive=True) as group:
                foo = ActionFlag()(Mock())
                bar = ActionFlag()(Mock())
            baz = ActionFlag()(Mock())

        with self.assert_raises_contains_str(CommandDefinitionError, 'different order values'):
            Foo.parse([])

    def test_af_mixed_grouping_ordered_ok(self):
        attrs = ('foo', 'bar', 'baz')
        for i, attr in enumerate(attrs):
            with self.subTest(attr=attr):
                mocks = [Mock(), Mock(), Mock()]

                class Foo(Command):
                    with ParamGroup(mutually_exclusive=True) as group:
                        foo = ActionFlag()(mocks[0])
                        bar = ActionFlag()(mocks[1])
                    baz = ActionFlag(order=2)(mocks[2])

                foo = Foo.parse([f'--{attr}'])
                foo()
                self.assertTrue(mocks[i].called)
                for j in {0, 1, 2} - {i}:
                    self.assertFalse(mocks[j].called)

                parsed = foo.ctx.get_parsed()
                self.assertTrue(parsed[attr])
                for a in set(attrs) - {attr}:
                    self.assertFalse(parsed[a])

    def test_no_reassign(self):
        expected = 'Cannot re-assign the func to call for ActionFlag'
        with self.assert_raises_contains_str(CommandDefinitionError, expected):

            class Foo(Command):
                foo = ActionFlag()(Mock())

                @foo
                def bar(self):
                    pass

    def test_short_option_conflict_rejected(self):
        class Foo(Command):
            bar = ActionFlag('-b', order=1)(Mock())
            baz = ActionFlag('-b', order=2)(Mock())

        with self.assert_raises_contains_str(CommandDefinitionError, "short option='-b' conflict for command="):
            Foo.parse([])

    def test_extra_flags_provided_cause_error(self):
        mocks = [Mock(), Mock()]

        class Foo(Command, error_handler=None, multiple_action_flags=False):
            foo = ActionFlag('-f', order=1)(mocks[0])
            bar = ActionFlag('-b', order=2)(mocks[1])

        expected_error_text = '--bar / -b, --foo / -f (combining multiple action flags is disabled)'
        with self.assert_raises_contains_str(ParamConflict, expected_error_text):
            Foo.parse_and_run(['-fb'])

        with self.assert_raises_contains_str(ParamConflict, expected_error_text):
            Foo.parse_and_run(['--foo', '--bar'])

    def test_multi_flag_order_followed(self):
        class Foo(Command, multiple_action_flags=True):
            def __init__(self):
                self.call_order = {}
                self.counter = count()

            @action_flag('-b', order=2)
            def bar(self):
                self.call_order['bar'] = next(self.counter)

            @action_flag('-a', order=1)
            def foo(self):
                self.call_order['foo'] = next(self.counter)

            @action_flag('-c', order=3)
            def baz(self):
                self.call_order['baz'] = next(self.counter)

            def main(self):
                self.call_order['main'] = next(self.counter)

        # fmt: off
        cases = (
            ['-abc'], ['-acb'], ['-cab'], ['-bac'], ['-bca'],
            ['-b', '-a', '-c'], ['-b', '-c', '-a'], ['-a', '-b', '-c'],
        )
        # fmt: on
        for case in cases:
            with self.subTest(case=case):
                order = Foo.parse_and_run(case).call_order
                a, b, c, d = order['foo'], order['bar'], order['baz'], order['main']
                self.assertTrue(a < b < c < d, f'Bad order: {a}, {b}, {c}, {d}')

    def test_before_and_after_flags(self):
        class Foo(Command, multiple_action_flags=True):
            def __init__(self):
                self.call_order = {}
                self.counter = count()

            @before_main('-f', order=1)
            def foo(self):
                self.call_order['foo'] = next(self.counter)

            def main(self):
                super().main()
                self.call_order['main'] = next(self.counter)

            @after_main('-b', order=2)
            def bar(self):
                self.call_order['bar'] = next(self.counter)

        for case, args in {'combined': ['-fb'], 'split': ['-b', '-f']}.items():
            with self.subTest(case=case):
                foo = Foo.parse_and_run(args)
                self.assertLess(foo.call_order['foo'], foo.call_order['main'])
                self.assertLess(foo.call_order['main'], foo.call_order['bar'])
                self.assertEqual(2, foo.ctx.actions_taken)  # 2 because no non-flag Actions

        with self.subTest(case='only after'):
            foo = Foo.parse_and_run(['-b'])
            self.assertNotIn('foo', foo.call_order)
            self.assertLess(foo.call_order['main'], foo.call_order['bar'])
            self.assertEqual(1, foo.ctx.actions_taken)  # 1 because no non-flag Actions

        with self.subTest(case='only before'):
            foo = Foo.parse_and_run(['-f'])
            self.assertLess(foo.call_order['foo'], foo.call_order['main'])
            self.assertNotIn('bar', foo.call_order)
            self.assertEqual(1, foo.ctx.actions_taken)  # 1 because no non-flag Actions

    def test_af_before_and_after_with_action(self):
        class Foo(Command):
            action = Action()

            def __init__(self):
                self.call_order = {}
                self.counter = count()

            @action(default=True)
            def default_action(self):
                self.call_order['default_action'] = next(self.counter)

            @before_main('-f')
            def foo(self):
                self.call_order['foo'] = next(self.counter)

            @after_main('-b')
            def bar(self):
                self.call_order['bar'] = next(self.counter)

        foo = Foo.parse_and_run(['-fb'])
        self.assertLess(foo.call_order['foo'], foo.call_order['default_action'])
        self.assertLess(foo.call_order['default_action'], foo.call_order['bar'])
        self.assertEqual(3, foo.ctx.actions_taken)

    def test_bad_action(self):
        with self.assertRaises(ParameterDefinitionError):

            class Foo(Command):
                action_flag(action='store')(Mock())

    def test_equals(self):
        self.assertEqual(help_action, help_action)
        self.assertNotEqual(help_action, '')

    def test_dunder_get(self):
        mock = Mock()

        class Foo(Command):
            @action_flag('-f')
            def foo(self):
                mock()

        Foo.parse(['-f']).foo()
        self.assertTrue(mock.called)

    def test_no_func(self):
        class Foo(Command):
            bar = ActionFlag()

        with self.assert_raises_contains_str(ParameterDefinitionError, 'No function was registered'):
            Foo.parse(['--bar'])

    def test_before_main_sorts_before_after_main(self):
        a, b = ActionFlag(before_main=False), ActionFlag(before_main=True)
        expected = [b, a]
        self.assertListEqual(expected, sorted([a, b]))

    def test_after_main_always_available(self):
        with self.assert_raises_contains_str(ParameterDefinitionError, 'cannot be combined with'):
            ActionFlag(before_main=False, always_available=True)

    def test_nargs_not_allowed(self):
        with self.assertRaises(TypeError):
            ActionFlag(nargs='+')

    def test_choices_not_allowed(self):
        with self.assertRaises(TypeError):
            ActionFlag(choices=(1, 2))

    def test_always_available_must_come_first(self):
        class Foo(Command):
            foo = before_main(order=1)(Mock(__doc__=''))
            bar = before_main(order=2, always_available=True)(Mock(__doc__=''))

        expected = "invalid parameters: {(True, 2): ActionFlag('bar',"
        with self.assert_raises_contains_str(CommandDefinitionError, expected):
            Foo.parse([])


class ActionFlagPickleTest(ParserTest):
    def test_pickleability_help(self):
        foo = ExampleCommand.parse(['-h'])
        self.assertEqual(foo.test_attr, 0)
        clone = pickle.loads(pickle.dumps(foo))
        self.assertIsNot(foo, clone)
        with self.assertRaises(SystemExit), RedirectStreams() as streams:
            clone()

        self.assertTrue(streams.stdout.startswith('usage: '))

    def test_pickleability_no_args(self):
        foo = ExampleCommand.parse([])
        self.assertEqual(foo.test_attr, 0)
        clone = pickle.loads(pickle.dumps(foo))
        self.assertIsNot(foo, clone)
        clone()
        self.assertEqual(clone.test_attr, 0)

    def test_pickleability_other(self):
        foo = ExampleCommand.parse(['-a'])
        self.assertEqual(foo.test_attr, 0)
        clone = pickle.loads(pickle.dumps(foo))
        self.assertIsNot(foo, clone)
        clone()
        self.assertEqual(clone.test_attr, 1)

    def test_pickleability_no_func(self):
        flag = ActionFlag('--test', '-t', order=1)
        clone = pickle.loads(pickle.dumps(flag))
        self.assertIsNot(flag, clone)


class ExampleCommand(Command):
    # This command needed to be defined here for it to be pickleable - pickle.dumps fails when the class is defined
    # in a test method.

    def __init__(self):
        self.test_attr = 0

    @before_main('-a')
    def action_a(self):
        self.test_attr += 1


if __name__ == '__main__':
    try:
        main(verbosity=2)
    except KeyboardInterrupt:
        print()
