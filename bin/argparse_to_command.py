#!/usr/bin/env python

from __future__ import annotations

import logging
from pathlib import Path

from cli_command_parser import Command, Counter, Positional, Flag, ParamGroup, SubCommand, main
from cli_command_parser.compat import cached_property
from cli_command_parser.inputs import Path as IPath

log = logging.getLogger(__name__)

arg_parser = 'argparse.ArgumentParser'
cli_cp_cmd = 'cli-command-parser Command'


class ParserConverter(Command, description=f'Tool to convert an {arg_parser} into a {cli_cp_cmd}'):
    action = SubCommand()
    input: Path
    # fmt: off
    smart_for = Flag(
        '--no-smart-for', '-S', default=True, help='Disable "smart" for loop handling, which attempts to dedupe common subparser params'
    )
    # fmt: on
    with ParamGroup('Common'):
        verbose = Counter('-v', help='Increase logging verbosity (can specify multiple times)')
        dry_run = Flag('-D', help='Print the actions that would be taken instead of taking them')

    def _init_command_(self):
        log_fmt = '%(asctime)s %(levelname)s %(name)s %(lineno)d %(message)s' if self.verbose > 1 else '%(message)s'
        logging.basicConfig(level=logging.DEBUG if self.verbose else logging.INFO, format=log_fmt)

    @cached_property
    def script(self):
        from cli_command_parser.conversion import Script

        script = Script(self.input.read_text(), self.smart_for, path=self.input)
        log.debug(f'Found script={script!r}')
        return script


class Convert(ParserConverter):
    input: Path = Positional(type=IPath(type='file', exists=True), help=f'A file containing an {arg_parser}')

    def main(self):
        from cli_command_parser.conversion import convert_script

        print(convert_script(self.script))


class Pprint(ParserConverter):
    input: Path = Positional(type=IPath(type='file', exists=True), help=f'A file containing an {arg_parser}')

    def main(self):
        for parser in self.script.parsers:
            parser.pprint()


if __name__ == '__main__':
    main()