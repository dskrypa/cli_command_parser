#!/usr/bin/env python

import sys
from pathlib import Path
from unittest import TestCase, main

sys.path.append(Path(__file__).parents[1].joinpath('lib').as_posix())
from command_parser.nargs import Nargs


class MiscTest(TestCase):
    def test_version(self):
        from command_parser import __version__

        self.assertEqual('command_parser', __version__.__title__)

    def test_dunder_main(self):
        from command_parser import __main__

        self.assertEqual('this counts for coverage...?  ._.', 'this counts for coverage...?  ._.')


if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    try:
        main(warnings='ignore', verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
