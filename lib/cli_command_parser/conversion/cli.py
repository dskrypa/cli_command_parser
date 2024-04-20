from __future__ import annotations

import logging
from functools import cached_property
from pathlib import Path

from cli_command_parser import Command, Counter, Positional, Flag, ParamGroup, SubCommand, main
from cli_command_parser.inputs import Path as IPath

log = logging.getLogger(__name__)

arg_parser = 'argparse.ArgumentParser'
cli_cp_cmd = 'cli-command-parser Command'


class ParserConverter(Command, description=f'Tool to convert an {arg_parser} into a {cli_cp_cmd}'):
    action = SubCommand()
    input: Path
    no_smart_for = Flag('-S', help='Disable "smart" for loop handling that attempts to dedupe common subparser params')
    with ParamGroup('Common'):
        verbose = Counter('-v', help='Increase logging verbosity (can specify multiple times)')
        dry_run = Flag('-D', help='Print the actions that would be taken instead of taking them')

    def _init_command_(self):
        log_fmt = '%(asctime)s %(levelname)s %(name)s %(lineno)d %(message)s' if self.verbose > 1 else '%(message)s'
        logging.basicConfig(level=logging.DEBUG if self.verbose else logging.INFO, format=log_fmt)

    @cached_property
    def script(self):
        from cli_command_parser.conversion import Script

        script = Script(self.input.read_text(), not self.no_smart_for, path=self.input)
        log.debug(f'Found {script=}')
        return script


class Convert(ParserConverter):
    input: Path = Positional(type=IPath(type='file', exists=True), help=f'A file containing an {arg_parser}')
    add_methods = Flag('--no-methods', '-M', default=True, help='Do not include boilerplate methods in Commands')

    def main(self):
        from cli_command_parser.conversion import convert_script

        print(convert_script(self.script, self.add_methods))


class Pprint(ParserConverter):
    input: Path = Positional(type=IPath(type='file', exists=True), help=f'A file containing an {arg_parser}')

    def main(self):
        for parser in self.script.parsers:
            parser.pprint()


if __name__ == '__main__':
    main()
