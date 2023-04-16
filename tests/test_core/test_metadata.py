#!/usr/bin/env python

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, main
from unittest.mock import patch, Mock, seal

from cli_command_parser import Command, Context, main as ccp_main
from cli_command_parser.core import CommandMeta
from cli_command_parser.metadata import ProgramMetadata, Metadata, ProgFinder
from cli_command_parser.metadata import _path_and_globals, _description, _doc_name, _prog_finder, EntryPoint

MODULE = 'cli_command_parser.metadata'
THIS_FILE = Path(__file__)


class Foo(Command):
    pass


def ep_scripts(*name_val_tuples):
    cs = 'console_scripts'
    return tuple(EntryPoint(name, val, cs) for name, val in name_val_tuples)


class MetadataTest(TestCase):
    def test_repr(self):
        meta_repr = repr(CommandMeta.meta(Foo))
        self.assertRegex(meta_repr, r'\s{8}path=.*?/commands.py')
        self.assertRegex(meta_repr, r'\s{4}path=.*?/test_metadata.py')

    def test_metadata_self(self):
        self.assertIsInstance(ProgramMetadata.prog, Metadata)
        self.assertEqual('Metadata(default=None)', repr(ProgramMetadata.prog))

    def test_bad_arg(self):
        with self.assertRaisesRegex(TypeError, 'Invalid arguments for ProgramMetadata: bar, foo'):
            ProgramMetadata(foo=123, bar=456)

    # region Docstring / Description

    def test_cmd_doc_dedented(self):
        class Bar(Command):
            """
            Foo
            Bar
            Baz
            """

        self.assertEqual('Foo\nBar\nBaz\n', Bar.__class__.meta(Bar).description)

    def test_empty_doc_ignored(self):
        self.assertIs(None, _description(None, '\n\n'))

    def test_doc_str_non_pkg(self):
        meta = ProgramMetadata(doc_str=' test ')
        self.assertEqual('test', meta.get_doc_str())
        self.assertEqual(' test ', meta.get_doc_str(False))

    def test_doc_str_pkg(self):
        meta = ProgramMetadata(doc_str=' test ', pkg_doc_str=' pkg test ')
        self.assertEqual('pkg test', meta.get_doc_str())
        self.assertEqual(' pkg test ', meta.get_doc_str(False))

    # endregion

    def test_extended_epilog(self):
        meta = ProgramMetadata(
            prog='foo', epilog='test', version='4.3.2', email='example@fake.com', url='http://fake.com'
        )
        self.assertEqual('test', meta.format_epilog(False))
        expected = 'test\n\nReport foo [ver. 4.3.2] bugs to example@fake.com\n\nOnline documentation: http://fake.com'
        self.assertEqual(expected, meta.format_epilog())

    def test_extended_epilog_no_email(self):
        meta = ProgramMetadata(prog='foo', epilog='test', version='4.3.2', url='http://fake.com')
        self.assertEqual('test\n\nOnline documentation: http://fake.com', meta.format_epilog())

    def test_doc_name_prog(self):
        self.assertEqual('test_123', _doc_name(None, Path('UNKNOWN'), 'test_123'))

    # region Docs URL

    def test_doc_url_none(self):
        self.assertIs(None, ProgramMetadata(url='https://github.com/foo').docs_url)

    def test_docs_url(self):
        meta = ProgramMetadata.for_command(Foo, url='https://github.com/foo/bar')
        self.assertEqual('https://foo.github.io/bar/', meta.docs_url)

    def test_docs_url_no_repo(self):
        self.assertIs(None, ProgramMetadata.for_command(Foo, url='https://github.com/').docs_url)

    def test_docs_url_not_https(self):
        self.assertIs(None, ProgramMetadata.for_command(Foo, url='hxxps://test.com/fake').docs_url)

    # endregion

    # region Path & Globals

    def test_cwd_default(self):
        self.assertEqual(Path.cwd().joinpath('UNKNOWN'), _path_and_globals(None, None)[0])  # noqa

    def test_path_from_cmd(self):
        self.assertEqual(THIS_FILE.resolve(), _path_and_globals(Foo)[0])

    def test_explicit_path(self):
        path = Path('.')
        self.assertEqual(path, _path_and_globals(Foo, path)[0])

    # endregion


class MetadataProgTest(TestCase):
    def test_prog_from_path_on_no_sys_argv(self):
        with patch('sys.argv', []):
            # self.assertEqual(path.name, _prog(None, path, None, False)[0])
            self.assertEqual(THIS_FILE.name, _prog_finder.normalize(None, THIS_FILE, None, False, Mock())[0])

    def test_prog_from_sys_argv(self):
        name = 'example_test_123.py'
        with TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir).joinpath(name)
            tmp_path.touch()
            with patch('sys.argv', [tmp_path.as_posix()]), Context():
                # self.assertEqual(name, _prog(None, path, None, False)[0])
                self.assertEqual(name, _prog_finder.normalize(None, THIS_FILE, None, False, Mock())[0])

    def test_entry_points_old(self):
        entry_points = {'console_scripts': ep_scripts(('bar.py', 'foo:bar'), ('baz.py', 'foo:baz'))}
        expected = {'foo': {'bar': 'bar.py', 'baz': 'baz.py'}}
        with patch(f'{MODULE}.entry_points', side_effect=[TypeError, entry_points]):  # Simulate py 3.8/3.9
            self.assertDictEqual(expected, ProgFinder().mod_obj_prog_map)

    def test_entry_points_new(self):
        entry_points = ep_scripts(('bar.py', 'foo:bar'), ('baz.py', 'foo:baz'))
        expected = {'foo': {'bar': 'bar.py', 'baz': 'baz.py'}}
        with patch(f'{MODULE}.entry_points', return_value=entry_points):
            self.assertDictEqual(expected, ProgFinder().mod_obj_prog_map)

    def test_prog_from_entry_point_main(self):
        Cmd = type('Cmd', (Command,), {'__module__': 'foo.bar'})
        entry_points = ep_scripts(('bar.py', 'foo.bar:bar'), ('baz.py', 'foo.bar:main'))
        mod = Mock(main=ccp_main)
        seal(mod)  # Trigger the obj = getattr(...) AttributeError
        with patch(f'{MODULE}.modules', {'foo.bar': mod}), patch(f'{MODULE}.entry_points', return_value=entry_points):
            self.assertEqual('baz.py', ProgFinder().normalize(None, THIS_FILE, None, False, Cmd)[0])  # noqa

    def test_prog_from_entry_point_method(self):
        Cmd = type('Cmd', (Command,), {'__module__': 'foo.bar'})
        entry_points = ep_scripts(('bar.py', 'foo.bar:bar'), ('baz.py', 'foo.bar:Cmd.parse_and_run'))
        with patch(f'{MODULE}.modules', {'foo.bar': Mock(Cmd=Cmd)}):
            with patch(f'{MODULE}.entry_points', return_value=entry_points):
                self.assertEqual('baz.py', ProgFinder().normalize(None, THIS_FILE, None, False, Cmd)[0])  # noqa

    def test_prog_from_entry_point_with_extras(self):
        Cmd = type('Cmd', (Command,), {'__module__': 'foo.bar'})
        entry_points = ep_scripts(('bar.py', 'foo.bar:bar'), ('baz.py', 'foo.bar:main [test]'))
        with patch(f'{MODULE}.modules', {'foo.bar': Mock(main=ccp_main)}):
            with patch(f'{MODULE}.entry_points', return_value=entry_points):
                self.assertEqual('baz.py', ProgFinder().normalize(None, THIS_FILE, None, False, Cmd)[0])  # noqa

    def test_prog_no_entry_point_found(self):
        Cmd = type('Cmd', (Command,), {'__module__': 'foo.bar'})
        entry_points = ep_scripts(('bar.py', 'foo.bar:bar'), ('baz.py', 'foo.bar:main'))
        with patch(f'{MODULE}.modules', {'foo.bar': Mock()}):
            with patch(f'{MODULE}.entry_points', return_value=entry_points):
                self.assertEqual(THIS_FILE.name, ProgFinder().normalize(None, THIS_FILE, None, False, Cmd)[0])  # noqa


if __name__ == '__main__':
    try:
        main(verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
