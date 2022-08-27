#!/usr/bin/env python

from unittest import main
from unittest.mock import Mock

from cli_command_parser import Command
from cli_command_parser.context import Context
from cli_command_parser.exceptions import ParameterDefinitionError, CommandDefinitionError, BadArgument, InvalidChoice
from cli_command_parser.parameters.choice_map import SubCommand, Action
from cli_command_parser.testing import ParserTest


class ChoiceMapTest(ParserTest):
    def test_reassign_choice_rejected(self):
        with self.assertRaises(CommandDefinitionError):

            class Foo(Command):
                action = Action()
                action('foo')(Mock())
                action('foo')(Mock())

    def test_bad_choice_append_rejected(self):
        class Foo(Command):
            action = Action()
            action('foo bar')(Mock())

        with Context():
            Foo.action.take_action('foo')
            with self.assertRaises(InvalidChoice):
                Foo.action.append('baz')

    def test_missing_action_target(self):
        class Foo(Command):
            action = Action()

        self.assert_parse_fails(Foo, [], CommandDefinitionError)

    def test_missing_action_target_forced(self):
        class Foo(Command):
            action = Action()

        with Context():
            with self.assertRaises(BadArgument):
                Foo.action.validate('-foo')
            self.assertIs(None, Foo.action.validate('foo'))

    def test_choice_map_too_many(self):
        class Foo(Command):
            action = Action()
            action('foo')(Mock())

        with Context():
            Foo.action.take_action('foo')
            with self.assertRaises(BadArgument):
                Foo.action.validate('bar')

    def test_no_choices_result_forced(self):
        class Foo(Command):
            action = Action()
            action('foo')(Mock())

        with self.assertRaises(CommandDefinitionError):
            foo = Foo.parse([])
            del Foo.action.choices['foo']
            foo.action  # noqa

    def test_unexpected_nargs(self):
        class Foo(Command):
            action = Action()
            action('foo bar')(Mock())

        with Context():
            Foo.action.take_action('foo')
            with self.assertRaises(BadArgument):
                Foo.action.result()

    def test_unexpected_choice(self):
        class Foo(Command):
            action = Action()
            action('foo bar')(Mock())
            action('foo baz')(Mock())

        with Context():
            Foo.action.take_action('foo bar')
            del Foo.action.choices['foo bar']
            with self.assertRaises(BadArgument):
                Foo.action.result()

    def test_reassign_sub_command_rejected(self):
        class Foo(Command):
            sub = SubCommand()

        Foo.sub.register(Mock(__name__='bar'))
        with self.assertRaises(CommandDefinitionError):
            Foo.sub.register(Mock(__name__='bar'))

    def test_redundant_sub_cmd_choice_rejected(self):
        class Foo(Command):
            sub = SubCommand()

        with self.assertRaises(CommandDefinitionError):
            Foo.sub.register('foo', choice='foo')

    def test_custom_action_choice(self):
        class Foo(Command):
            action = Action()
            action(choice='foo')(Mock(__name__='bar'))

        self.assertIn('foo', Foo.action.choices)

    def test_nargs_not_allowed_sub_cmd(self):
        with self.assertRaises(TypeError):
            SubCommand(nargs='+')

    def test_type_not_allowed_sub_cmd(self):
        with self.assertRaises(TypeError):
            SubCommand(type=int)

    def test_choices_not_allowed_sub_cmd(self):
        with self.assertRaises(ParameterDefinitionError):
            SubCommand(choices=(1, 2))

    def test_nargs_not_allowed_action(self):
        with self.assertRaises(TypeError):
            Action(nargs='+')

    def test_type_not_allowed_action(self):
        with self.assertRaises(TypeError):
            Action(type=int)

    def test_choices_not_allowed_action(self):
        with self.assertRaises(ParameterDefinitionError):
            Action(choices=(1, 2))


if __name__ == '__main__':
    try:
        main(verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
