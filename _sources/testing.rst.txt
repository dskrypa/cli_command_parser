Testing Commands
****************

Commands can be tested without necessarily doing anything special to work with them in a unit testing context.  When a
Command runs normally, it does not call :func:`python:sys.exit` on a successful run, but it may do so if an unhandled
exception is propagated.  Error handling :ref:`can be disabled<configuration:Error Handling Options>`, but sometimes
you may still need to use ``with self.assertRaises(SystemExit)`` in a test case if it is intentional / expected.


Testing Parsing
===============

To ensure that particular combinations of arguments are parsed as expected, the :meth:`.Command.parse` method can be
used to parse arguments without running :meth:`.Command.main` or triggering any actions.  Parsed attributes may be
accessed directly (as they would be from within the Command when running normally), or gathered in a dict via
:ref:`get_parsed <advanced:Parsed Args as a Dictionary>`.

Using the :gh_examples:`hello_world.py` script that has been used in other examples:

.. literalinclude:: ../../examples/hello_world.py
   :pyobject: HelloWorld

We can write these example test cases::

    from unittest import TestCase
    from cli_command_parser import get_parsed
    from hello_world import HelloWorld

    class HelloWorldTest(TestCase):
        def test_parse_count(self):
            cmd = HelloWorld.parse(['-c', '5'])
            self.assertEqual(5, cmd.count)

        def test_parse_name_and_count(self):
            cmd = HelloWorld.parse(['-c', '3', '-n', 'Bob'])
            expected = {'name': 'Bob', 'count': 3, 'help': False}
            self.assertDictEqual(expected, get_parsed(cmd))


Test Helpers
============

A :class:`.RedirectStreams` :ref:`context manager <python:context-managers>` is available to temporarily override both
``stdout``, ``stderr``, and optionally to provide input for ``stdin``.  It's also possible to use
:func:`python:contextlib.redirect_stdout` and/or :func:`python:contextlib.redirect_stderr`, but this does both at once.

To test the result of actually executing the program, the :meth:`.Command.parse_and_run` method can be used.  Using
the same ``hello_world.py`` script as the above test, we can define some additional example test cases that check
the output::

    from unittest import TestCase
    from cli_command_parser.testing import RedirectStreams
    from hello_world import HelloWorld

    class HelloWorldTest(TestCase):
        def test_hello_default(self):
            with RedirectStreams() as streams:
                HelloWorld.parse_and_run([])
            self.assertEqual('Hello World!\n', streams.stdout)
            self.assertEqual('', streams.stderr)

        def test_hello_test(self):
            with RedirectStreams() as streams:
                HelloWorld.parse_and_run(['-n', 'test'])
            self.assertEqual('Hello test!\n', streams.stdout)


Using ``InputsExample`` from the :gh_examples:`custom_inputs.py` script as the example Command being tested, we can see
how it works to provide ``stdin``::

    def test_custom_input_json_stdin(self):
        with RedirectStreams('{"a": 1, "b": 2}') as streams:
            InputsExample.parse_and_run(['-j', '-'])
        self.assertEqual("You provided a dict\n[0] ('a', 1)\n[1] ('b', 2)\n", streams.stdout)
