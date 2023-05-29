#!/usr/bin/env python

from itertools import product, starmap
from operator import or_
from unittest import TestCase, main

from cli_command_parser import Command, SubCommand, CommandConfig, ShowDefaults, AllowLeadingDash, OptionNameMode
from cli_command_parser.core import get_config
from cli_command_parser.config import ConfigItem, DEFAULT_CONFIG
from cli_command_parser.testing import ParserTest


class ConfigItemTest(TestCase):
    def test_config_item_self(self):
        self.assertIsInstance(CommandConfig.show_defaults, ConfigItem)

    def test_config_item_repr(self):
        self.assertEqual("<ConfigItem(True, type=<class 'bool'>)>", repr(CommandConfig.add_help))

    def test_config_item_del(self):
        config = CommandConfig(add_help=False)
        self.assertDictEqual({'add_help': False}, config.as_dict(False))
        del config.add_help
        self.assertDictEqual({}, config.as_dict(False))
        with self.assertRaises(AttributeError):
            del config.add_help

    def test_config_item_default(self):
        self.assertTrue(CommandConfig().add_help)

    def test_ro_set_rejected(self):
        with self.assertRaises(AttributeError):
            DEFAULT_CONFIG.usage_column_width = 50  # noqa

    def test_ro_del_rejected(self):
        with self.assertRaises(AttributeError):
            del DEFAULT_CONFIG.usage_column_width

    def test_dynamic_ro_set_rejected(self):
        with self.assertRaises(AttributeError):
            DEFAULT_CONFIG.cmd_alias_mode = 'repeat'  # noqa


class ConfigEnumTest(TestCase):
    # region Show Default

    def test_invalid_show_defaults(self):
        with self.assertRaisesRegex(ValueError, 'Invalid.*- expected one of'):
            ShowDefaults('foo')

    def test_any_show_default_or_never_returns_never(self):
        never = ShowDefaults.NEVER
        for sd in ShowDefaults:
            self.assertIs(never, sd | never)
            self.assertIs(never, never | sd)

        for sd in starmap(or_, product(ShowDefaults, ShowDefaults)):
            self.assertIs(never, sd | never)
            self.assertIs(never, never | sd)

    def test_set_show_default(self):
        config = CommandConfig()
        self.assertIsNot(ShowDefaults.NEVER, config.show_defaults)
        config.show_defaults = 'never'  # noqa
        self.assertIs(ShowDefaults.NEVER, config.show_defaults)

    # endregion

    def test_invalid_allow_leading_dash(self):
        with self.assertRaises(ValueError):
            AllowLeadingDash('foo')
        with self.assertRaises(ValueError):
            AllowLeadingDash(1)

    def test_name_mode_aliases(self):
        cases = {
            'underscore': OptionNameMode.UNDERSCORE,
            'dash': OptionNameMode.DASH,
            'both': OptionNameMode.BOTH,
            'both_dash': OptionNameMode.BOTH_DASH,
            'both_underscore': OptionNameMode.BOTH_UNDERSCORE,
            'none': OptionNameMode.NONE,
            None: OptionNameMode.NONE,
            '-': OptionNameMode.DASH,
            '_': OptionNameMode.UNDERSCORE,
            '*': OptionNameMode.BOTH,
            '-*': OptionNameMode.BOTH_DASH,
            '*-': OptionNameMode.BOTH_DASH,
            '*_': OptionNameMode.BOTH_UNDERSCORE,
            '_*': OptionNameMode.BOTH_UNDERSCORE,
        }
        for alias, expected in cases.items():
            with self.subTest(alias=alias):
                self.assertEqual(expected, OptionNameMode(alias))


class ConfigTest(ParserTest):
    def test_config_no_overrides_empty(self):
        self.assertDictEqual({}, CommandConfig().as_dict(False))

    def test_config_invalid_key(self):
        with self.assert_raises_contains_str(TypeError, 'unsupported options: bar, foo'):
            CommandConfig(foo=1, bar=2)

    # region Inheritance

    def test_config_inherited_value(self):
        self.assertFalse(CommandConfig(CommandConfig(add_help=False)).add_help)

    def test_config_alt_parent_inherited_value(self):
        self.assertFalse(CommandConfig(CommandConfig(CommandConfig(), add_help=False)).add_help)
        self.assertFalse(CommandConfig(CommandConfig(CommandConfig(add_help=False))).add_help)

    def test_config_sub_cmd_inheritance(self):
        class Foo(Command, show_group_tree=True):
            sub = SubCommand()

        class Bar(Foo):
            pass

        self.assertTrue(Foo().ctx.config.show_group_tree)
        self.assertTrue(Bar().ctx.config.show_group_tree)
        self.assertTrue(get_config(Foo).show_group_tree)
        self.assertTrue(get_config(Bar).show_group_tree)

    # endregion

    def test_validate_wrap_usage_str(self):
        with self.assertRaisesRegex(TypeError, 'Invalid value=.*a bool or a positive integer'):
            CommandConfig(wrap_usage_str='foo')
        with self.assertRaisesRegex(ValueError, 'Invalid value=.*a bool or a positive integer'):
            CommandConfig(wrap_usage_str=-1)
        with self.assertRaisesRegex(ValueError, 'Invalid value=.*a bool or a positive integer'):
            CommandConfig(wrap_usage_str=0)

        self.assertEqual(False, CommandConfig().wrap_usage_str)
        self.assertEqual(True, CommandConfig(wrap_usage_str=True).wrap_usage_str)
        self.assertEqual(1, CommandConfig(wrap_usage_str=1).wrap_usage_str)
        self.assertEqual(123, CommandConfig(wrap_usage_str=123).wrap_usage_str)

    def test_validate_sub_cmd_doc_depth(self):
        with self.assertRaisesRegex(TypeError, 'Invalid value=.*a positive integer'):
            CommandConfig(sub_cmd_doc_depth='foo')
        with self.assertRaisesRegex(ValueError, 'Invalid value=.*a positive integer'):
            CommandConfig(sub_cmd_doc_depth=-1)

        self.assertEqual(0, CommandConfig(sub_cmd_doc_depth=0).sub_cmd_doc_depth)
        self.assertEqual(1, CommandConfig(sub_cmd_doc_depth=1).sub_cmd_doc_depth)
        self.assertEqual(123, CommandConfig(sub_cmd_doc_depth=123).sub_cmd_doc_depth)


if __name__ == '__main__':
    try:
        main(verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
