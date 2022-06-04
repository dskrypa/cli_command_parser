Parameters
**********

Parameters are split into different types to simplify the initialization of each one, and to make it clearer (than,
say, argparse) to differentiate between parameter types.  The two major categories are `Options`_ and `Positionals`_,
but there are `Others`_ as well.  The base class for all Parameters is extensible, and user-defined
:class:`~cli_command_parser.parameters.Parameter` types are technically possible as well.

Many parameters support a ``type`` argument, which will result in the user-provided value being cast to that type before
being stored.  For the parameters that support a type, if not explicitly specified when initializing the parameter, the
type will be inferred automatically from any type annotations (see :pep:`484`) that are present.


.. _common_init_params:

.. rubric:: Common Initialization Parameters

All parameters that can be specified when initializing Parameters should be passed as keyword arguments unless
otherwise stated.

Common parameters that are supported by all Parameters:

- **action**: The action to take on individual parsed values.  This usually does not need to be specified.  It is
  automatically determined based on the specified ``nargs`` value.  Supported values depend on the actions defined for
  each Parameter class.
- **name**: The name of the Parameter.  Defaults to the name assigned to it in a Command.  Shown in usage / help text
  when no ``metavar`` value is specified.
- **metavar**: The name to use as a placeholder for values in usage / help messages.
- **help**: A brief description for the Parameter that will appear in ``--help`` text.
- **hide**: Set this to ``True`` to prevent a Parameter from being included in usage / help text.
- **show_default**: Override the :ref:`show_defaults <configuration:Usage & Help Text Options>` setting for a given
  Parameter to always or never include the default value in usage / help messages.  The default behavior is to follow
  the ``show_defaults`` setting.

Common parameters that are supported when initializing most Parameters:

- **default**: The default value to use when no argument is provided.  When a Parameter is not required, this defaults
  to ``None`` if ``nargs`` would only accept 1 value, and to an empty list if multiple values would be accepted.  Not
  used if the Parameter is required.  Some specialized Parameters have different defaults.
- **required**: Whether a Parameter must be provided or not.  Generally defaults to ``False``, but Positionals, for
  example, default to ``True``.
- **choices**: A container that holds the specific values that users must pick from.  By default, any value is allowed.
- **nargs**: The number of values that are expected/required when the Parameter is specified.  Generally defaults to 1.
  When multiple arguments are accepted, they are collected in a list.  When only 0 - 1 arguments are accepted, they
  will be stored / returned as-is.  Supported values:

    - ``N`` (an integer): Exactly ``N`` arguments must be provided.  If ``N > 1``, the arguments will be collected in
      a list.
    - ``'?'``: One argument may be provided, but it is not required.  Generally only useful for Positional Parameters.
    - ``'*'``: Any number of arguments may be provided, including none.  The arguments will be collected in a list.
    - ``'+'``: One or more arguments may be provided.  The arguments will be collected in a list.
    - ``(N₀, N₁)`` (a tuple of 2 integers): Accept exactly either ``N₀`` or ``N₁`` arguments.  ``N₀`` must be less
      than ``N₁``.
    - ``(N, None)`` (a tuple of an integer and ``None``): Similar to ``'+'``, accept a minimum of ``N`` arguments, or
      any number of arguments greater than ``N``.
    - ``{N₀, N₁, ..., Nₓ}`` (a set of integers): Accept any specific number of
      arguments in the set.
    - ``range(...)`` (a :class:`python:range` object):  Similar to the set of integers, accept any number of arguments
      for which ``N in range(...)`` is ``True`` for the specified range.  Can be used to accept only an even number of
      arguments, such as ``range(0, 6, 2)`` to accept 0, 2, or 4 values.
- **type**: A callable (function, class, etc.) that accepts a single string argument to be used to transform parsed
  argument values.  It will be used before evaluating whether the value is in ``choices``, if specified.  If ``nargs``
  accepts multiple values, then this will be called on each value individually before appending it to the list of
  values.  By default, no transformation is performed, and values will be strings.  If not specified, but a type
  annotation is detected, then that annotation will be used as if it was provided here.  When both are present, this
  argument takes precedence.


Options
=======

Options are parameters that may be provided in any order, and are roughly equivalent to keyword arguments to functions.
They are typically not required by default, and often have both long and short forms, where long forms typically have
a ``--`` prefix, and short forms have a ``-`` prefix.  The long form is automatically added, if not explicitly
specified, based on the name of the Parameter attribute.


.. _options_init_params:

.. rubric:: Common Initialization Parameters - Options

Options support one additional initialization parameter:

- **\*option_strs**: One or more long or short form option strings may be provided positionally, similar to how they
  would be specified when using ``argparse``.

    - Option strings cannot end with ``-`` or contain ``=``.
    - Short forms must begin with a ``-`` prefix, and may be one or more characters.  They may not contain any other
      ``-`` characters.
    - Long forms must begin with a ``--`` prefix, and may be one or more characters.  If provided, the automatically
      generated long form based on the Parameter's name will not be added.


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

:class:`.Flag` parameters typically represent boolean values, and do not accept any values.  By default, Flag
parameters have a default value of ``False``, and will change to ``True`` if provided by a user.  By specifying
``default=True``, then that behavior is reversed.  It is also possible to specify any default value with a different
``const`` value to use if the flag is provided.

.. _flag_init_params:

**Unique Flag initialization parameters:**

- **action**: While not specific to Flags, this is one example of a Parameter where it may be desirable to specify a
  value here.  The default action is ``store_const``, but ``append_const`` is also supported.
- **const**: The constant value to store / append.  If a ``default`` value is provided that is not a bool, then this
  must also be provided.  Defaults to ``True`` when ``default`` is ``False`` (the default when it is not specified),
  and to ``False`` when ``default`` is ``True``.
- **nargs**: Not supported.
- **type**: Not supported.
- **choices**: Not supported.


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

:class:`.Counter` parameters are similar to Flags, but they may be specified multiple times, and they support an
optional integer value to explicitly increase their stored value by that amount.  One common use case for Counters
is for verbosity levels, where logging verbosity would increase with the number of ``-v`` arguments that are provided.

.. _counter_init_params:

**Unique Counter initialization parameters:**

- **default**: The default value if the Parameter is not specified.  This value is also be used as the initial value
  that will be incremented when the flag is provided.  Defaults to ``0``.
- **const**: The value by which the stored value should increase whenever the flag is provided. Defaults to ``1``.
  If a different ``const`` value is used, and if an explicit value is provided by a user, the user-provided value
  will be added verbatim - it will NOT be multiplied by ``const``.
- **nargs**: Not supported.
- **type**: Not supported.
- **choices**: Not supported.


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
    $ prog.py --verbose=2


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

.. _positional_init_params:

**Unique Positional initialization parameters:**

- **nargs**: The number of values that are expected/required for the Parameter.  Defaults to 1.  Use a value that
  allows 0 values to have the same effect as making the Parameter not required (the ``required`` option is not
  supported for Positional Parameters).  Only the last Positional in a given :class:`.Command` may allow a
  variable / unbound number of arguments.
- **default**: Only supported when ``action='store'`` and 0 values are allowed by the specified ``nargs``.  Defaults
  to ``None`` under those conditions.


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

.. _subcommand_init_params:

**Unique SubCommand initialization parameters:**

- **title**: The title to use for help text sections containing the choices for the Parameter.  Defaults to
  ``Subcommands``.
- **description**: The description to be used in help text for the Parameter.
- **nargs**: Not supported.  Automatically calculated / maintained based on registered choices (subcommand target
  Commands).
- **type**: Not supported.
- **choices**: Not supported.


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

.. _action_init_params:

**Unique Action initialization parameters:**

- **title**: The title to use for help text sections containing the choices for the Parameter.  Defaults to
  ``Actions``.
- **description**: The description to be used in help text for the Parameter.
- **nargs**: Not supported.  Automatically calculated / maintained based on registered choices (target methods).
- **type**: Not supported.
- **choices**: Not supported.


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

PassThru
--------

:class:`.PassThru` is a parameter that allows all remaining arguments to be collected, without processing them.  Only
one PassThru parameter may exist in a given :class:`.Command`.  When provided, it must be preceded by ``--`` and a
space.

.. _passthru_init_params:

**Unique PassThru initialization parameters:**

- **nargs**: Not supported.
- **type**: Not supported.
- **choices**: Not supported.


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

.. _actionflag_init_params:

**Unique ActionFlag initialization parameters:**

- **order**: The priority / order for execution, relative to other ActionFlags, if others would also be executed.  Two
  ActionFlags in a given :class:`.Command` may not have the same combination of ``before_main`` and ``order`` values.
  ActionFlags with lower ``order`` values are executed before those with higher values.  The ``--help`` action is
  implemented as an ActionFlag with ``order=float('-inf')``.
- **func**: The function (any callable) to call.  Instead of passing a value here, ActionFlag can be used as a
  decorator for a method that should be called.
- **before_main**: Whether the action should be executed before the :meth:`.Command.main` method or after it.  Defaults
  to ``True``.
- **always_available**: Whether the action should always be available to be called, even if parsing failed.  Only
  allowed when ``before_main=True``.  The intended use case is for actions like ``--help`` text.
- **nargs**: Not supported.
- **type**: Not supported.
- **choices**: Not supported.


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
