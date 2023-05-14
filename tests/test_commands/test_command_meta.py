#!/usr/bin/env python

from unittest import TestCase, main

from cli_command_parser import Command, CommandConfig
from cli_command_parser.core import CommandMeta, get_config, get_parent, get_params, _choice_items
from cli_command_parser.exceptions import CommandDefinitionError

_get_config = CommandMeta.config


class TestCommandMeta(TestCase):
    # region Subcommand Choice Tests

    def test_choice_with_no_sub_cmd_param_warns(self):
        class Foo(Command):
            pass

        cases = [
            ({'choice': 'bar'}, "choice='bar' was not registered.*"),
            ({'choice': 'bar', 'choices': ('bar1',)}, r"choice='bar' and choices=\('bar1',\) were not registered.*"),
            ({'choices': ('bar', 'bar1')}, r"choices=\('bar', 'bar1'\) were not registered.*"),
        ]
        for kwargs, exp_pat_prefix in cases:
            with self.subTest(kwargs=kwargs):
                with self.assertWarnsRegex(Warning, exp_pat_prefix + 'has no SubCommand parameter'):

                    class Bar(Foo, **kwargs):
                        pass

    def test_choice_with_no_parent_warns(self):
        cases = [
            ({'choice': 'foo'}, "choice='foo' was not registered.*"),
            ({'choice': 'foo', 'choices': ('foo1',)}, r"choice='foo' and choices=\('foo1',\) were not registered.*"),
            ({'choices': ('foo', 'foo1')}, r"choices=\('foo', 'foo1'\) were not registered.*"),
        ]
        for kwargs, exp_pat_prefix in cases:
            with self.subTest(kwargs=kwargs):
                with self.assertWarnsRegex(Warning, exp_pat_prefix + 'because it has no parent Command'):

                    class Foo(Command, **kwargs):
                        pass

    def test_no_warn_on_parent_without_choice(self):
        class Foo(Command):
            pass

        class Bar(Foo):
            pass

        self.assertEqual(get_params(Bar).command_parent, Foo)

    def test_choice_items_results(self):
        cases = [
            ((None, None), set()),
            (('a', None), {('a', None)}),
            (('a', ['c', 'b']), {('a', None), ('b', None), ('c', None)}),
            (('a', ['b', 'b']), {('a', None), ('b', None)}),
            (('a', {'a': None, 'b': 'foo'}), {('a', None), ('b', 'foo')}),
            ((None, {'a': None, 'b': 'foo'}), {('a', None), ('b', 'foo')}),
            (('', {'a': None, 'b': 'foo'}), {('a', None), ('b', 'foo')}),
        ]
        for args, expected in cases:
            with self.subTest(args=args, expected=expected):
                self.assertSetEqual(expected, set(_choice_items(*args)))

    # endregion

    # region Config Tests

    def test_double_config_rejected(self):
        with self.assertRaisesRegex(CommandDefinitionError, 'Cannot combine .* with keyword config'):

            class Foo(Command, config=CommandConfig(), multiple_action_flags=True):
                pass

    def test_config_defaults(self):
        class Foo(Command):
            pass

        config = _get_config(Foo)
        self.assertDictEqual(config.as_dict(), CommandConfig().as_dict())

    def test_config_from_kwarg(self):
        default = CommandConfig().multiple_action_flags

        class Foo(Command, multiple_action_flags=not default):
            pass

        self.assertEqual(_get_config(Foo).multiple_action_flags, not default)

    def test_config_from_dict(self):
        default = CommandConfig().multiple_action_flags

        class Foo(Command, config={'multiple_action_flags': not default}):
            pass

        self.assertEqual(_get_config(Foo).multiple_action_flags, not default)

    def test_config_explicit(self):
        default = CommandConfig().multiple_action_flags

        class Foo(Command, config=CommandConfig(multiple_action_flags=not default)):
            pass

        self.assertEqual(_get_config(Foo).multiple_action_flags, not default)

    def test_config_inherited(self):
        default_config = CommandConfig()

        class Foo(Command, multiple_action_flags=not default_config.multiple_action_flags):
            pass

        self.assertEqual(_get_config(Foo).action_after_action_flags, default_config.action_after_action_flags)
        self.assertNotEqual(_get_config(Foo).multiple_action_flags, default_config.multiple_action_flags)

        class Bar(Foo, action_after_action_flags=not default_config.action_after_action_flags):
            pass

        self.assertNotEqual(_get_config(Bar).action_after_action_flags, default_config.action_after_action_flags)
        self.assertNotEqual(_get_config(Bar).multiple_action_flags, default_config.multiple_action_flags)
        # Ensure Foo config has not changed:
        self.assertEqual(_get_config(Foo).action_after_action_flags, default_config.action_after_action_flags)
        self.assertNotEqual(_get_config(Foo).multiple_action_flags, default_config.multiple_action_flags)

    def test_get_config(self):
        cfg = CommandConfig()

        class Foo(Command, config=cfg):
            pass

        self.assertIs(cfg, get_config(Foo))
        self.assertIs(cfg, get_config(Foo()))

    # endregion

    def test_get_parent(self):
        class Foo(Command):
            pass

        self.assertIs(Command, get_parent(Foo))
        self.assertIs(Command, get_parent(Foo()))

    def test_init_subclass_kwargs_allowed(self):
        class Foo(Command):
            def __init_subclass__(cls, test123, **kwargs):  # noqa
                super().__init_subclass__(**kwargs)
                cls.test123 = test123

        class Bar(Foo, test123='test'):
            pass

        self.assertEqual('test', Bar.test123)  # noqa

    def test_extra_kwargs_rejected(self):
        with self.assertRaises(TypeError):

            class Foo(Command, test123='test'):
                pass


if __name__ == '__main__':
    try:
        main(verbosity=2)
    except KeyboardInterrupt:
        print()
