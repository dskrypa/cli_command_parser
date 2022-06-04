Getting Started
***************

Simple scripts usually contain a single Command and implement a ``def main(self):`` method in that Command to be
called after arguments are parsed.

Multiple Parameters can be specified as attributes inside the Command to define how CLI arguments will be parsed.

The ``main()`` function that can be imported from ``cli_command_parser`` provides the main entry point for parsing
arguments and running the Command.

Here's a basic example of a program that uses CLI Command Parser::

    from cli_command_parser import Command, Option, main

    class HelloWorld(Command, description='Simple greeting example'):
        name = Option('-n', default='World', help='The person to say hello to')

        def main(self):
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

Even without explicitly specifying the long form for the ``name`` :ref:`parameters:Option` in the example above, it
was automatically added based on the name of the attribute in which that Parameter was stored.  Short forms are not
automatically generated to avoid conflicts.

The ``Option(...)`` Parameter above would be equivalent to the following if you were using argparse::

    parser.add_argument('--name', '-n', default='World', help='The person to say hello to')


A Command may contain any number of Parameters to define how it will parse CLI arguments.  To better differentiate
between Parameter types, they are defined as separate classes.  The basics are :ref:`parameters:Positional`,
:ref:`parameters:Option`, and :ref:`parameters:Flag`, but there are :doc:`others<parameters>` as well, including
:doc:`groups<groups>` that can be mutually exclusive or dependent.


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
      --help, -h                  Show this help message and exit (default: False)


The ``--help`` / ``-h`` option is automatically added to the command, and usage / help text is automatically generated
based on the Command, the file it is in, and the Parameters in the Command.

More information about help text and other ways to document programs (such as generating RST) can be found in
:doc:`documentation`.
