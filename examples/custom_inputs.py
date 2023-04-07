#!/usr/bin/env python

from cli_command_parser import Command, Option, ParamGroup, main, inputs
from cli_command_parser.inputs import Range, NumRange, File, Path, Json, FileWrapper


class InputsExample(Command):
    path = Option('-p', type=Path(exists=True, type='file'), help='The path to a file')
    in_file = Option('-f', type=File(allow_dash=True, lazy=False), help='The path to a file to read')
    out_file: FileWrapper = Option('-o', type=File(allow_dash=True, mode='w'), help='The path to a file to write')
    json: FileWrapper = Option('-j', type=Json(allow_dash=True), help='The path to a file containing json')

    with ParamGroup(mutually_exclusive=True):
        simple_range = Option('-r', type=Range(50), help='Choose a number in the specified range')
        skip_range = Option('-k', type=range(1, 30, 2), help='Choose a number in the specified range')
        float_range = Option('-F', type=NumRange(float, min=0, max=1), help='Choose a number in the specified range')
        choice_range = Option('-c', choices=range(20), help='Choose a number in the specified range')

    def main(self):
        if self.path:
            self.print(f'You provided path={self.path}')
        if self.in_file:
            self.print(f'Content from the provided file: {self.in_file!r}')
        if self.json:
            data = self.json.read()
            self.print(f'You provided a {type(data).__name__}')
            iter_data = data.items() if isinstance(data, dict) else data if isinstance(data, list) else [data]
            for n, line in enumerate(iter_data):
                self.print(f'[{n}] {line}')

        ranges = (self.simple_range, self.skip_range, self.float_range, self.choice_range)
        num = next((v for v in ranges if v is not None), None)
        if num is not None:
            self.print(f'You chose the number: {num}')

    def print(self, content):
        if self.out_file:
            self.out_file.write(content + '\n')
        else:
            print(content)


if __name__ == '__main__':
    main()
