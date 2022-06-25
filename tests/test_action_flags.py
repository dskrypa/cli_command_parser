#!/usr/bin/env python

from itertools import count
from unittest import main
from unittest.mock import Mock

from cli_command_parser import Command, Action, no_exit_handler, ActionFlag, ParamGroup
from cli_command_parser.actions import help_action
from cli_command_parser.context import Context
from cli_command_parser.parameters import before_main, after_main, action_flag
from cli_command_parser.exceptions import CommandDefinitionError, ParameterDefinitionError, ParamConflict
from cli_command_parser.testing import ParserTest, RedirectStreams


class ActionFlagTest(ParserTest):
    def test_help_action(self):
        mock = Mock(__name__='bar')

        class Foo(Command, error_handler=no_exit_handler):
            action = Action()
            action.register(mock)

        with RedirectStreams() as streams:
            Foo.parse(['bar', '-h'])()

        self.assertTrue(streams.stdout.startswith('usage: '))
        self.assertEqual(mock.call_count, 0)

    def test_af_func_missing(self):
        class Foo(Command):
            foo = ActionFlag()

        with self.assertRaisesRegex(ParameterDefinitionError, 'No function was registered'):
            Foo.parse([])

    def test_af_order_conflict(self):
        class Foo(Command):
            foo = ActionFlag()(Mock())
            bar = ActionFlag()(Mock())

        with self.assertRaisesRegex(CommandDefinitionError, 'different order values'):
            Foo.parse([])

    def test_af_non_me_group_conflict(self):
        class Foo(Command):
            with ParamGroup() as group:
                foo = ActionFlag()(Mock())
                bar = ActionFlag()(Mock())

        with self.assertRaisesRegex(CommandDefinitionError, 'different order values'):
            Foo.parse([])

    def test_af_md_group_conflict(self):
        class Foo(Command):
            with ParamGroup(mutually_dependent=True) as group:
                foo = ActionFlag()(Mock())
                bar = ActionFlag()(Mock())

        with self.assertRaisesRegex(CommandDefinitionError, 'different order values'):
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

        with self.assertRaisesRegex(CommandDefinitionError, 'different order values'):
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
        with self.assertRaises(CommandDefinitionError):

            class Foo(Command):
                foo = ActionFlag()(Mock())

                @foo
                def bar(self):
                    pass

    def test_short_option_conflict_rejected(self):
        class Foo(Command):
            bar = ActionFlag('-b', order=1)(Mock())
            baz = ActionFlag('-b', order=2)(Mock())

        with self.assertRaises(CommandDefinitionError):
            Foo.parse([])

    def test_extra_flags_provided_cause_error(self):
        mocks = [Mock(), Mock()]

        class Foo(Command, error_handler=None, multiple_action_flags=False):
            foo = ActionFlag('-f', order=1)(mocks[0])
            bar = ActionFlag('-b', order=2)(mocks[1])

        expected_error_text = r'--foo / -f, --bar / -b \(combining multiple action flags is disabled\)'
        with self.assertRaisesRegex(ParamConflict, expected_error_text):
            Foo.parse_and_run(['-fb'])

        with self.assertRaisesRegex(ParamConflict, expected_error_text):
            Foo.parse_and_run(['--foo', '--bar'])

    def test_multi_flag_order_followed(self):
        class Foo(Command, multiple_action_flags=True):
            def __init__(self):
                self.call_order = {}
                self.counter = count()

            @action_flag('-f', order=1)
            def foo(self):
                self.call_order['foo'] = next(self.counter)

            @action_flag('-b', order=2)
            def bar(self):
                self.call_order['bar'] = next(self.counter)

        for case, args in {'combined': ['-fb'], 'split': ['-b', '-f']}.items():
            with self.subTest(case=case):
                foo = Foo.parse_and_run(args)
                self.assertLess(foo.call_order['foo'], foo.call_order['bar'])

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

    def test_no_result(self):
        mock = Mock()

        class Foo(Command):
            @action_flag('-b')
            def bar(self):
                mock()

        foo = Foo.parse(['-b'])
        self.assertIsInstance(Foo.bar, ActionFlag)
        with foo.ctx:
            self.assertFalse(Foo.bar.result()(foo))

    def test_no_func(self):
        flag = ActionFlag()
        with Context() as ctx:
            flag.store_const()
            with self.assertRaises(ParameterDefinitionError):
                flag.result()

    def test_not_provided(self):
        flag = ActionFlag()
        with Context() as ctx:
            self.assertFalse(flag.result())

    def test_before_main_sorts_before_after_main(self):
        a, b = ActionFlag(before_main=False), ActionFlag(before_main=True)
        expected = [b, a]
        self.assertListEqual(expected, sorted([a, b]))

    def test_after_main_always_available(self):
        with self.assertRaisesRegex(ParameterDefinitionError, 'cannot be combined with'):
            ActionFlag(before_main=False, always_available=True)

    def test_nargs_not_allowed(self):
        with self.assertRaises(TypeError):
            ActionFlag(nargs='+')

    def test_type_not_allowed(self):
        with self.assertRaises(TypeError):
            ActionFlag(type=int)

    def test_choices_not_allowed(self):
        with self.assertRaises(TypeError):
            ActionFlag(choices=(1, 2))


if __name__ == '__main__':
    try:
        main(verbosity=2)
    except KeyboardInterrupt:
        print()
