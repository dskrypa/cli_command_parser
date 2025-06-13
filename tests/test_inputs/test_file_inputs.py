#!/usr/bin/env python

import json
import os
import pickle
from contextlib import contextmanager
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterator
from unittest import TestCase, main
from unittest.mock import Mock, PropertyMock, call, patch

from cli_command_parser import Command, Option, Positional
from cli_command_parser.exceptions import BadArgument
from cli_command_parser.inputs import File, Json, Path as PathInput, Pickle, Serialized, StatMode
from cli_command_parser.inputs.exceptions import InputValidationError
from cli_command_parser.inputs.utils import FileWrapper, InputParam, fix_windows_path
from cli_command_parser.testing import ParserTest, RedirectStreams

PKG = 'cli_command_parser.inputs'
MODULE = f'{PKG}.files'


# region Helpers


@contextmanager
def temp_chdir(path: Path):
    cwd = Path.cwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(cwd)


@contextmanager
def temp_path(file: str = None, touch: bool = False) -> Iterator[Path]:
    with TemporaryDirectory() as tmp_dir:
        d = Path(tmp_dir)
        if file:
            f = d.joinpath(file)
            if touch:
                f.touch()
            yield f
        else:
            yield d


def fn_mock(return_value) -> Mock:
    return Mock(return_value=return_value)


# endregion


class FileInputTest(TestCase):
    # region Stat Mode

    def test_invalid_stat_modes(self):
        with self.assertRaises(TypeError):
            StatMode(None)

        for val in ('StatMode', '|', 'file|mock'):
            with self.subTest(val=val), self.assertRaises(ValueError):
                StatMode(val)

    def test_stat_mode_from_pipe_str(self):
        d, f, lnk = StatMode.DIR, StatMode.FILE, StatMode.LINK
        str_exp_map = {'dir|': d, '|dir': d, 'file|dir': d | f, 'file||dir': d | f, 'file|link|dir': d | f | lnk}
        for sm_str, expected in str_exp_map.items():
            with self.subTest(sm_str=sm_str):
                self.assertEqual(expected, StatMode(sm_str))

    def test_stat_mode_from_invert_str(self):
        not_dir = StatMode('FILE|CHARACTER|BLOCK|FIFO|LINK|SOCKET')
        not_dir_or_file = StatMode('CHARACTER|BLOCK|FIFO|LINK|SOCKET')
        str_exp_map = {'!dir': not_dir, '~dir': not_dir, '~dir|file': not_dir_or_file}
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

    def test_no_friendly_name(self):
        # This test is purely for coverage in Python < 3.11
        mode = StatMode.__new_member__(StatMode, 12345)  # noqa
        self.assertFalse(hasattr(mode, 'mode'))
        self.assertFalse(hasattr(mode, 'friendly_name'))

    # endregion

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

    # region Input Validation

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

    # endregion

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

    # region fix_windows_path

    @patch(f'{MODULE}.fix_windows_path')
    def test_windows_fix_not_called_on_posix(self, fwp_mock: Mock):
        # Note: The name patch must be after initializing the temp Path object, otherwise Path gets confused
        with temp_path('a') as a, patch(f'{MODULE}.os.name', 'posix'):
            PathInput(use_windows_fix=True).validated_path(a)

        fwp_mock.assert_not_called()

    @patch(f'{MODULE}.fix_windows_path')
    def test_windows_fix_called_on_windows(self, fwp_mock: Mock):
        with temp_path('a') as a, patch(f'{MODULE}.os.name', 'nt'):
            PathInput(use_windows_fix=True).validated_path(a)

        fwp_mock.assert_called_once()

    @patch(f'{MODULE}.fix_windows_path', side_effect=OSError)
    def test_windows_fix_error_ignored(self, fwp_mock: Mock):
        with temp_path('a') as a, patch(f'{MODULE}.os.name', 'nt'):
            PathInput(use_windows_fix=True).validated_path(a)

        fwp_mock.assert_called_once()

    def test_fix_windows_path_skips_paths_that_dont_need_fix(self):
        parts_mock = PropertyMock(return_value=[])

        path_mock = Mock(exists=fn_mock(True), parts=parts_mock)
        self.assertIs(path_mock, fix_windows_path(path_mock))
        parts_mock.assert_not_called()

        path_mock = Mock(exists=fn_mock(False), parts=parts_mock, as_posix=fn_mock('foo/bar'))
        self.assertIs(path_mock, fix_windows_path(path_mock))
        parts_mock.assert_not_called()

    def test_fix_windows_path_handles_value_error(self):
        path_mock = Mock(exists=fn_mock(False), parts=['/'], as_posix=fn_mock('/'))
        with patch(f'{PKG}.utils.len') as len_mock:
            self.assertIs(path_mock, fix_windows_path(path_mock))
            len_mock.assert_not_called()

    def test_fix_windows_path_ignores_multi_char_base_dir(self):
        path_mock = Mock(exists=fn_mock(False), parts=['/', 'foo'], as_posix=fn_mock('/foo'))
        with patch(f'{PKG}.utils.Path') as path_cls_mock:
            self.assertIs(path_mock, fix_windows_path(path_mock))
            path_cls_mock.assert_not_called()

    def test_fix_windows_path_returns_alt_path(self):
        path_mock = Mock(exists=fn_mock(False), parts=['/', 'b', 'foo', 'bar'], as_posix=fn_mock('/b/foo/bar'))
        alt_path_mock = Mock(exists=fn_mock(True))
        with patch(f'{PKG}.utils.Path', return_value=alt_path_mock) as path_cls_mock:
            self.assertIs(alt_path_mock, fix_windows_path(path_mock))
            path_cls_mock.assert_called_once_with('B:/', 'foo', 'bar')

    def test_fix_windows_path_returns_original_on_alt_not_existing(self):
        path_mock = Mock(exists=fn_mock(False), parts=['/', 'b', 'foo', 'bar'], as_posix=fn_mock('/b/foo/bar'))
        alt_path_mocks = [Mock(exists=fn_mock(False)), Mock(exists=fn_mock(False))]
        with patch(f'{PKG}.utils.Path', side_effect=alt_path_mocks) as path_cls_mock:
            self.assertIs(path_mock, fix_windows_path(path_mock))

        path_cls_mock.assert_has_calls([call('B:/', 'foo', 'bar'), call('B:/')])

    # endregion

    def test_fix_default_handling(self):
        class Cmd(Command):
            foo = Option(type=PathInput(), default='/var/tmp')
            bar = Option(type=PathInput(fix_default=False), default='123')
            baz = Option(type=PathInput(), default=None)

        cmd = Cmd()
        self.assertEqual(Path('/var/tmp'), cmd.foo)
        self.assertEqual('123', cmd.bar)
        self.assertIsNone(cmd.baz)

    def test_reprs(self):
        for input_cls in (PathInput, File, Json, Pickle):
            with self.subTest(input_cls=input_cls):
                self.assertTrue(repr(input_cls()).startswith(f'<{input_cls.__name__}('))


class WriteFileTest(TestCase):
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

    def test_write_create_parent_dir(self):
        with temp_path() as tmp_dir:
            path = tmp_dir.joinpath('a', 'b', 'c', 'd.txt')
            self.assertFalse(path.exists())
            with self.assertRaises(InputValidationError):
                File(mode='w')(path.as_posix()).write('test')

            File(mode='w', parents=True)(path.as_posix()).write('test')
            self.assertEqual('test', path.read_text())

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


class ReadFileTest(ParserTest):
    def test_plain_read_with(self):
        with temp_path('a') as a:
            a.write_text('{"a": 1}')
            with File()(a.as_posix()) as f:
                self.assertEqual('{"a": 1}', f.read())

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
        with RedirectStreams(StringIO('test')):
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

    def test_read_error(self):
        with temp_path() as tmp_path:
            b = tmp_path.joinpath('b')
            b.mkdir()
            with self.assert_raises_contains_str(InputValidationError, 'Unable to open'):
                File(lazy=False, type='any')(b.as_posix())

    def test_cmd_read_error(self):
        class Foo(Command, error_handler=None):
            bar = Option('-b', type=File(lazy=False, type='any'))

        with temp_path() as tmp_path:
            b = tmp_path.joinpath('b')
            b.mkdir()
            with self.assert_raises_contains_str(BadArgument, 'Unable to open'):
                Foo.parse_and_run(['-b', b.as_posix()])


class ReadJsonTest(ParserTest):
    def test_json_read_stdin(self):
        with RedirectStreams('{"a": 1, "b": 2}'):
            self.assertEqual({'a': 1, 'b': 2}, Json(allow_dash=True, lazy=False, mode='r')('-'))

    def test_json_read_stdin_bytes(self):
        with RedirectStreams(b'{"a": 1, "b": 2}'):
            self.assertEqual({'a': 1, 'b': 2}, Json(allow_dash=True, lazy=False, mode='rb')('-'))

    def test_json_read_stdin_invalid(self):
        with self.assert_raises_contains_str(InputValidationError, 'the provided json content - are you sure'):
            with RedirectStreams('{"a": 1, "b": 2]'):
                Json(allow_dash=True, lazy=False, mode='r')('-')

    def test_read_invalid_json(self):
        expected_error = r"json from file='.+?' - are you sure it contains properly formatted json\?"
        with temp_path() as tmp_path:
            data_path = tmp_path.joinpath('data.txt')
            data_path.write_text('test\n123')

            with self.subTest(lazy=False), self.assertRaisesRegex(InputValidationError, expected_error):
                Json(lazy=False)(data_path.as_posix())

            with self.subTest(lazy=True), self.assertRaisesRegex(InputValidationError, expected_error):
                Json(lazy=True)(data_path.as_posix()).read()

            with self.subTest(wrap_errors=False), self.assertRaises(json.JSONDecodeError):
                Json(lazy=False, wrap_errors=False)(data_path.as_posix())


class ParseInputTest(ParserTest):
    def test_short_option_no_space(self):
        class Foo(Command):
            foo = Option('-f', type=File(exists=False))
            bar = Option('-b', type=File(exists=False, allow_dash=True))

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
            bar = Option('-b', type=File(lazy=False, exists=False))

        for args in (['-b', 'test'], ['-btest']):
            with self.subTest(args=args):
                read_mock = Mock(return_value='test\ndata')
                with patch.object(FileWrapper, '_open', return_value=Mock(read=read_mock)):
                    foo = Foo.parse_and_run(args)
                    self.assertEqual('test\ndata', foo.bar)

                self.assertEqual(1, read_mock.call_count)

    def test_path_default_type_fix(self):
        class Foo(Command):
            config_dir = Option('-d', type=PathInput(type='dir', expand=False), default='~/.config')
            config_path = Option('-p', type=PathInput(type='dir', expand=False), default=Path('~/.config'))

        cases = {Path('~/.config'): [], Path('test'): ['-d', 'test', '-p', 'test']}
        for expected, argv in cases.items():
            with self.subTest(expected=expected, argv=argv):
                foo = Foo.parse(argv)
                self.assertIsInstance(foo.config_dir, Path)
                self.assertIsInstance(foo.config_path, Path)
                self.assertEqual(expected, foo.config_dir)
                self.assertEqual(expected, foo.config_path)


if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    try:
        main(verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
