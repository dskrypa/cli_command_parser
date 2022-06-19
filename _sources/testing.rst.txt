Testing Commands
****************

Commands can be tested without necessarily doing anything special to work with them in a unit testing context.  When a
Command runs normally, it does not call :func:`python:sys.exit` on a successful run, but it may do so if an unhandled
exception is propagated.  Error handling :ref:`can be disabled<configuration:Error Handling Options>`, but sometimes
you may still need to use ``with self.assertRaises(SystemExit)`` in a test case if it is intentional / expected.


Test Helpers
============

A :class:`.RedirectStreams` :ref:`context manager <python:context-managers>` is available to temporarily override
``stdout``, ``stderr``, and optionally to provide input for ``stdin``.  It's also possible to use
:func:`python:contextlib.redirect_stdout` and/or :func:`python:contextlib.redirect_stderr`, but this does both at once.

Using the `hello_world.py <https://github.com/dskrypa/cli_command_parser/blob/main/examples/hello_world.py>`__ script
that has been used in other examples::

    class HelloWorld(Command):
        name = Option('-n', default='World', help='The person to say hello to')

        def main(self):
            print(f'Hello {self.name}!')


We can test it like this::

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


Using InputsExample from the
`custom_inputs.py <https://github.com/dskrypa/cli_command_parser/blob/main/examples/custom_inputs.py>`__ script
as the example Command being tested, we can see how it works to provide ``stdin``::

    def test_custom_input_json_stdin(self):
        with RedirectStreams('{"a": 1, "b": 2}') as streams:
            InputsExample.parse_and_run(['-j', '-'])
        self.assertEqual("You provided a dict\n[0] ('a', 1)\n[1] ('b', 2)\n", streams.stdout)
