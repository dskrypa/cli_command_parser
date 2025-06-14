#!/usr/bin/env python

from pathlib import Path
from unittest import main

from cli_command_parser import Command, Context
from cli_command_parser.documentation import load_commands, render_command_rst, render_script_rst, top_level_commands
from cli_command_parser.testing import ParserTest, get_help_text, get_usage_text, load_command

THIS_FILE = Path(__file__).resolve()
EXAMPLES_DIR = THIS_FILE.parents[2].joinpath('examples')
TEST_DATA_DIR = THIS_FILE.parents[1].joinpath('data', 'test_examples_documentation')


def load_expected(name: str) -> str:
    return TEST_DATA_DIR.joinpath(name).read_text('utf-8').rstrip()


class ExampleHelpTest(ParserTest):
    def test_advanced_subcommand(self):
        with load_command(EXAMPLES_DIR, 'advanced_subcommand.py', 'Base') as Base:
            for args in ('foo', 'run foo'):
                expected = f'usage: advanced_subcommand.py {args} [--verbose [VERBOSE]] [--help]'
                with self.subTest(args=args):
                    self.assert_str_starts_with_line(expected, get_help_text(Base.parse(args.split())))

    def test_common_group_shown(self):
        with load_command(EXAMPLES_DIR, 'rest_api_wrapper.py', 'ApiWrapper') as ApiWrapper:
            for sub_cmd in ('show', 'find'):
                expected = load_expected(f'rest_api_wrapper__{sub_cmd}.txt')
                with self.subTest(sub_cmd=sub_cmd):
                    cmd = ApiWrapper.parse([sub_cmd, '-h'])
                    self.assert_strings_equal(expected, get_help_text(cmd).rstrip())

    def test_example_help_texts(self):
        cases = [
            ('echo.py', 'Echo', 'echo_help.txt'),
            ('simple_flags.py', 'Example', 'simple_flags_help.txt'),
            ('custom_inputs.py', 'InputsExample', 'custom_inputs_help.txt'),
            ('complex', 'Update', 'complex_update_help.txt'),
        ]
        for file_name, cmd_name, expected_file_name in cases:
            with self.subTest(file=file_name, command=cmd_name):
                with load_command(EXAMPLES_DIR, file_name, cmd_name) as command:
                    expected = load_expected(expected_file_name)
                    self.assert_strings_equal(expected, get_help_text(command()).rstrip())

    def test_wrapped_usage(self):
        expected = """\
usage: custom_inputs.py [--path PATH]
    [--in-file IN_FILE] [--out-file OUT_FILE]
    [--json JSON] [--simple-range {0 <= N <= 49}]
    [--skip-range {1 <= N <= 29, step=2}]
    [--float-range {0.0 <= N < 1.0}]
    [--choice-range {0 <= N <= 19}] [--help]"""
        with load_command(EXAMPLES_DIR, 'custom_inputs.py', 'InputsExample', config={'wrap_usage_str': 50}) as command:
            self.assert_strings_equal(expected, get_usage_text(command))


class ExampleRstFormatTest(ParserTest):
    def test_examples_shared_logging_init(self):
        expected = TEST_DATA_DIR.joinpath('shared_logging_init.rst').read_text('utf-8')
        commands = load_commands(EXAMPLES_DIR.joinpath('shared_logging_init.py'))
        self.assertSetEqual({'Base', 'Show'}, set(commands))
        self.assertSetEqual({'Base'}, set(top_level_commands(commands)))
        with self.subTest(fix_name=True):
            self.assert_strings_equal(expected, render_command_rst(commands['Base']))

        with self.subTest(fix_name=False):
            rendered = render_command_rst(commands['Base'], fix_name=False)
            self.assertTrue(rendered.startswith('shared_logging_init\n*******************\n'))

    def test_examples_advanced_subcommand(self):
        commands = load_commands(EXAMPLES_DIR.joinpath('advanced_subcommand.py'))
        self.assertSetEqual({'Base', 'Foo', 'Bar', 'Baz'}, set(commands))
        self.assertSetEqual({'Base'}, set(top_level_commands(commands)))

    def _test_example_rst_texts(self):
        cases = [
            ('action_with_args.py', 'Example', 'action_with_args.rst'),
            ('hello_world.py', 'HelloWorld', 'hello_world.rst'),
            ('advanced_subcommand.py', 'Base', 'advanced_subcommand.rst'),
            ('complex', 'Example', 'complex__all.rst'),
        ]
        for file_name, cmd_name, expected_file_name in cases:
            with self.subTest(file=file_name, command=cmd_name):
                expected = load_expected(expected_file_name)
                path = EXAMPLES_DIR.joinpath(file_name)
                with Context.for_prog(path):
                    rendered = render_script_rst(path)
                    self.assert_strings_equal(expected, rendered.rstrip())

    def test_example_rst_texts_no_ctx(self):
        self._test_example_rst_texts()

    def test_example_rst_texts_with_ctx(self):
        class DocBuilder(Command):
            pass

        with Context([], DocBuilder):
            self._test_example_rst_texts()

    def test_wrapped_usage(self):
        InputsExample = next(iter(load_commands(EXAMPLES_DIR.joinpath('custom_inputs.py')).values()))

        class Inputs(InputsExample, wrap_usage_str=55, prog='custom_inputs.py'):
            pass

        self.assert_strings_equal(load_expected('custom_inputs.rst'), render_command_rst(Inputs).rstrip())

    def test_nested_subcommands_limited_depths(self):
        Example = next(iter(load_commands(EXAMPLES_DIR.joinpath('complex')).values()))
        for depth in (0, 1):
            with self.subTest(depth=depth):
                Command.__class__.config(Example).sub_cmd_doc_depth = depth
                expected = load_expected(f'complex__depth_{depth}.rst')
                self.assert_strings_equal(expected, render_command_rst(Example).rstrip())


if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    try:
        main(verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
