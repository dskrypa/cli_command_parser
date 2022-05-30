Parameters
**********

Parameters are split into different types to simplify the initialization of each one, and to make it clearer (than,
say, argparse) to differentiate between parameter types.  The two major categories are `Options`_ and `Positionals`_,
but there are `Others`_ as well.  The base class for all Parameters is extensible, and user-defined
:class:`~cli_command_parser.parameters.Parameter` types are technically possible as well.

Many parameters support a ``type`` argument, which will result in the user-provided value being cast to that type before
being stored.  For the parameters that support a type, if not explicitly specified when initializing the parameter, the
type will be inferred automatically from any type annotations (see :pep:`484`) that are present.


Options
=======

Options are parameters that may be provided in any order, and are roughly equivalent to keyword arguments to functions.
They are typically not required by default, and often have both long and short forms, where long forms typically have
a ``--`` prefix, and short forms have a ``-`` prefix.  The long form is automatically added, if not explicitly
specified, based on the name of the Parameter attribute.


Option
------

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


Flag
----

:class:`~cli_command_parser.parameters.Flag` parameters typically represent boolean values, and do not accept any
values.  By default, Flag parameters have a default value of ``False``, and will change to ``True`` if provided by a
user.  By specifying ``default=True``, then that behavior is reversed.  It is also possible to specify any default value
with a different ``const`` value to use if the flag is provided.

`Example command <https://github.com/dskrypa/cli_command_parser/blob/main/examples/simple_flags.py>`__::

    class Example(Command):
        foo = Flag('-f')  # the default ``default`` value is False
        bar = Flag('--no-bar', '-B', default=True)

        def main(self):
            print(f'self.foo = {self.foo!r}')
            print(f'self.bar = {self.bar!r}')


Example usage::

    $ simple_flags.py
    self.foo = False
    self.bar = True

    $ simple_flags.py -f --no-bar
    self.foo = True
    self.bar = False

    $ simple_flags.py -h
    usage: simple_flags.py [--foo] [--no-bar] [--help]

    Optional arguments:
      --foo, -f                   (default: False)
      --no-bar, -B                (default: True)
      --help, -h                  Show this help message and exit (default: False)


Counter
-------

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


Positionals
===========

Positionals are parameters that must be provided in a specific order.  They are typically required by default, and they
do not have any prefix before values.

Arguments for Positional parameters may be provided before, after, and between `Options`_, as long as the immediately
preceding optional parameter accepts a bounded number of arguments and those values were provided.

The order that positional parameters are defined in a given :class:`~cli_command_parser.commands.Command` determines
the order in which they must be provided; i.e., the top-most positional parameters must be provided first.


Positional
----------

The generic :class:`~cli_command_parser.parameters.Positional` parameter, that accepts arbitrary values or lists of
values.

`Example command <https://github.com/dskrypa/cli_command_parser/blob/main/examples/echo.py>`__::

    class Echo(Command):
        text = Positional(nargs='*', help='The text to print')

        def main(self):
            print(' '.join(self.text))


Example usage::

    $ echo.py Hello World
    Hello World


SubCommand
----------

The :class:`.SubCommand` parameter allows additional :class:`.Command` classes to be registered as subcommands of the
Command that contains the SubCommand parameter.  A given Command may only contain one SubCommand parameter.

SubCommand exists as a Parameter so that it is possible to specify where the argument for choosing the subcommand
should be provided relative to other positional parameters, if any.

Explicit registration is not necessary for Commands that extend their parent Command - given the `following example
<https://github.com/dskrypa/cli_command_parser/blob/main/examples/basic_subcommand.py>`_::

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
:meth:`~.SubCommand.register` sub commands explicitly to specify a different choice value, including names that may
include spaces.  Such names can be provided without requiring users to escape or quote the string (i.e., as
technically separate arguments).  This allows for a more natural way to provide multi-word commands, without needing
to jump through hoops to handle them.


Action
------

:class:`.Action` parameters are similar to :class:`.SubCommand` parameters, but allow methods in :class:`.Command`
classes to be registered as a callable to be executed based on a user's choice instead of separate sub Commands.

When there are multiple choices of functions that may be called for a given program, Actions are better suited to use
cases where all of those functions share the same parameters.  If the target functions require different / additional
parameters, then using a :class:`.SubCommand` with separate sub :class:`.Command` classes may make more sense.

`Example command <https://github.com/dskrypa/cli_command_parser/blob/main/examples/action_with_args.py>`__ that uses
actions::

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


Others
======

ParamGroup
----------

A group of parameters.  :class:`~cli_command_parser.parameters.ParamGroup` is intended to be used as a context manager,
where group members are defined inside the ``with`` block.  Supports mutually exclusive and mutually dependent groups.

Allows arbitrary levels of nesting, including mutually dependent groups inside mutually exclusive groups, and vice
versa.  Grouping may also be used to simply organize parameters as they appear in help text.

In the following example, ``wait`` and ``no_wait`` are mutually exclusive - if both are provided, then an exception is
raised.  The ``tasks`` and ``verbose`` parameters are not in the group::

    class TaskRunner(Command):
        tasks = Positional(nargs='+', help='The tasks to run')

        with ParamGroup('Wait Options', mutually_exclusive=True):
            wait: int = Option('-w', default=1, help='Seconds to wait (0 or below to wait indefinitely)')
            no_wait = Flag('-W', help='Do not wait')

        verbose = Counter('-v', help='Increase logging verbosity (can specify multiple times)')


PassThru
--------

:class:`~cli_command_parser.parameters.PassThru` is a parameter that allows all remaining arguments to be collected,
without processing them.  Only one PassThru parameter may exist in a given
:class:`~cli_command_parser.commands.Command`.  When provided, it must be preceded by ``--`` and a space.

`Example command <https://github.com/dskrypa/cli_command_parser/blob/main/examples/command_wrapper.py>`__::

    class Wrapper(Command):
        hosts = Positional(nargs='+', help='The hosts on which the given command should be run')
        command = PassThru(help='The command to run')

        def main(self):
            for host in self.hosts:
                print(f'Would run on {host}: {self.command}')


Example help text::

    $ command_wrapper.py -h
    usage: command_wrapper.py HOSTS [--help] [-- COMMAND]

    Positional arguments:
      HOSTS [HOSTS ...]           The hosts on which the given command should be run

    Optional arguments:
      COMMAND                     The command to run (default: None)
      --help, -h                  Show this help message and exit (default: False)


Example usage::

    $ command_wrapper.py one two -- service foo restart
    Would run on one: ['service', 'foo', 'restart']
    Would run on two: ['service', 'foo', 'restart']


ActionFlag
----------

:class:`.ActionFlag` parameters act like a combination of :ref:`parameters:Flag` and :ref:`parameters:Action`
parameters.  Like Flags, they are not required, and they can be combined with other :ref:`parameters:Options`.  Like
Actions, they allow methods in :class:`.Command` classes to be registered as execution targets.

When ActionFlag arguments are provided, the associated methods are called in the order that was specified when marking
those methods as ActionFlags.  Execution order is also customizable relative to when the :meth:`.Command.main`
method is called, so each ActionFlag must indicate whether it should run before or after main.  Helper decorators
are provided to simplify this distinction: :data:`~.parameters.before_main` and :data:`~.parameters.after_main`.

Example command::

    class Build(Command):
        build_dir: Path = Option(required=True, help='The target build directory')
        install_dir: Path = Option(required=True, help='The target install directory')
        backup_dir: Path = Option(required=True, help='Directory in which backups should be stored')

        @before_main('-b', help='Backup the install directory before building')
        def backup(self):
            shutil.copy(self.install_dir, self.backup_dir)

        def main(self):
            subprocess.check_call(['make', 'build', self.build_dir.as_posix()])
            shutil.copy(self.build_dir, self.install_dir)

        @after_main('-c', help='Cleanup the build directory after installing')
        def cleanup(self):
            shutil.rmtree(self.build_dir)


By default, the ActionFlags configured to run after :meth:`.Command.main` will not run if an exception was raised in
:meth:`.Command.main`.  It is possible to specify :attr:`.CommandConfig.always_run_after_main` to allow
:meth:`.Command._after_main_` (and therefore ActionFlags registered to run after main) to be called even if an
exception was raised.
