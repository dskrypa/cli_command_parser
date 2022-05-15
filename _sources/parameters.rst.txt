Parameters
==========

Parameters are split into different types to simplify the initialization of each one, and to make it clearer (than,
say, argparse) to differentiate between parameter types.  The two major categories are `Options`_ and `Positionals`_,
but there are `Others`_ as well.  The base class for all Parameters is extensible, and user-defined
:class:`~cli_command_parser.parameters.Parameter` types are technically possible as well.

Many parameters support a ``type`` argument, which will result in the user-provided value being cast to that type before
being stored.  For the parameters that support a type, if not explicitly specified when initializing the parameter, the
type will be inferred automatically from any type annotations (see :pep:`484`) that are present.


.. _Options:

Options
-------

Options are parameters that may be provided in any order, and are roughly equivalent to keyword arguments to functions.
They are typically not required by default, and often have both long and short forms, where long forms typically have
a ``--`` prefix, and short forms have a ``-`` prefix.  The long form is automatically added, if not explicitly
specified, based on the name of the Parameter attribute.


.. _Option:

Option
^^^^^^

The generic :class:`~cli_command_parser.parameters.Option` parameter, that accepts arbitrary values or lists of values.

Given the following example Command::

    class MyCommand(Command):
        foo = Option('-f', nargs='+')


All of the following are valid arguments::

    $ prog.py --foo bar baz
    $ prog.py --foo bar
    $ prog.py --foo=bar
    $ prog.py -f bar baz
    $ prog.py -f bar
    $ prog.py -f=bar
    $ prog.py -fbar


Inside ``MyCommand``, the resulting value of ``self.foo`` would be ``['bar']`` or ``['bar', 'baz']`` for each of those
inputs, respectively.


.. _Flag:

Flag
^^^^

:class:`~cli_command_parser.parameters.Flag` parameters typically represent boolean values, and do not accept any
values.  By default, Flag parameters have a default value of ``False``, and will change to ``True`` if provided by a
user.  By specifying ``default=True``, then that behavior is reversed.  It is also possible to specify any default value
with a different ``const`` value to use if the flag is provided.

Example::

    class RiskyCommand(Command):
        dry_run = Flag('-D', help='Print the actions that would be taken instead of taking them')

        def main(self):
            if self.dry_run:
                print('[DRY RUN] Would execute risky command')
            else:
                print('Executing risky command!')


Example usage::

    $ risky_command.py --dry_run
    [DRY RUN] Would execute risky command

    $ risky_command.py
    Executing risky command!


.. _Counter:

Counter
^^^^^^^

:class:`~cli_command_parser.parameters.Counter` parameters are similar to Flags, but they may be specified multiple
times, and they support an optional integer value to explicitly increase their stored value by that amount.  One common
use case for Counters is for verbosity levels, where logging verbosity would increase with the number of ``-v``
arguments that are provided.

Given the following example Command::

    class NoisyCommand(Command):
        verbose = Counter('-v', help='Increase logging verbosity (can specify multiple times)')


All of the following would result in ``self.verbose`` being ``2``::

    $ prog.py -v -v
    $ prog.py -vv
    $ prog.py --verbose -v
    $ prog.py -v2
    $ prog.py -v=2
    $ prog.py -v 2


When provided, the short forms of Option*, Flag, and Counter parameters can be chained together without a space or
additional ``-`` prefix character.

\*: Options are less flexible when combining since they require a value.  Only one may be combined with other short
forms, and it must be the last parameter in the combo so that it immediately precedes its value.


.. _Positionals:

Positionals
-----------

Positionals are parameters that must be provided in a specific order.  They are typically required by default, and they
do not have any prefix before values.

Arguments for Positional parameters may be provided before, after, and between `Options`_, as long as the immediately
preceding optional parameter accepts a bounded number of arguments and those values were provided.

The order that positional parameters are defined in a given :class:`~cli_command_parser.commands.Command` determines
the order in which they must be provided; i.e., the top-most positional parameters must be provided first.


.. _Positional:

Positional
^^^^^^^^^^

The generic :class:`~cli_command_parser.parameters.Positional` parameter, that accepts arbitrary values or lists of
values.

Example command::

    class Echo(Command):
        text = Positional(nargs='*', help='The text to print')

        def main(self):
            print(' '.join(self.text))


Example usage::

    $ echo.py Hello World
    Hello World


.. _SubCommand:

SubCommand
^^^^^^^^^^

The :class:`~cli_command_parser.parameters.SubCommand` parameter allows additional
:class:`~cli_command_parser.commands.Command` classes to be registered as subcommands of the Command that contains the
SubCommand parameter.

Explicit registration is not necessary for Commands that extend their parent Command - given the following example::

    class Base(Command):
        sub_cmd = SubCommand()

    class Foo(Base, help='Print foo'):
        def main(self):
            print('foo')

    class Bar(Base, help='Print bar'):
        def main(self):
            print('bar')


It produces the following help text::

    $ basic_subcommand.py -h
    usage: basic_subcommand.py {foo,bar} [--help]

    Subcommands:
      {foo,bar}
        foo                       Print foo
        bar                       Print bar


    Optional arguments:
      --help, -h                  Show this help message and exit (default: False)


Usage examples::

    $ basic_subcommand.py foo
    foo

    $ basic_subcommand.py bar
    bar


When automatically registered, the choice will be the lower-case name of the sub command class.  It is possible to
:meth:`~cli_command_parser.parameters.SubCommand.register` sub commands explicitly to specify a different choice value,
including names that may include spaces.  Such names can be provided without requiring users to escape or quote the
string (i.e., as technically separate arguments).  This allows for a more natural way to provide multi-word commands,
without needing to jump through hoops to handle them.


.. _Action:

Action
^^^^^^

:class:`~cli_command_parser.parameters.Action` parameters are similar to
:class:`~cli_command_parser.parameters.SubCommand` parameters, but allow methods in
:class:`~cli_command_parser.commands.Command` classes to be registered as a callable to be executed based on a user's
choice instead of separate sub Commands.

When there are multiple choices of functions that may be called for a given program, Actions are better suited to use
cases where all of those functions share the same parameters.  If the target functions require different / additional
parameters, then using a :class:`~cli_command_parser.parameters.SubCommand` with separate sub
:class:`~cli_command_parser.commands.Command` classes may make more sense.

Example command that uses actions::

    class Example(Command):
        action = Action(help='The action to take')
        text = Positional(nargs='+', help='The text to print')

        @action(help='Echo the provided text')
        def echo(self):
            print(' '.join(self.text))

        @action(help='Split the provided text so that each word is on a new line')
        def split(self):
            print('\n'.join(self.text))


The resulting help text::

    $ action_with_args.py -h
    usage: action_with_args.py {echo,split} TEXT [--help]

    Positional arguments:

    Actions:
      {echo,split}
        echo                      Echo the provided text
        split                     Split the provided text so that each word is on a new line

      TEXT [TEXT ...]             The text to print

    Optional arguments:
      --help, -h                  Show this help message and exit (default: False)


Example usage::

    $ action_with_args.py echo one two
    one two

    $ action_with_args.py split one two
    one
    two


.. _Others:

Others
------

TODO - This is still a work in progress.  The remainder of this document will be filled in soon.

.. _ParamGroup:

ParamGroup
^^^^^^^^^^


.. _PassThru:

PassThru
^^^^^^^^


.. _ActionFlag:

ActionFlag
^^^^^^^^^^
