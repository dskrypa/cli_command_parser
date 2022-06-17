#!/usr/bin/env python

import logging
from contextlib import redirect_stderr
from unittest import TestCase, main
from unittest.mock import Mock, PropertyMock

from cli_command_parser import Command, Action, Positional, action_flag
from cli_command_parser.exceptions import (
    ParameterDefinitionError,
    CommandDefinitionError,
    MissingArgument,
    InvalidChoice,
)

log = logging.getLogger(__name__)

# TODO: Test multi-word actions; multi-word actions combined with subcommands (with multiple words)
# TODO: Test space/-/_ switch for multi-word?


class ActionTest(TestCase):
    def test_action_called(self):
        # redundant with the next test, but proves it works with intended usage
        call_count = 0

        class Foo(Command):
            action = Action()

            @action.register
            def bar(self):
                nonlocal call_count
                call_count += 1

        Foo.parse(['bar'])()
        self.assertEqual(call_count, 1)

    def test_action_called_mock(self):
        mock = Mock(__name__='bar')

        class Foo(Command):
            action = Action()
            action.register(mock)

        foo = Foo.parse(['bar'])
        foo()
        self.assertEqual(mock.call_count, 1)
        # self.assertEqual(mock.call_args.args[0], foo)  # 3.8+
        self.assertEqual(mock.call_args[0][0], foo)

    def test_action_wrong(self):
        class Foo(Command):
            action = Action()
            action(Mock(__name__='bar'))

        with self.assertRaises(InvalidChoice):
            Foo.parse(['baz']).main()

    def test_action_missing(self):
        class Foo(Command):
            action = Action()
            action.register(Mock(__name__='bar'))

        with self.assertRaises(MissingArgument):
            Foo.parse([]).main()

    def test_custom_name(self):
        call_count = 0

        class Foo(Command):
            action = Action()

            @action.register('bar-baz')
            def bar(self):
                nonlocal call_count
                call_count += 1

        with self.assertRaises(InvalidChoice):
            Foo.parse(['bar'])()

        Foo.parse(['bar-baz'])()
        self.assertEqual(call_count, 1)

    def test_invalid_names(self):
        for name in ('baz\n', 'a\nb', '\x00', '-baz', '--baz'):
            with self.subTest(name=name), self.assertRaises(ParameterDefinitionError):

                class Foo(Command):
                    action = Action()
                    action(name)(Mock(__name__='bar'))

    def test_positional_allowed_after_action(self):
        class Foo(Command):
            action = Action(help='The action to take')
            text = Positional(nargs='+')
            action(Mock(__name__='foo'))

        foo = Foo.parse(['foo', 'bar'])
        self.assertTrue(foo.ctx.get_parsed()['action'])
        self.assertEqual(foo.text, ['bar'])

    def test_reject_double_choice(self):
        with self.assertRaises(CommandDefinitionError):

            class Foo(Command):
                action = Action()
                action('foo', choice='foo')(Mock(__name__='foo'))

    def test_stacked_action_flag_action_as_action(self):
        BuildDocs, build_mock, clean_mock = make_build_docs_command()
        BuildDocs.parse_and_run(['clean'])
        self.assertFalse(build_mock.called)
        self.assertTrue(clean_mock.called)

    def test_stacked_action_flag_action_as_flag(self):
        for option in ('-c', '--clean'):
            BuildDocs, build_mock, clean_mock = make_build_docs_command()
            BuildDocs.parse_and_run([option])
            self.assertTrue(build_mock.called)
            self.assertTrue(clean_mock.called)

    def test_stacked_action_flag_action_as_both(self):
        for option in ('-c', '--clean'):
            BuildDocs, build_mock, clean_mock = make_build_docs_command()
            BuildDocs.parse_and_run(['clean', option])
            self.assertFalse(build_mock.called)
            self.assertEqual(2, clean_mock.call_count)

    def test_no_action_choice_with_default(self):
        BuildDocs, build_mock, clean_mock = make_build_docs_command()
        BuildDocs.parse_and_run([])
        self.assertTrue(build_mock.called)
        self.assertFalse(clean_mock.called)

    def test_invalid_action_choice_with_default(self):
        BuildDocs, build_mock, clean_mock = make_build_docs_command()
        with redirect_stderr(Mock()), self.assertRaises(SystemExit):
            BuildDocs.parse_and_run(['foo'])

        self.assertFalse(build_mock.called)
        self.assertFalse(clean_mock.called)

    def test_explicit_choice_of_default(self):
        BuildDocs, build_mock, clean_mock = make_build_docs_command(True)
        BuildDocs.parse_and_run(['build'])
        self.assertTrue(build_mock.called)
        self.assertFalse(clean_mock.called)

    def test_no_action_choice_with_explicit_default(self):
        BuildDocs, build_mock, clean_mock = make_build_docs_command(True)
        BuildDocs.parse_and_run([])
        self.assertTrue(build_mock.called)
        self.assertFalse(clean_mock.called)

    def test_action_flags_called_with_explicit_default(self):
        for option in ('-c', '--clean'):
            BuildDocs, build_mock, clean_mock = make_build_docs_command(True)
            BuildDocs.parse_and_run(['build', option])
            self.assertTrue(build_mock.called)
            self.assertTrue(clean_mock.called)

    def test_default_default_help_text(self):
        class Foo(Command):
            action = Action()
            action(default=True)(Mock(__name__='main', __doc__=None))

        self.assertEqual('Default action if no other action is specified', Foo.action.choices[None].help)

    def test_default_doc_help_text(self):
        class Foo(Command):
            action = Action()
            action(default=True)(Mock(__name__='main', __doc__='test'))

        self.assertEqual('test', Foo.action.choices[None].help)

    def test_doc_help_text(self):
        class Foo(Command):
            action = Action()
            action(Mock(__name__='main', __doc__='test'))

        self.assertEqual('test', Foo.action.choices['main'].help)

    def test_multiple_defaults_rejected(self):
        with self.assertRaisesRegex(CommandDefinitionError, 'Invalid default.*already assigned to'):

            class Foo(Command):
                action = Action()
                action(default=True)(Mock())
                action(default=True)(Mock())

    def test_no_doc_attr_help(self):
        class NoDoc:
            __doc__ = PropertyMock(side_effect=AttributeError)  # This didn't work as a Mock param/attr

            def __init__(self, name):
                self.__name__ = name

        class Foo(Command):
            action = Action()
            action(NoDoc('foo'))  # noqa
            bar = action_flag(func=NoDoc('bar'))  # noqa

        self.assertIs(None, Foo.action.choices['foo'].help)
        self.assertIs(None, Foo.bar.help)


def make_build_docs_command(explicit_build: bool = False):
    build_mock, clean_mock = Mock(__name__='sphinx_build'), Mock()

    class BuildDocs(Command, description='Build documentation using Sphinx'):
        action = Action()
        if explicit_build:
            action('build', default=True, help='Run sphinx-build')(build_mock)
        else:
            action(default=True, help='Run sphinx-build')(build_mock)

        @action_flag('-c', help='Clean the docs directory before building docs', order=1)
        @action(help='Clean the docs directory')
        def clean(self):
            clean_mock()

    return BuildDocs, build_mock, clean_mock


if __name__ == '__main__':
    try:
        main(warnings='ignore', verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
