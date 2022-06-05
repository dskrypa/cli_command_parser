#!/usr/bin/env python

import json
import os
import pickle
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import ContextManager
from unittest import main, TestCase
from unittest.mock import patch, Mock

from cli_command_parser import Command, Positional, Option
from cli_command_parser.inputs import Path as PathInput, File, Serialized, Json, Pickle, StatMode
from cli_command_parser.inputs.utils import InputParam, FileWrapper
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
def temp_path(file: str = None, touch: bool = False) -> ContextManager[Path]:
    with TemporaryDirectory() as tmp_dir:
        d = Path(tmp_dir)
        if file:
            f = d.joinpath(file)
            if touch:
                f.touch()
            yield f
        else:
            yield d


class InputTest(TestCase):
    def test_invalid_stat_modes(self):
        with self.assertRaises(TypeError):
            StatMode(None)
        with self.assertRaises(TypeError):
            StatMode('StatMode')
        with self.assertRaises(TypeError):
            StatMode('|')
        with self.assertRaises(TypeError):
            StatMode('file|mock')

    def test_stat_mode_from_pipe_str(self):
        d, f, lnk = StatMode.DIR, StatMode.FILE, StatMode.LINK
        str_exp_map = {'dir|': d, '|dir': d, 'file|dir': d | f, 'file||dir': d | f, 'file|link|dir': d | f | lnk}
        for sm_str, expected in str_exp_map.items():
            with self.subTest(sm_str=sm_str):
                self.assertEqual(expected, StatMode(sm_str))

    def test_stat_mode_combo_strs(self):
        self.assertEqual('directory', str(StatMode.DIR))
        self.assertEqual('directory or regular file', str(StatMode.DIR | StatMode.FILE))
        expected = 'directory, regular file, or symbolic link'
        self.assertEqual(expected, str(StatMode.DIR | StatMode.FILE | StatMode.LINK))

    def test_stat_mode_combo_reprs(self):
        self.assertEqual('<StatMode:DIR>', repr(StatMode.DIR))
        self.assertEqual('<StatMode:DIR|FILE>', repr(StatMode.DIR | StatMode.FILE))
        self.assertEqual('<StatMode:DIR|FILE|LINK>', repr(StatMode.DIR | StatMode.FILE | StatMode.LINK))

    def test_input_param_on_cls(self):
        self.assertIsInstance(PathInput.exists, InputParam)

    def test_path_reprs(self):
        self.assertEqual('<Path()>', repr(PathInput()))
        self.assertEqual('<Path(exists=True)>', repr(PathInput(exists=True)))
        self.assertEqual('<Path(exists=True, type=<StatMode:DIR>)>', repr(PathInput(exists=True, type='dir')))
        self.assertEqual('<File(exists=True)>', repr(File(exists=True)))

    def test_path_resolve(self):
        with temp_path('a', True) as a, temp_chdir(a.parent):
            self.assertEqual(a, PathInput(exists=True, resolve=True, type='file', expand=False)('a'))

    def test_path_reject_missing(self):
        with temp_path('a') as a:
            with self.assertRaises(ValueError):
                PathInput(exists=True)(a.as_posix())

    def test_path_reject_exists(self):
        with temp_path('a', True) as a:
            with self.assertRaises(ValueError):
                PathInput(exists=False)(a.as_posix())

    def test_path_reject_dir(self):
        with TemporaryDirectory() as tmp_dir:
            with self.assertRaises(ValueError):
                PathInput(type=StatMode.FILE)(tmp_dir)

    def test_path_reject_file(self):
        with temp_path('a', True) as a:
            with self.assertRaises(ValueError):
                PathInput(type=StatMode.LINK | StatMode.DIR)(a.as_posix())

    def test_path_accept_file_or_dir(self):
        with temp_path('a', True) as a:
            b = a.parent.joinpath('b')
            b.mkdir()
            pi = PathInput(type=StatMode.DIR | StatMode.FILE)
            self.assertEqual(a, pi(a.as_posix()))
            self.assertEqual(b, pi(b.as_posix()))

    def test_empty_arg_rejected(self):
        with self.assertRaises(ValueError):
            PathInput()('')

    def test_write_eager_rejected(self):
        for case in ('w', 'a', 'wb', 'wt', 'r+', 'r+b'):
            with self.subTest(case=case), self.assertRaises(ValueError):
                File(mode=case, lazy=False)

    def test_dash_rejected(self):
        with self.assertRaises(ValueError):
            PathInput()('-')

    def test_dash_allowed(self):
        self.assertEqual(Path('-'), PathInput(allow_dash=True)('-'))

    def test_not_writable_rejected(self):
        with temp_path('a', True) as a:
            a.chmod(0o000)
            with self.assertRaises(ValueError):
                PathInput(writable=True)(a.as_posix())
            a.chmod(0o700)  # workaround for python 3.7 error

    def test_not_readable_rejected(self):
        with temp_path() as tmp_path:
            a = tmp_path.joinpath('a', 'b')
            with self.assertRaises(ValueError):
                PathInput(readable=True)(a.as_posix())

    def test_pickle_text_rejected(self):
        for case in ('rt', 'r+t', 'wt'):
            with self.subTest(case=case), self.assertRaises(ValueError):
                Pickle(mode=case)

    def test_pickle_b_added(self):
        self.assertEqual('rb', Pickle(mode='r').mode)
        self.assertEqual('r+b', Pickle(mode='r+').mode)
        self.assertEqual('wb', Pickle(mode='w').mode)

    def test_close_no_fp(self):
        with temp_path('a') as a:
            fw = FileWrapper(a)
            fw._fp = 'test'
            fw._close()
            self.assertIs(None, fw._fp)

    def test_close_warning(self):
        with self.assertWarns(ResourceWarning):
            FileWrapper._cleanup(Mock(), 'test')

    def test_file_wrapper_eq_bad_type(self):
        self.assertNotEqual('test', FileWrapper(Path('test')))


class ReadWriteTest(TestCase):
    def test_plain_read_with(self):
        with temp_path('a') as a:
            a.write_text('{"a": 1}')
            with File()(a.as_posix()) as f:
                self.assertEqual('{"a": 1}', f.read())

    def test_plain_write_with(self):
        with temp_path('a') as a:
            a.write_text('a\n')
            with File(mode='a')(a.as_posix()) as f:
                f.write('b')

            self.assertEqual('a\nb', a.read_text())

    def test_plain_write(self):
        with temp_path('a') as a:
            File(mode='w')(a.as_posix()).write('test')
            self.assertEqual('test', a.read_text())

    def test_json_read(self):
        with temp_path('a') as a:
            a.write_text('{"a": 1}')
            self.assertEqual({'a': 1}, Json(lazy=False)(a.as_posix()))

    def test_json_read_with(self):
        with temp_path('a') as a:
            a.write_text('{"a": 1}')
            with Json()(a.as_posix()) as j:
                self.assertEqual({'a': 1}, j.read())

    def test_json_write(self):
        with temp_path('a') as a:
            j = Json(mode='w')(a.as_posix())
            j.write({'a': 1})
            self.assertEqual('{"a": 1}', a.read_text())

    def test_json_write_with(self):
        with temp_path('a') as a:
            with Json(mode='w')(a.as_posix()) as j:
                j.write({'a': 1})
            self.assertEqual('{"a": 1}', a.read_text())

    def test_serialized_json_write_with(self):
        with temp_path('a') as a:
            with Serialized(json.dumps, mode='w')(a.as_posix()) as j:
                j.write({'a': 1})
            self.assertEqual('{"a": 1}', a.read_text())

    def test_serialized_pickle_read(self):
        with temp_path('a') as a:
            a.write_bytes(pickle.dumps({'a': 1}))
            self.assertEqual({'a': 1}, Serialized(pickle.loads, mode='rb', lazy=False)(a.as_posix()))

    def test_serialized_pickle_read_with(self):
        with temp_path('a') as a:
            a.write_bytes(pickle.dumps({'a': 1}))
            with Serialized(pickle.loads, mode='rb')(a.as_posix()) as f:
                self.assertEqual({'a': 1}, f.read())

    def test_pickle_read(self):
        with temp_path('a') as a:
            a.write_bytes(pickle.dumps({'a': 1}))
            self.assertEqual({'a': 1}, Pickle(lazy=False)(a.as_posix()))

    def test_read_stdin(self):
        with patch('sys.stdin.read', return_value='test'):
            self.assertEqual('test', File(allow_dash=True, lazy=False)('-'))

    def test_file_read_text(self):
        with temp_path('a') as a:
            a.write_text('test')
            self.assertEqual('test', File(lazy=False)(a.as_posix()))

    def test_command_read_text(self):
        class Foo(Command):
            bar = Positional(type=File(lazy=False))

        with temp_path('a') as a:
            a.write_text('test')
            foo = Foo.parse_and_run([a.as_posix()])
            self.assertEqual('test', foo.bar)


class ParseInputTest(ParserTest):
    def test_short_option_no_space(self):
        class Foo(Command):
            foo = Option('-f', type=File())
            bar = Option('-b', type=File(allow_dash=True))

        success_cases = [
            (['-bar'], {'bar': FileWrapper(Path('ar')), 'foo': None}),
            (['-btest'], {'bar': FileWrapper(Path('test')), 'foo': None}),
            (['-ftest'], {'foo': FileWrapper(Path('test')), 'bar': None}),
            (['-b-'], {'bar': FileWrapper(Path('-')), 'foo': None}),
        ]
        with temp_path() as tmp_path, temp_chdir(tmp_path):
            self.assert_parse_results_cases(Foo, success_cases)

    def test_only_read_once(self):
        class Foo(Command):
            bar = Option('-b', type=File(lazy=False))

        for args in (['-b', 'test'], ['-btest']):
            with self.subTest(args=args):
                read_mock = Mock(return_value='test\ndata')
                with patch.object(FileWrapper, '_open', return_value=Mock(read=read_mock)):
                    foo = Foo.parse_and_run(args)
                    self.assertEqual('test\ndata', foo.bar)

                self.assertEqual(1, read_mock.call_count)


if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    try:
        main(warnings='ignore', verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
