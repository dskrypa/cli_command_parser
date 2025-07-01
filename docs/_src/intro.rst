Getting Started
***************

Simple scripts usually contain a single class that extends ``Command`` and implements a ``def main(self):`` method
to be called after arguments are parsed.

CLI parameters are defined as attributes within that class that are very similar to properties.  There's no need to
specify a ``'--long-option-name'`` string for options, flags, and other similar parameters (but you can!) - by default,
those are automatically generated based on the name assigned to the attribute.

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


That example used the ``main()`` function imported from ``cli_command_parser`` to automatically find the command that
should be used, to parse the provided CLI arguments, and to invoke the ``main`` method within that command.


Parameters
==========

Types
-----

One of the largest changes for users who are familiar with other Python libraries used for parsing CLI arguments is
that different kinds of parameters all have their own distinct :doc:`Parameter<parameters>` class.  This helps to make
it clear which settings are supported by each one.  Commands may contain any number of Parameters.

A short intro for each type:
  - :ref:`parameters:Positional`: Arguments without a ``--key`` preceding their values, where order matters
  - :ref:`parameters:Option`: Options that can be provided as ``--key value`` or ``-k value`` pairs
  - :ref:`parameters:Flag`: Options that usually toggle between ``True`` / ``False``, provided as ``--flag`` or ``-f``
  - :ref:`parameters:TriFlag`: Similar to ``Flag``, but with support for a third constant and an alternate ``--no-flag``
  - :ref:`parameters:Counter`: Counts the number of times it was provided as a flag; useful for cases like log verbosity
  - :ref:`parameters:ActionFlag`: Chainable action methods invoked in a pre-defined order when provided like a ``--flag``
  - :ref:`parameters:SubCommand`: Positional parameter used to specify where the name of a subcommand should be provided
  - :ref:`parameters:Action`: Similar to ``SubCommand``, but used with action methods within a command
  - :ref:`parameters:PassThru`: Arguments that are collected verbatim and provided as ``-- extra args here``

Parameters can also be :doc:`grouped<groups>` for organizational purposes, or to make parameters be mutually exclusive
or dependent.


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


By default, multi-part `snake_case` names will be translated such that the underscores become dashes.  I.e.,
``foo_bar = Option()`` will result in ``--foo-bar``.  This behavior can be adjusted for all options in a given command
(and its subcommands, if any), and on a per-option basis.  See :ref:`configuration:Parsing Options:option_name_mode`
for more info about how to configure this.


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
