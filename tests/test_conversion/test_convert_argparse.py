#!/usr/bin/env python

from __future__ import annotations

import ast
from itertools import count
from typing import TYPE_CHECKING
from unittest import main
from unittest.mock import Mock, patch

from cli_command_parser.compat import cached_property
from cli_command_parser.conversion.argparse_ast import Script, AstArgumentParser, AstCallable
from cli_command_parser.conversion.argparse_ast import AddVisitedChild, visit_func
from cli_command_parser.conversion.argparse_utils import ArgumentParser, SubParsersAction
from cli_command_parser.conversion.command_builder import Converter, ParserConverter, ParamConverter, convert_script
from cli_command_parser.conversion.command_builder import ConversionError
from cli_command_parser.conversion.utils import get_name_repr, collection_contents
from cli_command_parser.conversion.visitor import ScriptVisitor, TrackedRefMap, TrackedRef
from cli_command_parser.testing import ParserTest, RedirectStreams

if TYPE_CHECKING:
    from cli_command_parser.conversion.argparse_ast import InitNode


PACKAGE = 'cli_command_parser.conversion'
CMD0 = 'Command0'
DISCLAIMER = '# This is an automatically generated name that should probably be updated'
IMPORT_LINE = (
    'from cli_command_parser import Command, SubCommand, ParamGroup, Positional, Option, Flag, Counter, PassThru, main'
)


# region Helper functions


def prep_args(*add_args: str, remainder: bool = False) -> str:
    if remainder:
        imports = 'from argparse import REMAINDER, ArgumentParser as AP'
    else:
        imports = 'from argparse import ArgumentParser as AP'
    return '\n'.join((imports, 'p = AP()', *(f'p.add_argument({arg})' for arg in add_args)))


def prep_cmd(*members: str, name: str = CMD0, base: str = 'Command', suffix: str = '', **kwargs) -> str:
    if kwargs:
        cmd_args = ', ' + ', '.join(f'{k}={v}' for k, v in kwargs.items())
    else:
        cmd_args = ''

    cls_def_line = f'class {name}({base}{cmd_args}):{suffix}'
    if members:
        return '\n'.join((cls_def_line, *(f'    {mem}' if mem else mem for mem in members)))
    return cls_def_line


def prep_group(*add_args: str, title: str = None, description: str = None, parser: str = 'p', var: str = 'g') -> str:
    group_arg_str = ', '.join(f'{k}={v!r}' for k, v in {'title': title, 'description': description}.items() if v)
    add_arg_iter = (f'{var}.add_argument({arg})' for arg in add_args)
    return '\n'.join((f'{var} = {parser}.add_argument_group({group_arg_str})', *add_arg_iter))


def prep_expected(*members: str, name: str = CMD0, parent: str = 'Command', **kwargs) -> str:
    expected = IMPORT_LINE + '\n\n\n' + prep_cmd(*members, name=name, base=parent, suffix=f'  {DISCLAIMER}', **kwargs)
    return expected if members else expected + '\n'


def prep_and_convert(*add_argument_args_strs: str, remainder: bool = False, **kwargs) -> str:
    code = prep_args(*add_argument_args_strs, remainder=remainder)
    return convert_script(Script(code), **kwargs)


# endregion


class CommandBuilderTest(ParserTest):
    # region Sub Parsers / Command kwargs

    def test_sub_parser_args_in_loop(self):
        code = """import argparse\nparser = argparse.ArgumentParser()
subparsers = parser.add_subparsers(dest='action')
sp1 = subparsers.add_parser('one', help='Command one')
sp1.add_argument('--foo-bar', '-f', action='store_true', help='Do foo bar')
sp2 = subparsers.add_parser('two', description='Command two')
sp2.add_argument('--baz', '-b', nargs='+', help='What to baz')
for sp in (sp1, sp2):
    group = sp.add_argument_group('Common options')
    group.add_argument('--verbose', '-v', action='count', default=0, help='Increase logging verbosity')
    group.add_argument('--dry-run', '-D', action='store_true', help='Perform a dry run with no side effects')
        """

        common = """
    with ParamGroup(description='Common options'):
        verbose = Counter('-v', help='Increase logging verbosity')
        dry_run = Flag('-D', help='Perform a dry run with no side effects')
        """.rstrip()
        base = prep_expected('action = SubCommand()')
        a = "class One(Command0, help='Command one'):\n    foo_bar = Flag('-f', help='Do foo bar')\n"
        b = "class Two(Command0, description='Command two'):\n    baz = Option('-b', nargs='+', help='What to baz')\n"
        cases = [(True, f'{base}\n{common}\n\n\n{a}\n\n{b}'), (False, f'{base}\n\n\n{a}{common}\n\n\n{b}{common}')]
        for smart_loop_handling, expected in cases:
            with self.subTest(smart_loop_handling=smart_loop_handling):
                self.assert_strings_equal(expected, convert_script(Script(code, smart_loop_handling)), trim=True)

    def test_sub_parser_args_mismatch_in_loop(self):
        code = """
import argparse as ap
parser = ap.ArgumentParser()
add_arg = parser.add_argument
add_arg('foo')
subparsers = parser.add_subparsers(dest='action')
sp1 = subparsers.add_parser('one', help='Command one')
sp1.add_argument('--foo-bar', '-f', action='store_true', help='Do foo bar')
sp2 = subparsers.add_parser('two', description='Command two')
sp2.add_argument('--baz', '-b', nargs='+', help='What to baz')
for sp in [sp1, sp123456789]:
    group = sp.add_mutually_exclusive_group()
    group.add_argument('--verbose', '-v', action='count', default=0, help='Increase logging verbosity')
    group.add_argument('--dry_run', '-D', action='store_true', help='Perform a dry run with no side effects')
        """

        expected = f"""{prep_expected("foo = Positional()", "action = SubCommand()")}\n\n
class One(Command0, help='Command one'):
    foo_bar = Flag('-f', help='Do foo bar')\n
    with ParamGroup(mutually_exclusive=True):
        verbose = Counter('-v', help='Increase logging verbosity')
        dry_run = Flag('-D', name_mode='_', help='Perform a dry run with no side effects')
\n
class Two(Command0, description='Command two'):
    baz = Option('-b', nargs='+', help='What to baz')
        """.rstrip()
        self.assert_strings_equal(expected, convert_script(Script(code)))

    def test_parser_add_help(self):
        code = 'from argparse import ArgumentParser as AP\np1 = AP(add_help=False)\np2 = AP(add_help=True)\n'
        cmds = (prep_expected('pass', add_help='False'), prep_cmd('pass', name='Command1', suffix=f'  {DISCLAIMER}'))
        self.assert_strings_equal('\n\n\n'.join(cmds), convert_script(Script(code)))

    def test_sub_parser_choices(self):
        code = """
from argparse import ArgumentParser
p1 = ArgumentParser()
sp_act = p1.add_subparsers(dest='in')
sp_act.add_parser('foo-bar')
sp_act.add_parser('foo', aliases=('bar', 'baz'))
p2 = ArgumentParser()
sp_act = p2.add_subparsers()
sp_act.add_parser(aliases=(k for k in 'abc'))
sp_act.add_parser(aliases={k: 1 for k in 'abc'})
sp_act.add_parser(aliases={'a': 1, 'b': 2})
sp_act.add_parser(aliases=ALIASES)
sp_act.add_parser(BAR, aliases=BARS['x'])
sp_act.add_parser(aliases={'a'})
sp_act.add_parser(aliases=())
sp_act.add_parser('abc def')
sp_act.add_parser('123 456')
        """

        expected = f"""{IMPORT_LINE}\n\n
class Command0(Command):  {DISCLAIMER}\n    sub_cmd = SubCommand()\n\n
class FooBar(Command0, choice='foo-bar'):\n    pass\n\n
class Foo(Command0, choices=('foo', 'bar', 'baz')):\n    pass\n\n
class Command1(Command):  {DISCLAIMER}\n    sub_cmd = SubCommand()\n\n
class Command2(Command1, choices=tuple(k for k in 'abc')):\n    pass\n\n
class Command3(Command1, choices={{k: 1 for k in 'abc'}}):\n    pass\n\n
class Command4(Command1, choices=('a', 'b')):\n    pass\n\n
class Command5(Command1, choices=ALIASES):\n    pass\n\n
class Command6(Command1, choices=(BAR, *BARS['x'])):\n    pass\n\n
class Command7(Command1, choice='a'):\n    pass\n\n
class Command8(Command1):\n    pass\n\n
class AbcDef(Command1, choice='abc def'):\n    pass\n\n
class Command9(Command1, choice='123 456'):\n    pass\n\n
        """.rstrip()
        self.assert_strings_equal(expected, convert_script(Script(code)))

    # endregion

    # region Option names / name mode

    def test_option_names(self):
        converter = Converter.init_for_ast_callable(Script(prep_args("'--foo', '-'")).parsers[0].args[0], Mock(), 0)
        converter._counter = count()  # prevent potential interference from other tests
        attr_name_candidates = converter._attr_name_candidates()
        self.assertEqual('foo', next(attr_name_candidates))
        self.assertEqual('param_0', next(attr_name_candidates))
        self.assertEqual('param_1', next(attr_name_candidates))
        converter.__dict__['is_option'] = False
        self.assertEqual('param_2', next(converter._attr_name_candidates()))

    def test_option_attr_name_no_candidates(self):
        converter = Converter.init_for_ast_callable(Script(prep_args("'--foo'")).parsers[0].args[0], Mock(), 0)
        # Note: this would never actually happen
        with patch.object(ParamConverter, '_attr_name_candidates', return_value=()):
            with self.assertRaises(StopIteration):
                _ = converter._attr_name  # noqa

    def test_option_name_mode_default(self):
        self.assertEqual(prep_expected('foo_bar = Option()'), prep_and_convert("'--foo-bar'"))

    def test_option_name_mode_underscore(self):
        self.assertEqual(prep_expected('foo_bar = Option()', option_name_mode="'_'"), prep_and_convert("'--foo_bar'"))

    def test_option_name_mode_underscore_subparser(self):
        lines = [prep_args(), 'sp = p.add_subparsers()', "sp1 = sp.add_parser('one', help='Command one')"]
        code = '\n'.join(lines + ["sp1.add_argument('--foo_bar', '-f', action='store_true')"])
        exp_a = prep_expected('sub_cmd = SubCommand()', option_name_mode="'_'")
        exp_b = prep_cmd("foo_bar = Flag('-f')", name='One', base=CMD0, help="'Command one'")
        self.assert_strings_equal(f'{exp_a}\n\n\n{exp_b}', convert_script(Script(code)))

    # endregion

    # region Actions

    def test_bad_positional_action(self):
        with self.assertRaisesRegex(ConversionError, 'is not supported for Positional parameters'):
            prep_and_convert("'foo', action='store_true'")

    def test_bad_option_action(self):
        with self.assertRaisesRegex(ConversionError, 'is not supported for Option parameters'):
            prep_and_convert("'--foo', action='extend'")

    def test_explicit_option_action(self):
        self.assertEqual(prep_expected('foo = Option()'), prep_and_convert("'--foo', action='store'"))

    # endregion

    # region Param Groups

    def test_group_title_trim(self):
        code = prep_args() + '\n' + prep_group("'--foo'", title='Misc Options', description='Miscellaneous args')
        expected = prep_expected("with ParamGroup('Misc', description='Miscellaneous args'):", '    foo = Option()')
        self.assertEqual(expected, convert_script(Script(code)))

    def test_group_no_options_in_title(self):
        desc = 'Miscellaneous args'
        code = prep_args() + '\n' + prep_group("'foo', nargs=1", title='Misc Group', description=desc)
        expected = prep_expected(f"with ParamGroup('Misc Group', description='{desc}'):", '    foo = Positional()')
        self.assert_strings_equal(expected, convert_script(Script(code)))

    def test_space_between_groups(self):
        parts = (prep_args(), prep_group("'--foo'", title='A', var='a'), prep_group("'--bar'", title='B', var='b'))
        expected = prep_expected(
            "with ParamGroup('A'):", '    foo = Option()', '', "with ParamGroup('B'):", '    bar = Option()'
        )
        self.assertEqual(expected, convert_script(Script('\n'.join(parts))))

    def test_chained_mutually_exclusive_group_in_named_group(self):
        code = f"""{prep_args()}
group = p.add_argument_group('Exclusive Options').add_mutually_exclusive_group()
group.add_argument('--foo')"""
        expected = prep_expected(
            "with ParamGroup(description='Exclusive Options'):",
            '    with ParamGroup(mutually_exclusive=True):',
            '        foo = Option()',
        )
        self.assert_strings_equal(expected, convert_script(Script(code)))

    # endregion

    # region Param Converter

    def test_help_from_var(self):
        self.assertEqual(prep_expected('foo = Option(help=HELP)'), prep_and_convert("'--foo', help=HELP"))

    def test_help_strip_default(self):
        expected = prep_expected("foo = Option(help='The foo')")
        self.assertEqual(expected, prep_and_convert("'--foo', help='The foo (default: %(default)s)'"))

    def test_bad_param_type(self):
        with self.assertRaisesRegex(ConversionError, 'Unable to determine a suitable Parameter type'):
            prep_and_convert('')

    def test_param_order(self):
        expected = prep_expected('baz = Positional()', 'bar = Option()', 'foo = PassThru()', 'abc = Option()')
        converted = prep_and_convert("'--bar'", "'baz'", "'--foo', nargs=REMAINDER", "'--abc'", remainder=True)
        self.assert_strings_equal(expected, converted)

    def test_param_converter_misc(self):
        arg = Script(prep_args("'foo'")).parsers[0].args[0]
        converter = Converter.for_ast_callable(arg)(arg, Mock(), 1)  # noqa
        self.assertEqual(converter, converter)
        self.assertFalse(converter.use_auto_long_opt_str)  # noqa
        self.assertIsNone(converter._name_mode)  # noqa

    def test_pass_thru(self):
        expected = prep_expected('test = PassThru()')
        self.assert_strings_equal(expected, prep_and_convert("'test', nargs=REMAINDER", remainder=True))

    # endregion

    # region Positional Args

    def test_positional_nargs_non_literal(self):
        self.assert_strings_equal(prep_expected('foo = Positional(nargs=N)'), prep_and_convert("'foo', nargs=N"))

    def test_positional_nargs_gt_1(self):
        self.assert_strings_equal(prep_expected('foo = Positional(nargs=2)'), prep_and_convert("'foo', nargs=2"))

    def test_positional_nargs_append(self):
        expected = prep_expected('foo = Positional(nargs=2)')
        self.assert_strings_equal(expected, prep_and_convert("'foo', nargs=2, action='append'"))

    # endregion

    # region Option Args

    def test_option_append_nargs_default(self):
        expected = prep_expected("foo = Option(nargs='+')")
        self.assert_strings_equal(expected, prep_and_convert("'--foo', action='append'"))

    def test_option_append_nargs_set(self):
        expected = prep_expected('foo = Option(nargs=2)')
        self.assert_strings_equal(expected, prep_and_convert("'--foo', action='append', nargs=2"))

    def test_option_ignore_const(self):
        expected = prep_expected('foo = Option()')
        with self.assertLogs(f'{PACKAGE}.command_builder', 'WARNING'):
            self.assert_strings_equal(expected, prep_and_convert("'--foo', action='store', const='b'"))

    def test_option_store_nargs_default_value(self):
        self.assert_strings_equal(prep_expected('foo = Option()'), prep_and_convert("'--foo', action='store', nargs=1"))

    def test_option_nargs_star_to_plus(self):
        self.assert_strings_equal(prep_expected("foo = Option(nargs='+')"), prep_and_convert("'--foo', nargs='*'"))

    # endregion

    # region Flag Args

    def test_auto_flag_from_const(self):
        self.assert_strings_equal(prep_expected("foo = Flag(const='bar')"), prep_and_convert("'--foo', const='bar'"))

    def test_flag_store_non_standard_const(self):
        expected = prep_expected("foo = Flag(const='bar')")
        self.assert_strings_equal(expected, prep_and_convert("'--foo', action='store_const', const='bar'"))

    def test_flag_append_const(self):
        expected = prep_expected("foo = Flag(action='append_const', const='bar')")
        self.assert_strings_equal(expected, prep_and_convert("'--foo', action='append_const', const='bar'"))

    def test_flag_remove_redundant_default_true(self):
        expected = prep_expected('foo = Flag()')
        self.assert_strings_equal(expected, prep_and_convert("'--foo', action='store_true', default=False"))

    def test_flag_remove_redundant_default_false(self):
        expected = prep_expected('foo = Flag(default=True)')
        self.assert_strings_equal(expected, prep_and_convert("'--foo', action='store_false', default=True"))

    def test_flag_store_false(self):
        expected = prep_expected('foo = Flag(default=True)')
        self.assert_strings_equal(expected, prep_and_convert("'--foo', action='store_false'"))

    def test_negative_flag_with_dest(self):
        expected = prep_expected("bar = Flag('--foo', '-f', default=True)")
        self.assert_strings_equal(expected, prep_and_convert("'--foo', '-f', dest='bar', action='store_false'"))

    def test_positive_flag_with_dest(self):
        expected = prep_expected("bar = Flag('--foo', '-f')")
        self.assert_strings_equal(expected, prep_and_convert("'--foo', '-f', dest='bar', action='store_true'"))

    # endregion

    # region Add Methods

    def test_add_methods_base_cmd_both(self):
        p = '    pass'
        expected = prep_expected('foo = Option()', '', 'def _init_command_(self):', p, '', 'def main(self):', p)
        self.assert_strings_equal(expected, prep_and_convert("'--foo'", add_methods=True))

    def test_add_methods_base_cmd_no_args_both(self):
        expected = prep_expected('def _init_command_(self):', '    pass', '', 'def main(self):', '    pass')
        self.assert_strings_equal(expected, prep_and_convert(add_methods=True))

    def test_add_methods_split_across_subparsers(self):
        code = prep_args() + "\nsps = p.add_subparsers()\nsp = sps.add_parser('foo')"
        cmds = [
            prep_expected('sub_cmd = SubCommand()', '', 'def _init_command_(self):', '    pass'),
            prep_cmd('def main(self):', '    pass', name='Foo', base=CMD0),
        ]
        self.assert_strings_equal('\n\n\n'.join(cmds), convert_script(Script(code), add_methods=True))

    def test_add_methods_no_methods(self):
        converter = Converter.init_for_ast_callable(Script(prep_args()).parsers[0], add_methods=True)
        # This is unlikely to occur
        converter.__dict__.update(is_sub_parser=True, sub_parser_converters=1)
        self.assertEqual(['    pass'], list(converter.finalize(False, '')))

    # endregion


class AstUtilsTest(ParserTest):
    def test_utils_bad_types(self):
        with self.assertRaises(TypeError):
            get_name_repr('foo')  # noqa
        with self.assertRaises(TypeError):
            collection_contents('foo')  # noqa

    def test_get_name_repr_call(self):
        node = ast.parse('foo()').body[0]
        self.assertEqual('foo', get_name_repr(node.value))  # noqa # Tests the isinstance(node, Call) line
        self.assertEqual('foo()', get_name_repr(node))      # noqa # Tests the isinstance(node, AST) line


class AstCallableTest(ParserTest):
    def test_ast_callable_no_represents(self):
        ac = AstCallable(ast.parse('foo(123, bar=456)').body[0].value, Mock(), {})  # noqa
        self.assertEqual(['123'], ac.init_func_args)
        self.assertEqual({'bar': '456'}, ac.init_func_kwargs)

    def test_converter_for_ast_callable_error(self):
        ac = AstCallable(ast.parse('foo(123, bar=456)').body[0].value, Mock(), {})  # noqa
        with self.assertRaises(TypeError):
            Converter.for_ast_callable(ac)

    def test_pprint(self):
        code = "import argparse\np = argparse.ArgumentParser()\ng = p.add_argument_group()\ng.add_argument('--foo')\n"
        expected = """
 + <AstArgumentParser[sub_parsers=0]: ``argparse.ArgumentParser()``>:
    + <ArgGroup: ``p.add_argument_group()``>:
       - <ParserArg[g.add_argument('--foo')]>
       """.strip()
        with RedirectStreams() as streams:
            Script(code).parsers[0].pprint()
        self.assert_strings_equal(expected, streams.stdout.strip())

    # region Low value tests for coverage

    def test_argparse_typing_helpers(self):
        parser = ArgumentParser()
        parser.register('action', 'parsers', SubParsersAction)
        sp_action = parser.add_subparsers(dest='action', prog='')
        self.assertIsInstance(sp_action, SubParsersAction)
        sub_parser = sp_action.add_parser('test')
        self.assertIsNotNone(sub_parser.add_mutually_exclusive_group())
        self.assertIsNotNone(sub_parser.add_argument_group('test'))

    def test_script_reprs(self):
        self.assertEqual('<Script[parsers=0]>', repr(Script('foo()')))

    def test_group_and_arg_reprs(self):
        code = "import argparse\np = argparse.ArgumentParser()\ng = p.add_argument_group()\ng.add_argument('--foo')\n"
        parser = Script(code).parsers[0]
        group = parser.groups[0]
        self.assertIn('p.add_argument_group()', repr(group))
        self.assertIn("g.add_argument('--foo')", repr(group.args[0]))

    def test_descriptors(self):
        mock = Mock()

        class Foo:
            foo = AddVisitedChild(Mock, 'abc')

            @classmethod
            def _add_visit_func(cls, name):
                return False

            @visit_func
            def bar(self):
                return 123

        Foo.baz = visit_func(mock)
        self.assertEqual(123, Foo().bar())
        self.assertIsInstance(Foo().baz(), Mock)  # noqa
        mock.assert_called()
        self.assertIsInstance(Foo.foo, AddVisitedChild)

    def test_add_visit_func_attr_error(self):
        original = AstCallable.visit_funcs.copy()
        self.assertTrue(AstCallable._add_visit_func('foo_bar'))
        self.assertNotEqual(original, AstCallable.visit_funcs)
        self.assertIn('foo_bar', AstCallable.visit_funcs)
        AstCallable.visit_funcs = original

    def test_ast_callable_misc(self):
        ac = AstCallable(Mock(args=123, keywords=456), Mock(), {})
        self.assertEqual(123, ac.call_args)
        self.assertIsNone(ac.get_tracked_refs('foo', 'bar', None))
        with self.assertRaises(KeyError):
            self.assertIsNone(ac.get_tracked_refs('foo', 'bar'))

    def test_top_level_parser_no_choices(self):
        key, val = Converter.init_for_ast_callable(Script(prep_args()).parsers[0])._choices
        self.assertTrue(key is val is None)

    # endregion


class AstVisitorTest(ParserTest):
    def test_touch_unhandled_cases_for_coverage(self):
        code = """
from logging import getLogger
from argparse import Namespace, ArgumentParser as AP
log = getLogger(__name__)
def foo():
    for k, v in {}.items():
        pass
    for t in some_iterable:
        pass
with foo():
    a = int
    b = {'a': 1}['a']
p = AP()
        """
        self.assertEqual(1, len(Script(code).parsers))

    def test_tracked_ref(self):
        a, b = TrackedRef('foo.bar'), TrackedRef('foo.baz')
        self.assertEqual('<TrackedRef: foo.bar>', repr(a))
        self.assertIn(a, {a, b})
        self.assertNotIn(a, {b})
        self.assertEqual(a, TrackedRef('foo.bar'))

    def test_with_no_as_name(self):
        self.assertEqual(1, len(Script('from argparse import ArgumentParser as AP\nwith AP():\n    pass').parsers))

    def test_resolve_ref_no_visit_func(self):
        class FakeRef:
            def __init__(self, module, name):
                self.module, self.name = module, name

        ref = FakeRef('foo', 'bar')
        visitor = ScriptVisitor()
        visitor.track_refs_to(ref)  # noqa
        visitor.scopes['foo'] = ref
        self.assertIsNone(visitor.resolve_ref('foo.bar'))

    def test_for_multiple_parser_parents(self):
        code = prep_args() + "\ns = p.add_subparsers()\na = s.add_parser('f')\nb = AP()\nfor x in (a, b):\n    pass"
        self.assertEqual(2, len(Script(code).parsers))

    def test_for_no_subparsers(self):
        code = 'from argparse import ArgumentParser as AP\np1 = AP()\np2 = AP()\nfor p in (p1, p2):\n    pass'
        self.assertEqual(2, len(Script(code).parsers))

    def test_extra_import_and_def_in_func(self):
        code = """import logging\nfrom argparse import ArgumentParser\nlog = logging.getLogger(__name__)
def main():\n    parser = ArgumentParser()\n    parser.add_argument('test')"""
        self.assertEqual(prep_expected('test = Positional()'), convert_script(Script(code)))


class ArgparseConversionCustomSubclassTest(ParserTest):
    @classmethod
    def _prepare_test_classes(cls):
        class ArgParser(ArgumentParser):
            @property
            def subparsers(self):
                try:
                    return {sp.dest: sp for sp in self._subparsers._group_actions}
                except AttributeError:
                    return {}

            def add_subparser(self, dest, name, help_desc=None, *, help=None, description=None, **kwargs):  # noqa
                try:
                    sp_group = self.subparsers[dest]
                except KeyError:
                    sp_group = self.add_subparsers(dest=dest, title='subcommands')
                return sp_group.add_parser(name, help=help or help_desc, description=description or help_desc, **kwargs)

            def add_constant(self, key, value):
                pass

        class ParserConstant(AstCallable, represents=ArgParser.add_constant):
            parent: AstArgParser

        class AstArgParser(AstArgumentParser, represents=ArgParser, children=('constants',)):
            add_constant = AddVisitedChild(ParserConstant, 'constants')

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.constants = []

            @visit_func
            def add_subparser(self, node: InitNode, call: ast.Call, tracked_refs: TrackedRefMap):
                return self._add_subparser(node, call, tracked_refs, SubParserShortcut)

            def grouped_children(self):
                yield ParserConstant, self.constants
                yield from super().grouped_children()

        class SubParserShortcut(AstArgParser, represents=ArgParser.add_subparser):
            @cached_property
            def init_func_kwargs(self) -> dict[str, str]:
                kwargs = self._init_func_kwargs()
                help_desc = kwargs.get('help_desc')
                if help_desc and kwargs.setdefault('help', help_desc) != help_desc:
                    kwargs.setdefault('description', help_desc)
                return kwargs

        class ConstantConverter(Converter, converts=ParserConstant):
            def format_lines(self, indent: int = 4):
                try:
                    key, val = self.ast_obj.init_func_args
                except ValueError:
                    pass
                else:
                    yield f'{" " * indent}{ast.literal_eval(key)} = {val}'

        return ArgParser, AstArgParser, SubParserShortcut, ConstantConverter

    @classmethod
    def setUpClass(cls):
        ArgParser, AstArgParser, SubParserShortcut, ConstantConverter = cls._prepare_test_classes()

        class Module:
            def __init__(self, data):
                self.__dict__.update(data)

        modules = {'foo': Module({'ArgParser': ArgParser}), 'foo.bar': Module({'ArgParser': ArgParser})}
        with patch(f'{PACKAGE}.argparse_ast.sys.modules', modules):
            Script._register_parser('foo.bar.baz', 'ArgParser', AstArgParser)

    @classmethod
    def tearDownClass(cls):
        ac_converter_map = Converter._ac_converter_map
        del ac_converter_map[next(ac for ac in ac_converter_map if ac.__name__ == 'ParserConstant')]
        for module in ('foo', 'foo.bar', 'foo.bar.baz'):
            del Script._parser_classes[module]

    def test_custom_parser_subclass(self):
        code = """
from argparse import SUPPRESS as hide
from foo.bar import ArgParser
parser = ArgParser(description='Parse args')
parser.add_constant('abc', 123)
with parser.add_subparser('action', 'one') as sp1:
    sp1.add_argument('--foo', help=hide)
sp2 = parser.add_subparser('action', 'two')
        """
        cmds = [
            prep_expected('abc = 123', 'action = SubCommand()', description="'Parse args'"),
            prep_cmd('foo = Option(hide=True)', name='One', base=CMD0),
            prep_cmd('pass', name='Two', base=CMD0),
        ]
        self.assert_strings_equal('\n\n\n'.join(cmds), convert_script(Script(code)))

    def test_converter_for_ast_callable_subclass(self):
        code = "from foo import ArgParser\np = ArgParser()\nsp = p.add_subparser(name='one')\nsp.add_argument('--foo')"
        self.assertEqual(Converter.for_ast_callable(Script(code).parsers[0]), ParserConverter)


if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(name)s %(lineno)d %(message)s')
    try:
        main(verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
