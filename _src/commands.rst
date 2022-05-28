Commands
========

Commands provide a way to organize CLI applications intuitively.

Having parameters defined as attributes in the class results in a better developer experience when writing code that
references those attributes in an IDE.  You can take advantage of type annotations and variable name completion.
Changing the name of a parameter can take advantage of builtin renaming tools, instead of needing to hunt for
references to ``args.foo`` to be updated.  There's no need to keep function signatures up to date with parameters
defined in decorators.

A minimal set of pre-defined methods provide the basic functionality for parsing arguments and running code based on
the parsed input.  Any other attribute or method can be defined and used without affecting functionality.

Since subcommands can extend their parent command, they can take advantage of standard class inheritance to share
common parameters, methods, and initialization steps with minimal extra work or code.


Initializing Commands
---------------------

All commands must extend the :class:`~cli_command_parser.commands.Command` class.

Multiple keyword-only arguments are supported when defining a subclass of Command (or a subclass thereof)

`Example command <https://github.com/dskrypa/cli_command_parser/blob/main/examples/hello_world.py>`__ that uses some of
the following options::

    class HelloWorld(
        Command,
        description='Simple greeting example',
        epilog='Contact <example@fake.org> with any issues'
    ):
        name = Option('-n', default='World', help='The person to say hello to')

        def main(self):
            print(f'Hello {self.name}!')


Command Metadata
^^^^^^^^^^^^^^^^

Keyword arguments supported when defining a Command subclass:

- **choice**: SubCommand value that should be mapped to this command, if different than this class's (lower case)
  name.
- **prog**: The name of the program (default: ``sys.argv[0]``)
- **usage**: Usage message to be printed with help text or when incorrect arguments are provided (default:
  auto-generated)
- **description**: Description of what the program does
- **epilog**: Text to follow parameter descriptions
- **help**: Help text to be displayed as a SubCommand option.  Ignored for top-level commands.
- **config**: A :class:`~.config.CommandConfig` object containing the config options to use.  May not be combined
  with separate kwargs that would be stored in a CommandConfig object.


Configuration
^^^^^^^^^^^^^

Configuration options supported by :class:`~.config.CommandConfig`.  For convenience, they may also be specified as
keyword arguments when defining a Command subclass:

- **multiple_action_flags**: Whether multiple action_flag methods are allowed to run if they are all specified
  (default: True)
- **action_after_action_flags**: Whether action_flag methods are allowed to be combined with a positional Action
  method in a given CLI invocation (default: True)
- **add_help**: Whether the ``--help`` / ``-h`` action_flag should be added (default: True)
- **error_handler**: The :class:`~.error_handling.ErrorHandler` to be used by :meth:`.Command.__call__` to wrap
  :meth:`.Command.main`, or None to disable error handling.  (default: :obj:`~.error_handling.extended_error_handler`)
- **ignore_unknown**: Whether unknown arguments should be ignored (default: False / raise an exception when unknown
  arguments are encountered)
- **allow_missing**: Whether missing required arguments should be allowed (default: False / raise an exception when
  they are missing)
- **allow_backtrack**: Whether the parser is allowed to backtrack or not when a Positional parameter follows a
  parameter with variable :class:`.Nargs`, and not enough arguments are available to fulfil that Positional's
  requirements (default: True)
- **always_run_after_main**: Whether :meth:`.Command._after_main_` should always be called, even if an exception was
  raised in :meth:`.Command.main` (similar to a ``finally`` block) (default: False)
- **use_type_metavar**: Whether the metavar for Parameters that accept values should default to the name of the
  specified type (default: False / the name of the parameter)
- **show_defaults**: Whether default values for Parameters should be automatically included in help text or not, and
  related settings.  Acceptable values are defined as `enum flags <https://docs.python.org/3/library/enum.html#flag>`__
  that can be combined.  See :class:`.ShowDefaults` for more info.


Command Methods
---------------

Simple commands can define ``main`` as the primary method for that command::

    class HelloWorld(Command):
        def main(self):
            print('Hello World!')


If, however, a command uses :ref:`Action` methods, then :meth:`.Command.main` should not be overridden (or it should
include a call of ``super().main()``) to maintain the expected behavior.

To run code before / after :meth:`.Command.main`, the :meth:`.Command._before_main_` and :meth:`.Command._after_main_`
methods may be overridden, respectively.  Similar to the relationship between :meth:`.Command.main` and :ref:`Action`
methods, if :ref:`ActionFlag` methods are used, the corresponding before / after main method must either not be
overridden, or it must call the overridden method via ``super()...`` to maintain the expected behavior.


Subcommands
-----------

While subcommands will be automatically registered with their parent class as long as the parent class has a
:ref:`SubCommand` parameter, it is also possible to have more control over that process.

`Example commands <https://github.com/dskrypa/cli_command_parser/blob/main/examples/advanced_subcommand.py>`__::

    class Base(Command):
        sub_cmd = SubCommand()
        verbose = Counter('-v', help='Increase logging verbosity (can specify multiple times)')

        def __init__(self):
            if self.verbose > 1:
                log_fmt = '%(asctime)s %(levelname)s %(name)s %(lineno)d %(message)s'
            else:
                log_fmt = '%(message)s'

            level = logging.DEBUG if self.verbose else logging.INFO
            logging.basicConfig(level=level, format=log_fmt)

    @Base.sub_cmd.register('run foo', help='Run foo')  # Aliases can have their own help text
    class Foo(Base, help='Print foo'):
        # This is registered with both ``run foo`` and ``foo`` as names for this command - both can be used
        def main(self):
            print('foo')
            log.debug('[foo] this is a debug log')

    class Bar(Base, choice='run bar', help='Print bar'):
        # This is registered with ``run bar`` as the name for this command instead of ``bar``
        def main(self):
            print('bar')
            log.debug('[bar] this is a debug log')

    @Base.sub_cmd.register(help='Print baz')
    class Baz(Command):
        # This is registered as a subcommand of Base, named ``baz``, but it does not share parameters with Base
        def main(self):
            print('baz')
            # The next line will never appear in output because Base.__init__ will not be called for this subcommand
            log.debug('[baz] this is a debug log')

    if __name__ == '__main__':
        Base.parse_and_run()


When multiple top-level Commands exist, as they do in this example, then the :func:`~.commands.main` convenience
function can no longer be used as the main entry point for the program.  Instead, the
:ref:`parse_and_run()<parse_and_run>` method needs to be called on the primary Command subclass.


Top level ``--help`` text for the above example::

    $ advanced_subcommand.py -h
    usage: advanced_subcommand.py {foo,run foo,run bar,baz} [--help]

    Subcommands:
      {foo,run foo,run bar,baz}
        foo                       Print foo
        run foo                   Run foo
        run bar                   Print bar
        baz                       Print baz

    Optional arguments:
      --verbose [VERBOSE], -v [VERBOSE]
                                  Increase logging verbosity (can specify multiple times) (default: 0)
      --help, -h                  Show this help message and exit (default: False)


Each subcommand has its own command-specific help text as well::

    $ advanced_subcommand.py foo -h
    usage: advanced_subcommand.py foo [--verbose [VERBOSE]] [--help]

    Optional arguments:
      --verbose [VERBOSE], -v [VERBOSE]
                                  Increase logging verbosity (can specify multiple times) (default: 0)
      --help, -h                  Show this help message and exit (default: False)

    $ advanced_subcommand.py baz -h
    usage: advanced_subcommand.py baz [--help]

    Optional arguments:
      --help, -h                  Show this help message and exit (default: False)


Note that the ``baz`` subcommand, which does not extend ``Base``, does not include ``verbose`` because it does not
extend ``Base``.  Additionally, while ``Base.__init__`` will be called to initialize logging for both the ``Foo``
and ``Bar`` subcommands, it will not be called for ``Baz``.  Regardless of where ``--verbose`` / ``-v`` is specified,
however, it will not cause a parsing error for ``Baz`` since it is registered as a subcommand of a Command that expects
that argument::

    $ advanced_subcommand.py foo -v
    foo
    [foo] this is a debug log

    $ advanced_subcommand.py -v foo
    foo
    [foo] this is a debug log

    $ advanced_subcommand.py baz -v
    baz

    $ advanced_subcommand.py -v baz
    baz

    $ advanced_subcommand.py foo -x
    unrecognized arguments: -x


This set of commands also contains an example of using a subcommand name that contains a space.  It can be provided
without needing to escape the space or put it in quotes::

    $ advanced_subcommand.py run bar
    bar


.. _parse_and_run:

Parse & Run
-----------

When only one :class:`~.commands.Command` direct subclass is present, the :func:`~.commands.main` convenience function
can be used as the primary entry point for the program::

    from cli_command_parser import Command, Positional, main

    class Echo(Command):
        text = Positional(nargs='*', help='The text to print')

        def main(self):
            print(' '.join(self.text))

    if __name__ == '__main__':
        main()


The primary alternative is to use :meth:`~.Command.parse_and_run` - using the same Echo command as in the above example::

    if __name__ == '__main__':
        Echo.parse_and_run()


When using :func:`~.commands.main`, it looks for all known Command subclasses, and calls :meth:`~.Command.parse_and_run`
on the discovered subclass, passing along any arguments that were provided.

By default, :meth:`~.Command.parse_and_run` will use :data:`sys.argv` as the source of arguments to parse.  If desired
for testing purposes, or if there is a need to modify arguments before letting them be parsed, a list of strings may
also be provided::

    >>> class Foo(Command):
    ...     bar = Flag('--no-bar', '-B', default=True)
    ...     baz = Positional(nargs='+')
    ...
    ...     def main(self):
    ...         print(f'{self.bar=}, {self.baz=}')
    ...

    >>> Foo.parse_and_run(['test', 'one', '-B'])
    self.bar=False, self.baz=['test', 'one']
