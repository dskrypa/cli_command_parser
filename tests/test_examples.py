#!/usr/bin/env python

import sys
from functools import reduce
from operator import xor
from pathlib import Path
from subprocess import Popen, PIPE
from unittest import TestCase, TestSuite as _TestSuite, main

EXAMPLES_DIR = Path(__file__).resolve().parents[1].joinpath('examples')

# region Test Setup

WORKERS = 8

try:
    from testtools import ConcurrentTestSuite, iterate_tests
except ImportError:
    pass  # This is only used to improve run time when testing locally; they are not essential
else:

    def load_tests(loader, suite, pattern):
        """
        Called by unittest both when invoked via main and via ``coverage run -m unittest``, but not via pytest.  Returns a
        testtools.ConcurrentTestSuite to run the above methods in parallel instead of in series.
        """
        suites = []
        tests = list(iterate_tests(suite))
        chunk_size, remaining = divmod(len(tests), WORKERS)
        i = 0
        for c in range(WORKERS):
            j = i + chunk_size + (1 if remaining > 0 else 0)
            remaining -= 1
            suites.append(HashableSuite(tests[i:j]))
            i = j

        return ConcurrentTestSuite(suite, lambda s: suites)


class HashableSuite(_TestSuite):
    # This is needed to make testtools.ConcurrentTestSuite work properly
    def __init__(self, tests=()):
        super().__init__(tests)
        self.__tests = list(self)

    def __hash__(self):
        return reduce(xor, map(hash, (self.__class__, *self.__tests)))

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.__tests == other.__tests


# endregion


class ExampleScriptTest(TestCase):
    _path: str = None

    def __init_subclass__(cls, file: str, **kwargs):  # noqa
        super().__init_subclass__(**kwargs)
        cls._path = EXAMPLES_DIR.joinpath(file).as_posix()

    def call_script(self, *args) -> tuple[int, str, str]:
        proc = Popen([sys.executable, self._path, *args], text=True, stdout=PIPE, stderr=PIPE)
        stdout, stderr = proc.communicate()
        return proc.wait(), stdout, stderr

    def assertLinesStartWith(self, prefix: str, text: str):
        first_line = text.splitlines()[0]
        self.assertEqual(prefix, first_line)


class ActionWithArgsTest(ExampleScriptTest, file='action_with_args.py'):
    def test_no_args(self):
        code, stdout, stderr = self.call_script()
        self.assertEqual(code, 2)
        self.assertEqual(stderr, 'argument {echo,split}: missing required argument value\n')

    def test_help(self):
        code, stdout, stderr = self.call_script('-h')
        self.assertEqual(code, 0)
        self.assertLinesStartWith('usage: action_with_args.py {echo,split} TEXT [--help]', stdout)

    def test_echo(self):
        code, stdout, stderr = self.call_script('echo', 'test', 'one')
        self.assertEqual(code, 0)
        self.assertEqual(stdout, 'test one\n')

    def test_split(self):
        code, stdout, stderr = self.call_script('split', 'test', 'one')
        self.assertEqual(code, 0)
        self.assertEqual(stdout, 'test\none\n')

    def test_echo_no_args(self):
        code, stdout, stderr = self.call_script('echo')
        self.assertEqual(code, 2)
        self.assertEqual(stderr, 'argument TEXT [TEXT ...]: missing required argument value\n')


class SharedLoggingInitTest(ExampleScriptTest, file='shared_logging_init.py'):
    def test_no_args(self):
        code, stdout, stderr = self.call_script()
        self.assertEqual(code, 2)
        self.assertEqual(stderr, 'argument {show}: missing required argument value\n')

    def test_help(self):
        code, stdout, stderr = self.call_script('--help')
        self.assertEqual(code, 0)
        expected = 'usage: shared_logging_init.py {show} [--verbose [VERBOSE]] [--help]'
        self.assertLinesStartWith(expected, stdout)

    def test_show_no_args(self):
        code, stdout, stderr = self.call_script('show')
        self.assertEqual(code, 2)
        self.assertEqual(stderr, 'argument {attrs,hello,log_test}: missing required argument value\n')

    def test_show_help(self):
        code, stdout, stderr = self.call_script('show', '--help')
        self.assertEqual(code, 0)
        expected = 'usage: shared_logging_init.py {attrs,hello,log_test} [--verbose [VERBOSE]] [--help]'
        self.assertLinesStartWith(expected, stdout)

    def test_show_attrs(self):
        code, stdout, stderr = self.call_script('show', 'attrs')
        self.assertEqual(code, 0)
        self.assertTrue(all(line.startswith('self.') for line in stdout.splitlines()))

    def test_show_hello(self):
        code, stdout, stderr = self.call_script('show', 'hello')
        self.assertEqual(code, 0)
        self.assertEqual(stdout, 'Hello world!\n')

    def test_show_log_test(self):
        code, stdout, stderr = self.call_script('show', 'log_test')
        self.assertEqual(code, 0)
        self.assertEqual(stderr, 'This is an info log\nThis is a warning log\n')

    def test_show_log_test_v(self):
        code, stdout, stderr = self.call_script('show', 'log_test', '-v')
        self.assertEqual(code, 0)
        self.assertEqual(stderr, 'This is a debug log\nThis is an info log\nThis is a warning log\n')

    def test_show_log_test_vv(self):
        code, stdout, stderr = self.call_script('show', 'log_test', '-vv')
        self.assertEqual(code, 0)
        self.assertRegex(stderr, r'DEBUG __main__ \d+ This is a debug log\n')
        self.assertRegex(stderr, r'INFO __main__ \d+ This is an info log\n')
        self.assertRegex(stderr, r'WARNING __main__ \d+ This is a warning log\n')

    def test_show_oops(self):
        code, stdout, stderr = self.call_script('show', 'oops')
        self.assertEqual(code, 2)
        self.assertEqual(
            stderr,
            "argument {attrs,hello,log_test}: invalid choice: 'oops' (choose from: 'attrs', 'hello', 'log_test')\n",
        )


if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    try:
        main(warnings='ignore', verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
