#!/usr/bin/env python

import os
import pickle
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import main
from unittest.mock import patch

from cli_command_parser import Command, Positional
from cli_command_parser.inputs import Path as PathInput, File, Deserialized, Json, StatMode
from cli_command_parser.testing import ParserTest


@contextmanager
def temp_chdir(path: Path):
    cwd = Path.cwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(cwd)


@contextmanager
def temp_directory():
    with TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


class InputTest(ParserTest):
    def test_invalid_stat_modes(self):
        with self.assertRaises(TypeError):
            StatMode(None)
        with self.assertRaises(TypeError):
            StatMode('StatMode')

    def test_path_resolve(self):
        with temp_directory() as tmp_path:
            a = tmp_path.joinpath('a')
            a.touch()
            with temp_chdir(tmp_path):
                self.assertEqual(a, PathInput(exists=True, resolve=True, mode='file', expand=False)('a'))

    def test_path_reject_missing(self):
        with temp_directory() as tmp_path:
            a = tmp_path.joinpath('a')
            with self.assertRaises(ValueError):
                PathInput(exists=True)(a.as_posix())

    def test_path_reject_exists(self):
        with temp_directory() as tmp_path:
            a = tmp_path.joinpath('a')
            a.touch()
            with self.assertRaises(ValueError):
                PathInput(exists=False)(a.as_posix())

    def test_path_reject_dir(self):
        with TemporaryDirectory() as tmp_dir:
            with self.assertRaises(ValueError):
                PathInput(mode=StatMode.FILE)(tmp_dir)

    def test_path_reject_file(self):
        with temp_directory() as tmp_path:
            a = tmp_path.joinpath('a')
            a.touch()
            with self.assertRaises(ValueError):
                PathInput(mode=StatMode.DIR)(a.as_posix())

    def test_empty_rejected(self):
        with self.assertRaises(ValueError):
            PathInput()('')

    def test_dash_rejected(self):
        with self.assertRaises(ValueError):
            PathInput()('-')

    def test_dash_allowed(self):
        self.assertEqual(Path('-'), PathInput(allow_dash=True)('-'))

    def test_not_writable_rejected(self):
        with temp_directory() as tmp_path:
            a: Path = tmp_path.joinpath('a')
            a.touch()
            a.chmod(0o000)
            with self.assertRaises(ValueError):
                PathInput(writable=True)(a.as_posix())
            a.chmod(0o700)  # workaround for python 3.7 error

    def test_not_readable_rejected(self):
        with temp_directory() as tmp_path:
            a: Path = tmp_path.joinpath('a', 'b')
            with self.assertRaises(ValueError):
                PathInput(readable=True)(a.as_posix())

    def test_json_read(self):
        with temp_directory() as tmp_path:
            a: Path = tmp_path.joinpath('a')
            a.write_text('{"a": 1}')
            self.assertEqual({'a': 1}, Json()(a.as_posix()))

    def test_pickle_read(self):
        with temp_directory() as tmp_path:
            a: Path = tmp_path.joinpath('a')
            a.write_bytes(pickle.dumps({'a': 1}))
            self.assertEqual({'a': 1}, Deserialized(pickle.loads, binary=True)(a.as_posix()))

    def test_read_stdin(self):
        with patch('sys.stdin.read', return_value='test'):
            self.assertEqual('test', File(allow_dash=True)('-'))

    def test_file_read_text(self):
        with temp_directory() as tmp_path:
            a: Path = tmp_path.joinpath('a')
            a.write_text('test')
            self.assertEqual('test', File()(a.as_posix()))

    def test_command_read_text(self):
        class Foo(Command):
            bar = Positional(type=File())

        with temp_directory() as tmp_path:
            a: Path = tmp_path.joinpath('a')
            a.write_text('test')
            foo = Foo.parse_and_run([a.as_posix()])
            self.assertEqual('test', foo.bar)


if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    try:
        main(warnings='ignore', verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
