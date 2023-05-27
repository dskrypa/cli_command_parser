#!/usr/bin/env python

from unittest import main
from unittest.mock import Mock

from cli_command_parser import Command, Context
from cli_command_parser.exceptions import CommandDefinitionError, BadArgument, InvalidChoice, ParameterDefinitionError
from cli_command_parser.parameters.choice_map import SubCommand, Action, Choice
from cli_command_parser.testing import ParserTest


class ChoiceMapTest(ParserTest):
    def test_reassign_choice_rejected(self):
        with self.assertRaisesRegex(CommandDefinitionError, 'Invalid choice=.*- already assigned to Choice'):

            class Foo(Command):
                action = Action()

                @action
                def foo(self):
                    pass

                @action('foo')
                def _foo(self):
                    pass

    def test_bad_choice_append_rejected(self):
        class Foo(Command):
            action = Action()

            @action('foo bar')
            def foo(self):
                pass

        with Context():
            Foo.action.action.add_value('foo')
            with self.assertRaises(InvalidChoice):
                Foo.action.action.add_value('baz')

    def test_missing_action_target(self):
        class Foo(Command):
            action = Action()

        self.assert_parse_fails_cases(Foo, [[], ['foo'], ['-f']], CommandDefinitionError)

    def test_choice_map_too_many(self):
        class Foo(Command):
            action = Action()

            @action
            def foo(self):
                pass

        with Context():
            Foo.action.action.add_value('foo')
            with self.assertRaises(BadArgument):
                Foo.action.validate('bar')

    def test_no_choices_result_forced(self):
        class Foo(Command):
            action = Action()

            @action
            def foo(self):
                pass

        with self.assertRaisesRegex(CommandDefinitionError, 'No choices were registered for Action'):
            foo = Foo.parse([])
            del Foo.action.choices['foo']
            foo.action  # noqa

    def test_unexpected_nargs(self):
        class Foo(Command):
            action = Action()

            @action('foo bar')
            def foo(self):
                pass

        with Context():
            Foo.action.action.add_value('foo')
            with self.assertRaises(BadArgument):
                Foo.action.result()

    def test_unexpected_choice(self):
        class Foo(Command):
            action = Action()

            @action('foo bar')
            def foo(self):
                pass

            @action('foo baz')
            def bar(self):
                pass

        with Context():
            Foo.action.action.add_value('foo bar')
            del Foo.action.choices['foo bar']
            with self.assertRaises(BadArgument):
                Foo.action.result()

    def test_reassign_sub_command_rejected(self):
        class Foo(Command):
            sub = SubCommand()

        Foo.sub.register(Mock(__name__='bar'))
        with self.assertRaisesRegex(CommandDefinitionError, 'Invalid choice=.*with parent=None - already assigned to'):
            Foo.sub.register(Mock(__name__='bar'))

    def test_redundant_sub_cmd_choice_rejected(self):
        class Foo(Command):
            sub = SubCommand()

        with self.assertRaisesRegex(CommandDefinitionError, 'Cannot combine a positional command_or_choice='):
            Foo.sub.register('foo', choice='foo')

    def test_custom_action_choice(self):
        class Foo(Command):
            action = Action()

            @action('foo')
            def bar(self):
                pass

        self.assertIn('foo', Foo.action.choices)

    # region Kwargs Not Allowed

    def test_nargs_not_allowed_sub_cmd(self):
        with self.assertRaises(TypeError):
            SubCommand(nargs='+')

    def test_type_not_allowed_sub_cmd(self):
        with self.assertRaises(TypeError):
            SubCommand(type=int)

    def test_choices_not_allowed_sub_cmd(self):
        with self.assertRaises(TypeError):
            SubCommand(choices=(1, 2))

    def test_allow_leading_dash_not_allowed_sub_cmd(self):
        with self.assertRaises(TypeError):
            SubCommand(allow_leading_dash=True)

    def test_default_not_allowed_sub_cmd(self):
        with self.assertRaises(ParameterDefinitionError):
            SubCommand(default='foo')

    def test_nargs_not_allowed_action(self):
        with self.assertRaises(TypeError):
            Action(nargs='+')

    def test_type_not_allowed_action(self):
        with self.assertRaises(TypeError):
            Action(type=int)

    def test_choices_not_allowed_action(self):
        with self.assertRaises(TypeError):
            Action(choices=(1, 2))

    def test_allow_leading_dash_not_allowed_action(self):
        with self.assertRaises(TypeError):
            Action(allow_leading_dash=True)

    # endregion

    def test_choice_format_help(self):
        choice = Choice('test', help='Example choice')
        self.assertEqual('    test                      Example choice', choice.format_help())

    def test_default_when_missing(self):
        class Foo(Command, add_help=False):
            sub = SubCommand()

        class Bar(Foo):
            pass

        self.assertEqual({'sub': 123}, Foo().ctx.get_parsed(default=123))


if __name__ == '__main__':
    try:
        main(verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
