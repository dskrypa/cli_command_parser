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
DISCLAIMER = '# This is an automatically generated name that should probably be updated'
IMPORT_LINE = (
    'from cli_command_parser import Command, SubCommand, ParamGroup, Positional, Option, Flag, Counter, PassThru, main'
)


class ArgparseConversionTest(ParserTest):
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
        parser = Script('from argparse import ArgumentParser as AP\np = AP()').parsers[0]
        key, val = Converter.for_ast_callable(parser)(parser)._choices  # noqa
        self.assertTrue(key is val is None)

    # endregion

    # region get_name_repr & collection_contents

    def test_utils_bad_types(self):
        with self.assertRaises(TypeError):
            get_name_repr('foo')  # noqa
        with self.assertRaises(TypeError):
            collection_contents('foo')  # noqa

    def test_get_name_repr_call(self):
        node = ast.parse('foo()').body[0]
        self.assertEqual('foo', get_name_repr(node.value))  # noqa # Tests the isinstance(node, Call) line
        self.assertEqual('foo()', get_name_repr(node))      # noqa # Tests the isinstance(node, AST) line

    # endregion

    def test_ast_callable_no_represents(self):
        ac = AstCallable(ast.parse('foo(123, bar=456)').body[0].value, Mock(), {})  # noqa
        self.assertEqual(['123'], ac.init_func_args)
        self.assertEqual({'bar': '456'}, ac.init_func_kwargs)

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

    def test_renamed_import_and_remainder_in_func(self):
        code = """
import logging
from argparse import ArgumentParser as ArgParser, REMAINDER
log = logging.getLogger(__name__)
def main():
    parser = ArgParser()
    parser.add_argument('test', nargs=REMAINDER)
        """
        expected = f'{IMPORT_LINE}\n\n\nclass Command0(Command):  {DISCLAIMER}\n    test = PassThru()'
        self.assertEqual(expected, convert_script(Script(code)))

    def test_sub_parser_args_in_loop(self):
        code = """
import argparse
parser = argparse.ArgumentParser()
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

        expected_base = f'{IMPORT_LINE}\n\n\nclass Command0(Command):  {DISCLAIMER}\n    action = SubCommand()'
        common = """
    with ParamGroup(description='Common options'):
        verbose = Counter('-v', help='Increase logging verbosity')
        dry_run = Flag('-D', help='Perform a dry run with no side effects')
        """.rstrip()

        expected_smart = f"""{expected_base}\n{common}\n\n
class One(Command0, help='Command one'):
    foo_bar = Flag('-f', help='Do foo bar')\n\n
class Two(Command0, description='Command two'):
    baz = Option('-b', nargs='+', help='What to baz')
        """.rstrip()
        with self.subTest(smart_loop_handling=True):
            self.assert_strings_equal(expected_smart, convert_script(Script(code)))

        expected_split = f"""{expected_base}\n\n
class One(Command0, help='Command one'):
    foo_bar = Flag('-f', help='Do foo bar')
{common}\n\n
class Two(Command0, description='Command two'):
    baz = Option('-b', nargs='+', help='What to baz')
{common}
        """.rstrip()
        with self.subTest(smart_loop_handling=False):
            self.assert_strings_equal(expected_split, convert_script(Script(code, False)))

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
        expected = f"""{IMPORT_LINE}\n\n
class Command0(Command):  {DISCLAIMER}
    foo = Positional()
    action = SubCommand()
\n
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

    def test_converter_for_ast_callable_error(self):
        ac = AstCallable(ast.parse('foo(123, bar=456)').body[0].value, Mock(), {})  # noqa
        with self.assertRaises(TypeError):
            Converter.for_ast_callable(ac)

    def test_parser_add_help(self):
        code = 'from argparse import ArgumentParser as AP\np1 = AP(add_help=False)\np2 = AP(add_help=True)\n'
        expected = f"""{IMPORT_LINE}\n\n
class Command0(Command, add_help=False):  {DISCLAIMER}\n    pass\n\n
class Command1(Command):  {DISCLAIMER}\n    pass\n\n
        """.rstrip()
        self.assert_strings_equal(expected, convert_script(Script(code)))

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
        """.rstrip()
        self.assert_strings_equal(expected, convert_script(Script(code)))

    # region Option names / name mode

    def test_option_names(self):
        parser = Script("from argparse import ArgumentParser as AP\np = AP(); p.add_argument('--foo', '-')").parsers[0]
        converter = Converter.for_ast_callable(parser.args[0])(parser.args[0], Mock(), 0)  # noqa
        converter._counter = count()  # prevent potential interference from other tests
        attr_name_candidates = converter._attr_name_candidates()  # noqa
        self.assertEqual('foo', next(attr_name_candidates))
        self.assertEqual('param_0', next(attr_name_candidates))
        self.assertEqual('param_1', next(attr_name_candidates))
        converter.__dict__['is_option'] = False
        self.assertEqual('param_2', next(converter._attr_name_candidates()))  # noqa
        with patch.object(ParamConverter, '_attr_name_candidates', return_value=()):
            with self.assertRaises(StopIteration):
                _ = converter._attr_name  # noqa

    def test_option_name_mode_default(self):
        code = "from argparse import ArgumentParser as AP\np = AP(); p.add_argument('--foo-bar')"
        expected = f'{IMPORT_LINE}\n\n\nclass Command0(Command):  {DISCLAIMER}\n    foo_bar = Option()'
        self.assertEqual(expected, convert_script(Script(code)))

    def test_option_name_mode_underscore(self):
        code = "from argparse import ArgumentParser as AP\np = AP(); p.add_argument('--foo_bar')"
        expected = (
            f"{IMPORT_LINE}\n\n\nclass Command0(Command, option_name_mode='_'):  {DISCLAIMER}"
            '\n    foo_bar = Option()'
        )
        self.assertEqual(expected, convert_script(Script(code)))

    def test_option_name_mode_underscore_subparser(self):
        code = """
from argparse import ArgumentParser as AP\np = AP()\nsp = p.add_subparsers()\n
sp1 = sp.add_parser('one', help='Command one')\nsp1.add_argument('--foo_bar', '-f', action='store_true')
        """
        expected = f"""{IMPORT_LINE}\n\n
class Command0(Command, option_name_mode='_'):  {DISCLAIMER}\n    sub_cmd = SubCommand()\n\n
class One(Command0, help='Command one'):\n    foo_bar = Flag('-f')
        """.rstrip()
        self.assert_strings_equal(expected, convert_script(Script(code)))

    # endregion

    # region Actions

    def test_bad_positional_action(self):
        code = "from argparse import ArgumentParser as AP\np = AP(); p.add_argument('foo', action='store_true')"
        with self.assertRaisesRegex(ConversionError, 'is not supported for Positional parameters'):
            convert_script(Script(code))

    def test_bad_option_action(self):
        code = "from argparse import ArgumentParser as AP\np = AP(); p.add_argument('--foo', action='extend')"
        with self.assertRaisesRegex(ConversionError, 'is not supported for Option parameters'):
            convert_script(Script(code))

    def test_explicit_option_action(self):
        code = "from argparse import ArgumentParser as AP\np = AP(); p.add_argument('--foo', action='store')"
        expected = f'{IMPORT_LINE}\n\n\nclass Command0(Command):  {DISCLAIMER}\n    foo = Option()'
        self.assertEqual(expected, convert_script(Script(code)))

    # endregion

    def test_help_from_var(self):
        code = "from argparse import ArgumentParser as AP\np = AP(); p.add_argument('--foo', help=HELP)"
        expected = f'{IMPORT_LINE}\n\n\nclass Command0(Command):  {DISCLAIMER}\n    foo = Option(help=HELP)'
        self.assertEqual(expected, convert_script(Script(code)))

    def test_help_strip_default(self):
        text = 'The foo (default: %(default)s)'
        code = f"from argparse import ArgumentParser as AP\np = AP(); p.add_argument('--foo', help={text!r})"
        expected = f"{IMPORT_LINE}\n\n\nclass Command0(Command):  {DISCLAIMER}\n    foo = Option(help='The foo')"
        self.assertEqual(expected, convert_script(Script(code)))

    def test_group_title_trim(self):
        code = """from argparse import ArgumentParser as AP\np = AP()
g = p.add_argument_group(title='Misc Options', description='Miscellaneous option group')
g.add_argument('--foo')
        """
        expected = f"""{IMPORT_LINE}\n\n\nclass Command0(Command):  {DISCLAIMER}
    with ParamGroup('Misc', description='Miscellaneous option group'):
        foo = Option()
        """.rstrip()
        self.assertEqual(expected, convert_script(Script(code)))

    def test_group_no_options_in_title(self):
        code = """from argparse import ArgumentParser as AP\np = AP()
g = p.add_argument_group(title='Misc Group', description='Miscellaneous option group')
g.add_argument('foo', nargs=1)
        """
        expected = f"""{IMPORT_LINE}\n\n\nclass Command0(Command):  {DISCLAIMER}
    with ParamGroup('Misc Group', description='Miscellaneous option group'):
        foo = Positional()
        """.rstrip()
        self.assert_strings_equal(expected, convert_script(Script(code)))

    # region Param Converter

    def test_bad_param_type(self):
        code = 'from argparse import ArgumentParser as AP\np = AP(); p.add_argument()'
        with self.assertRaisesRegex(ConversionError, 'Unable to determine a suitable Parameter type'):
            convert_script(Script(code))

    def test_param_order(self):
        code = """from argparse import REMAINDER, ArgumentParser as AP\np = AP()
p.add_argument('--bar')\np.add_argument('baz')\np.add_argument('--foo', nargs=REMAINDER)\np.add_argument('--abc')
        """
        expected = f"""{IMPORT_LINE}\n\n\nclass Command0(Command):  {DISCLAIMER}
    baz = Positional()\n    bar = Option()\n    foo = PassThru()\n    abc = Option()\n
        """.rstrip()
        self.assert_strings_equal(expected, convert_script(Script(code)))

    def test_param_converter_misc(self):
        code = "from argparse import ArgumentParser as AP\np = AP()\np.add_argument('foo')"
        arg = Script(code).parsers[0].args[0]
        converter = Converter.for_ast_callable(arg)(arg, Mock(), 1)  # noqa
        self.assertEqual(converter, converter)
        self.assertFalse(converter.use_auto_long_opt_str)  # noqa
        self.assertIsNone(converter._name_mode)  # noqa

    # endregion

    # region Positional Args

    def test_positional_nargs_non_literal(self):
        code = "from argparse import ArgumentParser as AP\np = AP()\np.add_argument('foo', nargs=N)"
        expected = f'{IMPORT_LINE}\n\n\nclass Command0(Command):  {DISCLAIMER}\n    foo = Positional(nargs=N)'
        self.assert_strings_equal(expected, convert_script(Script(code)))

    def test_positional_nargs_gt_1(self):
        code = "from argparse import ArgumentParser as AP\np = AP()\np.add_argument('foo', nargs=2)"
        expected = f'{IMPORT_LINE}\n\n\nclass Command0(Command):  {DISCLAIMER}\n    foo = Positional(nargs=2)'
        self.assert_strings_equal(expected, convert_script(Script(code)))

    def test_positional_nargs_append(self):
        code = "from argparse import ArgumentParser as AP\np = AP()\np.add_argument('foo', nargs=2, action='append')"
        expected = f'{IMPORT_LINE}\n\n\nclass Command0(Command):  {DISCLAIMER}\n    foo = Positional(nargs=2)'
        self.assert_strings_equal(expected, convert_script(Script(code)))

    # endregion

    # region Option Args

    def test_option_append_nargs_default(self):
        code = "from argparse import ArgumentParser as AP\np = AP()\np.add_argument('--foo', action='append')"
        expected = f"{IMPORT_LINE}\n\n\nclass Command0(Command):  {DISCLAIMER}\n    foo = Option(nargs='+')"
        self.assert_strings_equal(expected, convert_script(Script(code)))

    def test_option_append_nargs_set(self):
        code = "from argparse import ArgumentParser as AP\np = AP()\np.add_argument('--foo', action='append', nargs=2)"
        expected = f'{IMPORT_LINE}\n\n\nclass Command0(Command):  {DISCLAIMER}\n    foo = Option(nargs=2)'
        self.assert_strings_equal(expected, convert_script(Script(code)))

    def test_option_ignore_const(self):
        code = "from argparse import ArgumentParser as AP\np = AP()\np.add_argument('--foo', action='store', const='b')"
        expected = f'{IMPORT_LINE}\n\n\nclass Command0(Command):  {DISCLAIMER}\n    foo = Option()'
        with self.assertLogs(f'{PACKAGE}.command_builder', 'WARNING'):
            self.assert_strings_equal(expected, convert_script(Script(code)))

    def test_option_store_nargs_default_value(self):
        code = "from argparse import ArgumentParser as AP\np = AP()\np.add_argument('--foo', action='store', nargs=1)"
        expected = f'{IMPORT_LINE}\n\n\nclass Command0(Command):  {DISCLAIMER}\n    foo = Option()'
        self.assert_strings_equal(expected, convert_script(Script(code)))

    def test_option_nargs_star_to_plus(self):
        code = "from argparse import ArgumentParser as AP\np = AP()\np.add_argument('--foo', nargs='*')"
        expected = f"{IMPORT_LINE}\n\n\nclass Command0(Command):  {DISCLAIMER}\n    foo = Option(nargs='+')"
        self.assert_strings_equal(expected, convert_script(Script(code)))

    # endregion

    # region Flag Args

    def test_auto_flag_from_const(self):
        code = "from argparse import ArgumentParser as AP\np = AP()\np.add_argument('--foo', const='bar')"
        expected = f"{IMPORT_LINE}\n\n\nclass Command0(Command):  {DISCLAIMER}\n    foo = Flag(const='bar')"
        self.assert_strings_equal(expected, convert_script(Script(code)))

    def test_flag_store_non_standard_const(self):
        code = """from argparse import ArgumentParser as AP\np = AP()
p.add_argument('--foo', action='store_const', const='bar')"""
        expected = f"{IMPORT_LINE}\n\n\nclass Command0(Command):  {DISCLAIMER}\n    foo = Flag(const='bar')"
        self.assert_strings_equal(expected, convert_script(Script(code)))

    def test_flag_append_const(self):
        code = """from argparse import ArgumentParser as AP\np = AP()
p.add_argument('--foo', action='append_const', const='bar')"""
        expected = f"""{IMPORT_LINE}\n\n\nclass Command0(Command):  {DISCLAIMER}
    foo = Flag(action='append_const', const='bar')"""
        self.assert_strings_equal(expected, convert_script(Script(code)))

    def test_flag_remove_redundant_default(self):
        code = """from argparse import ArgumentParser as AP\np = AP()
p.add_argument('--foo', action='store_true', default=False)"""
        expected = f'{IMPORT_LINE}\n\n\nclass Command0(Command):  {DISCLAIMER}\n    foo = Flag()'
        self.assert_strings_equal(expected, convert_script(Script(code)))

    # endregion


class AstVisitorTest(ParserTest):
    def test_touch_for_unhandled_cases(self):
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
        code = """
from argparse import ArgumentParser as AP\np1 = AP()\nsp = p1.add_subparsers()\nsp1 = sp.add_parser('foo')\n
p2 = AP()\nfor p in (sp1, p2):\n    pass
        """
        self.assertEqual(2, len(Script(code).parsers))

    def test_for_no_subparsers(self):
        code = 'from argparse import ArgumentParser as AP\np1 = AP()\np2 = AP()\nfor p in (p1, p2):\n    pass'
        self.assertEqual(2, len(Script(code).parsers))


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
        expected = f"""{IMPORT_LINE}\n\n
class Command0(Command, description='Parse args'):  {DISCLAIMER}
    abc = 123
    action = SubCommand()
\n
class One(Command0):
    foo = Option(hide=True)
\n
class Two(Command0):
    pass
        """.rstrip()
        self.assert_strings_equal(expected, convert_script(Script(code)))

    def test_converter_for_ast_callable_subclass(self):
        code = "from foo import ArgParser\np = ArgParser()\nsp = p.add_subparser(name='one')\nsp.add_argument('--foo')"
        parser = Script(code).parsers[0]
        converter_cls = Converter.for_ast_callable(parser)
        self.assertEqual(converter_cls, ParserConverter)


if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(name)s %(lineno)d %(message)s')
    try:
        main(verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
