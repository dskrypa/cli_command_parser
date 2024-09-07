#!/usr/bin/env python

from inspect import Signature
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, main
from unittest.mock import Mock, patch, seal

from cli_command_parser import Command, Context, main as ccp_main
from cli_command_parser.core import META_KEYS, CommandMeta, get_metadata
from cli_command_parser.metadata import (
    DynamicMetadata,
    EntryPoint,
    Metadata,
    ProgFinder,
    ProgramMetadata,
    _description,
    _path_and_globals,
    _prog_finder,
    dynamic_metadata,
)
from cli_command_parser.testing import ParserTest

MODULE = 'cli_command_parser.metadata'
THIS_FILE = Path(__file__)


class Foo(Command):
    pass


def ep_scripts(*name_val_tuples):
    cs = 'console_scripts'
    return tuple(EntryPoint(name, val, cs) for name, val in name_val_tuples)  # noqa


class MetadataTest(ParserTest):
    def test_repr(self):
        meta_repr = repr(CommandMeta.meta(Foo))
        self.assertRegex(meta_repr, r'\s{8}path=.*?/commands.py')
        self.assertRegex(meta_repr, r'\s{4}path=.*?/test_metadata.py')

    def test_metadata_self(self):
        self.assertIsInstance(ProgramMetadata.epilog, Metadata)
        self.assertIsInstance(ProgramMetadata.prog, DynamicMetadata)
        self.assertEqual('Metadata(default=None, inheritable=True)', repr(ProgramMetadata.epilog))
        self.assertEqual('DynamicMetadata(func=ProgramMetadata.prog, inheritable=True)', repr(ProgramMetadata.prog))

    def test_bad_arg(self):
        with self.assert_raises_contains_str(TypeError, 'Invalid arguments for ProgramMetadata: bar, foo'):
            ProgramMetadata(foo=123, bar=456)

    def test_dynamic_metadata_no_args(self):
        class Bar:
            _fields = set()

            @dynamic_metadata
            def baz(self):
                return 1

        self.assertIsInstance(Bar.baz, DynamicMetadata)

    # region Docstring / Description

    def test_cmd_doc_dedented(self):
        class Bar(Command):
            """
            Foo
            Bar
            Baz
            """

        self.assertEqual('Foo\nBar\nBaz\n', get_metadata(Bar).description)

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

    def test_docs_url_via_command_kwarg(self):
        class Bar(Command, docs_url='hxxps://test.com/fake'):
            pass

        self.assertEqual('hxxps://test.com/fake', get_metadata(Bar).docs_url)

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

    def test_command_kwargs_include_all_meta_kwargs(self):
        meta_kwargs = set(Signature.from_callable(ProgramMetadata.for_command).parameters)
        meta_kwargs -= {'command', 'parent'}  # Kwargs not intended to be provided by users
        self.assertEqual(
            META_KEYS,
            meta_kwargs,
            'cli_command_parser.core.META_KEYS need to be updated to match ProgramMetadata.for_command kwargs',
        )


class MetadataProgTest(TestCase):
    def test_prog_from_path_on_no_sys_argv(self):
        with patch('sys.argv', []):
            self.assertEqual(THIS_FILE.name, _prog_finder.normalize(THIS_FILE, None, True, 'foo.bar', 'Baz')[0])

    def test_prog_from_sys_argv(self):
        name = 'example_test_123.py'
        with TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir).joinpath(name)
            tmp_path.touch()
            with patch('sys.argv', [tmp_path.as_posix()]), Context():
                self.assertEqual(name, _prog_finder.normalize(THIS_FILE, None, True, 'foo.bar', 'Baz')[0])

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
        cmd_mod, cmd_name = 'foo.bar', 'Cmd'
        entry_points = ep_scripts(('bar.py', 'foo.bar:bar'), ('baz.py', 'foo.bar:main'))
        mod = Mock(main=ccp_main)
        seal(mod)  # Trigger the obj = getattr(...) AttributeError
        with patch(f'{MODULE}.modules', {'foo.bar': mod}), patch(f'{MODULE}.entry_points', return_value=entry_points):
            for argv_ok in (True, False):
                self.assertEqual('baz.py', ProgFinder().normalize(THIS_FILE, None, argv_ok, cmd_mod, cmd_name)[0])

    def test_prog_from_entry_point_method(self):
        cmd_mod, cmd_name = 'foo.bar', 'Cmd'
        Cmd = type(cmd_name, (Command,), {'__module__': cmd_mod})
        entry_points = ep_scripts(('bar.py', 'foo.bar:bar'), ('baz.py', 'foo.bar:Cmd.parse_and_run'))
        with patch(f'{MODULE}.modules', {'foo.bar': Mock(Cmd=Cmd)}):
            with patch(f'{MODULE}.entry_points', return_value=entry_points):
                for argv_ok in (True, False):
                    self.assertEqual('baz.py', ProgFinder().normalize(THIS_FILE, None, argv_ok, cmd_mod, cmd_name)[0])

    def test_prog_from_entry_point_with_extras(self):
        cmd_mod, cmd_name = 'foo.bar', 'Cmd'
        entry_points = ep_scripts(('bar.py', 'foo.bar:bar'), ('baz.py', 'foo.bar:main [test]'))
        with patch(f'{MODULE}.modules', {'foo.bar': Mock(main=ccp_main)}):
            with patch(f'{MODULE}.entry_points', return_value=entry_points):
                for argv_ok in (True, False):
                    self.assertEqual('baz.py', ProgFinder().normalize(THIS_FILE, None, argv_ok, cmd_mod, cmd_name)[0])

    def test_prog_no_entry_point_found(self):
        cmd_mod, cmd_name = 'foo.bar', 'Cmd'
        entry_points = ep_scripts(('bar.py', 'foo.bar:bar'), ('baz.py', 'foo.bar:main'))
        exp_name = THIS_FILE.name
        with patch(f'{MODULE}.modules', {'foo.bar': Mock()}):
            with patch(f'{MODULE}.entry_points', return_value=entry_points):
                for argv_ok in (True, False):
                    self.assertEqual(exp_name, ProgFinder().normalize(THIS_FILE, None, argv_ok, cmd_mod, cmd_name)[0])


if __name__ == '__main__':
    try:
        main(verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
