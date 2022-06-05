#!/usr/bin/env python

from cli_command_parser import Command, Option, main, inputs as i


class InputsExample(Command):
    path = Option('-p', type=i.Path(exists=True, type='file'), help='The path to a file')
    in_file = Option('-f', type=i.File(allow_dash=True, lazy=False), help='The path to a file to read')
    out_file: i.FileWrapper = Option('-o', type=i.File(allow_dash=True, mode='w'), help='The path to a file to write')
    json: i.FileWrapper = Option('-j', type=i.Json(allow_dash=True), help='The path to a file containing json')

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

    def print(self, content):
        if self.out_file:
            self.out_file.write(content + '\n')
        else:
            print(content)


if __name__ == '__main__':
    main()
