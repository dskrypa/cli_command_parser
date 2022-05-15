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


Option
^^^^^^

:class:`~cli_command_parser.parameters.Option` parameters accept arbitrary values or lists of values.

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
^^^^

:class:`~cli_command_parser.parameters.Flag` parameters typically represent boolean values, and do not accept any
values.  By default, Flag parameters have a default value of ``False``, and will change to ``True`` if provided by a
user.  By specifying ``default=True``, then that behavior is reversed.  It is also possible to specify any default value
with a different ``const`` value to use if the flag is provided.

Example::

    class RiskyCommand(Command):
        dry_run = Flag('-D', help='Print the actions that would be taken instead of taking them')


Example usage::

    $ risky_command.py --dry_run
    [DRY RUN] Would execute risky command

    $ risky_command.py
    Executing risky command!


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

*: Options are less flexible when combining since they require a value.  Only one may be combined with other short
forms, and it must be the last parameter in the combo so that it immediately precedes its value.


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
