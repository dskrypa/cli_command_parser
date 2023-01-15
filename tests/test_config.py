#!/usr/bin/env python

from itertools import product, starmap
from operator import or_
from unittest import TestCase, main

from cli_command_parser.config import CommandConfig, ShowDefaults, ConfigItem, DEFAULT_CONFIG


class ConfigTest(TestCase):
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
        config.show_defaults = 'never'
        self.assertIs(ShowDefaults.NEVER, config.show_defaults)

    def test_config_item_self(self):
        self.assertIsInstance(CommandConfig.show_defaults, ConfigItem)

    def test_config_item_repr(self):
        self.assertEqual("<ConfigItem(True, type=<class 'bool'>)>", repr(CommandConfig.add_help))

    def test_config_no_overrides_empty(self):
        self.assertDictEqual({}, CommandConfig().as_dict(False))

    def test_config_item_del(self):
        config = CommandConfig(add_help=False)
        self.assertDictEqual({'add_help': False}, config.as_dict(False))
        del config.add_help
        self.assertDictEqual({}, config.as_dict(False))
        with self.assertRaises(AttributeError):
            del config.add_help

    def test_config_item_default(self):
        self.assertTrue(CommandConfig().add_help)

    def test_config_inherited_value(self):
        self.assertFalse(CommandConfig((CommandConfig(add_help=False),)).add_help)

    def test_config_alt_parent_inherited_value(self):
        self.assertFalse(CommandConfig((CommandConfig(add_help=False), CommandConfig())).add_help)
        self.assertFalse(CommandConfig((CommandConfig(), CommandConfig(add_help=False))).add_help)

    def test_config_invalid_key(self):
        with self.assertRaisesRegex(TypeError, 'unsupported options: bar, foo'):
            CommandConfig(foo=1, bar=2)

    def test_ro_set_rejected(self):
        with self.assertRaises(AttributeError):
            DEFAULT_CONFIG.usage_column_width = 50

    def test_ro_del_rejected(self):
        with self.assertRaises(AttributeError):
            del DEFAULT_CONFIG.usage_column_width


if __name__ == '__main__':
    try:
        main(verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
