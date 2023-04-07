Getting Started
***************

Simple scripts usually contain a single Command and implement a ``def main(self):`` method in that Command to be
called after arguments are parsed.

Multiple Parameters can be specified as attributes inside the Command to define how CLI arguments will be parsed.

The ``main()`` function that can be imported from ``cli_command_parser`` provides the main entry point for parsing
arguments and running the Command.

.. _hello_example:

Here's a basic example of a program that uses CLI Command Parser::

    from cli_command_parser import Command, Option, main

    class Hello(Command, description='Simple greeting example'):
        name = Option('-n', default='World', help='The person to say hello to')
        count: int = Option('-c', default=1, help='Number of times to repeat the message')

        def main(self):
            for _ in range(self.count):
                print(f'Hello {self.name}!')

    if __name__ == '__main__':
        main()


After saving the example above as ``hello_world.py``, we can run it with multiple variations of arguments::

    $ hello_world.py
    Hello World!

    $ hello_world.py -n John
    Hello John!

    $ hello_world.py --name John
    Hello John!


Parameters
==========

Types
-----

Rather than needing to infer the type of parameter that will result from a combination of arguments when defining it,
each distinct type has its own :doc:`Parameter<parameters>` class.  Commands may contain any number of Parameters to
define how they will parse CLI arguments.

The basic types are :ref:`parameters:Positional`, :ref:`parameters:Option`, and :ref:`parameters:Flag`, but there are
:doc:`others<parameters>` as well, including :doc:`groups<groups>` that can be mutually exclusive or dependent.

Names
-----

Even without explicitly specifying the long form for the ``name`` :ref:`parameters:Option` in the example above, it was
automatically added based on the name of that Parameter attribute.  Following the
`DRY principle <https://en.wikipedia.org/wiki/Don%27t_repeat_yourself>`__, the ``--long`` form for Options,
Flags, etc. is generated automatically.  To avoid conflicts, short forms are not automatically generated.

The ``Option(...)`` Parameters :ref:`in the above Hello example<hello_example>` would be equivalent to the following
if you were using argparse::

    parser.add_argument('--name', '-n', default='World', help='The person to say hello to')
    parser.add_argument('--count', '-c', type=int, default=1, help='Number of times to repeat the message')

If an explicit long form is provided, then it will be used instead of the default name-based one.  Any number of long
and/or short forms may be provided::

    example = Option('--foo', '-f', '--FOO')


Entry Points
============

The example above contains only one Command and uses the ``main()`` function to handle parsing arguments and running
the Command.  By default, arguments will be parsed from :data:`python:sys.argv`, but it is also possible to pass a list
of strings as the first argument to parse arguments from that instead.

More advanced programs may contain multiple Commands, and more complex entry points for commands are
:ref:`also supported<commands:Parse & Run>`.


Help Text
=========

Using the Hello World example again, we can see the automatically generated help text::

    $ hello_world.py -h
    usage: hello_world.py [--name NAME] [--help]

    Simple greeting example

    Optional arguments:
      --name NAME, -n NAME        The person to say hello to (default: 'World')
      --help, -h                  Show this help message and exit


The ``--help`` / ``-h`` option is automatically added to the command, and usage / help text is automatically generated
based on the Command, the file it is in, and the Parameters in the Command.

More information about help text and other ways to document programs (such as generating RST) can be found in
:doc:`documentation`.
