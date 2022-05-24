#!/usr/bin/env python

from itertools import product, starmap
from operator import or_
from unittest import TestCase, main

from cli_command_parser.config import CommandConfig, ShowDefaults


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


if __name__ == '__main__':
    try:
        main(warnings='ignore', verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
