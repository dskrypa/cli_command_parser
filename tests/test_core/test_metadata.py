#!/usr/bin/env python

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, main
from unittest.mock import patch

from cli_command_parser import Command, Context
from cli_command_parser.core import CommandMeta
from cli_command_parser.metadata import ProgramMetadata, Metadata, _path_and_globals, _description, _doc_name, _prog


class Foo(Command):
    pass


class MetadataTest(TestCase):
    def test_repr(self):
        meta = CommandMeta.meta(Foo)
        meta_repr = repr(meta)
        self.assertRegex(meta_repr, r'\s{8}path=.*?/commands.py')
        self.assertRegex(meta_repr, r'\s{4}path=.*?/test_metadata.py')

    def test_cmd_doc_dedented(self):
        class Bar(Command):
            """
            Foo
            Bar
            Baz
            """

        self.assertEqual('Foo\nBar\nBaz\n', Bar.__class__.meta(Bar).description)

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

    def test_doc_url_none(self):
        self.assertIs(None, ProgramMetadata(url='https://github.com/foo').docs_url)

    def test_docs_url(self):
        meta = ProgramMetadata.for_command(Foo, url='https://github.com/foo/bar')
        self.assertEqual('https://foo.github.io/bar/', meta.docs_url)

    def test_docs_url_no_repo(self):
        self.assertIs(None, ProgramMetadata.for_command(Foo, url='https://github.com/').docs_url)

    def test_docs_url_not_https(self):
        self.assertIs(None, ProgramMetadata.for_command(Foo, url='hxxps://test.com/fake').docs_url)

    def test_doc_name_prog(self):
        self.assertEqual('test_123', _doc_name(None, Path('UNKNOWN'), 'test_123'))

    def test_empty_doc_ignored(self):
        self.assertIs(None, _description(None, '\n\n'))

    def test_cwd_default(self):
        self.assertEqual(Path.cwd().joinpath('UNKNOWN'), _path_and_globals(None, None)[0])  # noqa

    def test_path_from_cmd(self):
        self.assertEqual(Path(__file__).resolve(), _path_and_globals(Foo)[0])

    def test_explicit_path(self):
        path = Path('.')
        self.assertEqual(path, _path_and_globals(Foo, path)[0])

    def test_prog_from_path_on_no_sys_argv(self):
        path = Path(__file__)
        with patch('sys.argv', []):
            self.assertEqual(path.name, _prog(None, path, None, False)[0])

    def test_prog_from_sys_argv(self):
        path = Path(__file__)
        name = 'example_test_123.py'
        with TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir).joinpath(name)
            tmp_path.touch()
            with patch('sys.argv', [tmp_path.as_posix()]), Context():
                self.assertEqual(name, _prog(None, path, None, False)[0])

    def test_doc_str_non_pkg(self):
        meta = ProgramMetadata(doc_str=' test ')
        self.assertEqual('test', meta.get_doc_str())
        self.assertEqual(' test ', meta.get_doc_str(False))

    def test_doc_str_pkg(self):
        meta = ProgramMetadata(doc_str=' test ', pkg_doc_str=' pkg test ')
        self.assertEqual('pkg test', meta.get_doc_str())
        self.assertEqual(' pkg test ', meta.get_doc_str(False))

    def test_metadata_self(self):
        self.assertIsInstance(ProgramMetadata.prog, Metadata)
        self.assertEqual('Metadata(default=None)', repr(ProgramMetadata.prog))

    def test_bad_arg(self):
        with self.assertRaisesRegex(TypeError, 'Invalid arguments for ProgramMetadata: bar, foo'):
            ProgramMetadata(foo=123, bar=456)


if __name__ == '__main__':
    try:
        main(verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
