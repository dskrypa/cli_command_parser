#!/usr/bin/env python

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, main
from unittest.mock import Mock, patch

from cli_command_parser.metadata import ProgramMetadata, ProgInfo
from cli_command_parser.utils import camel_to_snake_case, get_args


class UtilsTest(TestCase):
    def test_camel_to_snake(self):
        self.assertEqual('foo_bar', camel_to_snake_case('FooBar'))
        self.assertEqual('foo bar', camel_to_snake_case('FooBar', ' '))
        self.assertEqual('foo', camel_to_snake_case('Foo'))

    def test_get_args(self):
        # This is for coverage in 3.9+ for the get_args compatibility wrapper, to mock the attr present in 3.8 & below
        self.assertEqual((), get_args(Mock(_special=True)))

    def test_meta_name(self):
        meta = ProgramMetadata(doc_name='foo')
        self.assertEqual('foo', meta.doc_name)

    def test_real_bad_path(self):
        with TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir).joinpath('foo.py')
            with patch('cli_command_parser.metadata.sys.argv', [tmp_path.as_posix()]):
                with patch.object(ProgInfo, '_find_top_frame_and_globals', side_effect=RuntimeError):
                    meta = ProgramMetadata()
                    self.assertEqual(meta.path.name, 'UNKNOWN')

    def test_fake_bad_path(self):
        with patch('pathlib.Path.is_file', side_effect=OSError):
            with patch.object(ProgInfo, '_find_top_frame_and_globals', side_effect=RuntimeError):
                meta = ProgramMetadata()
                self.assertEqual(meta.path.name, 'UNKNOWN')

    def test_prog_info_repr(self):
        self.assertIsNotNone(repr(ProgInfo()))


if __name__ == '__main__':
    try:
        main(warnings='ignore', verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
