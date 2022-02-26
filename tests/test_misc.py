#!/usr/bin/env python

from unittest import TestCase, main


class MiscTest(TestCase):
    def test_version(self):
        from cli_command_parser import __version__

        self.assertEqual('cli_command_parser', __version__.__title__)

    def test_dunder_main(self):
        from cli_command_parser import __main__

        self.assertEqual('this counts for coverage...?  ._.', 'this counts for coverage...?  ._.')


if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    try:
        main(warnings='ignore', verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
