#!/usr/bin/env python

import logging
from contextlib import redirect_stdout
from io import StringIO
from itertools import count
from unittest import TestCase, main
from unittest.mock import Mock

from command_parser import Command, Action, no_exit_handler, ActionFlag, ParameterGroup
from command_parser.parameters import before_main, after_main, action_flag
from command_parser.exceptions import CommandDefinitionError, ParameterDefinitionError, ParamConflict

log = logging.getLogger(__name__)


class ActionFlagTest(TestCase):
    def test_help_action(self):
        mock = Mock(__name__='bar')

        class Foo(Command, error_handler=no_exit_handler):
            action = Action()
            action.register(mock)

        sio = StringIO()
        with redirect_stdout(sio):
            foo = Foo.parse(['bar', '-h'])
            foo.run()

        self.assertTrue(sio.getvalue().startswith('usage: '))
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
            with ParameterGroup() as group:
                foo = ActionFlag()(Mock())
                bar = ActionFlag()(Mock())

        with self.assertRaisesRegex(CommandDefinitionError, 'different order values'):
            Foo.parse([])

    def test_af_md_group_conflict(self):
        class Foo(Command):
            with ParameterGroup(mutually_dependent=True) as group:
                foo = ActionFlag()(Mock())
                bar = ActionFlag()(Mock())

        with self.assertRaisesRegex(CommandDefinitionError, 'different order values'):
            Foo.parse([])

    def test_af_me_group_ok(self):
        class Foo(Command):
            with ParameterGroup(mutually_exclusive=True) as group:
                foo = ActionFlag()(Mock())
                bar = ActionFlag()(Mock())

        foo = Foo.parse([])
        with self.assertRaises(KeyError):
            self.assertFalse(foo.args['foo'])
        with self.assertRaises(KeyError):
            self.assertFalse(foo.args['bar'])

    def test_af_mixed_grouping_rejected(self):
        class Foo(Command):
            with ParameterGroup(mutually_exclusive=True) as group:
                foo = ActionFlag()(Mock())
                bar = ActionFlag()(Mock())
            baz = ActionFlag()(Mock())

        with self.assertRaisesRegex(CommandDefinitionError, 'different order values'):
            Foo.parser  # noqa

    def test_af_mixed_grouping_ordered_ok(self):
        attrs = ('foo', 'bar', 'baz')
        for i, attr in enumerate(attrs):
            with self.subTest(attr=attr):
                mocks = [Mock(), Mock(), Mock()]

                class Foo(Command):
                    with ParameterGroup(mutually_exclusive=True) as group:
                        foo = ActionFlag()(mocks[0])
                        bar = ActionFlag()(mocks[1])
                    baz = ActionFlag(order=2)(mocks[2])

                foo = Foo.parse([f'--{attr}'])
                foo.run()
                self.assertTrue(mocks[i].called)
                for j in {0, 1, 2} - {i}:
                    self.assertFalse(mocks[j].called)

                self.assertTrue(foo.args[attr])
                for a in set(attrs) - {attr}:
                    with self.assertRaises(KeyError):
                        foo.args[a]  # noqa

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
            Foo.parser  # noqa

    def test_extra_flags_provided_cause_error(self):
        mocks = [Mock(), Mock()]

        class Foo(Command, error_handler=None):
            foo = ActionFlag('-f', order=1)(mocks[0])
            bar = ActionFlag('-b', order=2)(mocks[1])

        expected_error_text = r'--foo / -f, --bar / -b \(combining multiple action flags is disabled\)'
        with self.assertRaisesRegex(ParamConflict, expected_error_text):
            Foo.parse_and_run(['-fb'])

        with self.assertRaisesRegex(ParamConflict, expected_error_text):
            Foo.parse_and_run(['--foo', '--bar'])

    def test_multi_flag_order_followed(self):
        class Foo(Command, multiple_action_flags=True):
            def __init__(self, args):
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
            def __init__(self, args):
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
                self.assertEqual(2, foo.args.actions_taken)  # 2 because no non-flag Actions

        with self.subTest(case='only after'):
            foo = Foo.parse_and_run(['-b'])
            self.assertNotIn('foo', foo.call_order)
            self.assertLess(foo.call_order['main'], foo.call_order['bar'])
            self.assertEqual(1, foo.args.actions_taken)  # 1 because no non-flag Actions

        with self.subTest(case='only before'):
            foo = Foo.parse_and_run(['-f'])
            self.assertLess(foo.call_order['foo'], foo.call_order['main'])
            self.assertNotIn('bar', foo.call_order)
            self.assertEqual(1, foo.args.actions_taken)  # 1 because no non-flag Actions


if __name__ == '__main__':
    try:
        main(warnings='ignore', verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()