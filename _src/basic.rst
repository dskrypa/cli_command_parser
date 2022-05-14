Getting Started
***************

Installing CLI Command Parser
=============================

CLI Command Parser is available on PyPI::

    $ pip install cli-command-parser


Example
=======

The following is a basic example of a program that uses CLI Command Parser::

    from cli_command_parser import Command, Option, main

    class HelloWorld(Command, description='Simple greeting example'):
        name = Option('-n', default='World', help='The person to say hello to')

        def main(self):
            print(f'Hello {self.name}!')

    if __name__ == '__main__':
        main()


After saving it as ``hello_world.py``, we can see the automatically generated help text::

    $ hello_world.py -h
    usage: hello_world.py [--name NAME] [--help]

    Simple greeting example

    Optional arguments:
      --name NAME, -n NAME        The person to say hello to (default: World)
      --help, -h                  Show this help message and exit (default: False)


We can run it with multiple variations of arguments::

    $ hello_world.py
    Hello World!

    $ hello_world.py -n John
    Hello John!

    $ hello_world.py --name John
    Hello John!


Even without explicitly specifying the long form for the ``name`` `Option`_, it was automatically added based on the
name of the attribute in which that Parameter was stored.


Parameters
==========

Parameters are split into different types to simplify the initialization of each one, and to make it clearer (than,
say, argparse) to differentiate between parameter types.  The two major categories are `Options`_ and `Positionals`_,
but there are `Others`_ as well.  The base class for all Parameters is extensible, and user-defined
:class:`~cli_command_parser.parameters.Parameter` types are technically possible as well.

Many parameters support a ``type`` argument, which will result in the user-provided value being cast to that type before
being stored.  For the parameters that support a type, if not explicitly specified when initializing the parameter, the
type will be inferred automatically from any `type annotations <https://peps.python.org/pep-0484/>`_ that are present.


Options
-------

Options are parameters that may be provided in any order, and are roughly equivalent to keyword arguments to functions.
They are typically not required by default, and often have both long and short forms, where long forms typically have
a ``--`` prefix, and short forms have a ``-`` prefix.  The long form is automatically added, if not explicitly
specified, based on the name of the Parameter attribute.

All options in CLI Command Parser extend :class:`~cli_command_parser.parameters.BaseOption`, which provides the basic
handling for long and short forms.


Option
^^^^^^

:class:`~cli_command_parser.parameters.Option` parameters accept arbitrary values or lists of values.

Examples::

    $ prog.py --foo bar baz
    $ prog.py --foo bar
    $ prog.py --foo=bar
    $ prog.py -f bar baz
    $ prog.py -f bar
    $ prog.py -f=bar
    $ prog.py -fbar


Flag
^^^^

:class:`~cli_command_parser.parameters.Flag` parameters typically represent boolean values, and do not accept any
values.  By default, Flag parameters have a default value of ``False``, and will change to ``True`` if provided by a
user.  By specifying ``default=True``, then that behavior is reversed.  It is also possible to specify any default value
with a different ``const`` value to use if the flag is provided.


Counter
^^^^^^^

:class:`~cli_command_parser.parameters.Counter` parameters are similar to Flags, but they may be specified multiple
times, and they support an optional integer value to explicitly increase their stored value by that amount.  One common
use case for Counters is for verbosity levels, where logging verbosity would increase with the number of ``-v``
arguments that are provided.

Given the following example Command::

    class MyCommand(Command):
        verbose = Counter('-v', help='Increase logging verbosity (can specify multiple times)')


All of the following would result in a count of ``2``::

    $ prog.py -v -v
    $ prog.py -vv
    $ prog.py --verbose -v
    $ prog.py -v2
    $ prog.py -v=2
    $ prog.py -v 2


Positionals
-----------

TODO - This is still a work in progress.  The remainder of this document will be filled in soon.

Positional
^^^^^^^^^^

SubCommand
^^^^^^^^^^

Action
^^^^^^


Others
------

ParamGroup
^^^^^^^^^^

PassThru
^^^^^^^^

ActionFlag
^^^^^^^^^^
