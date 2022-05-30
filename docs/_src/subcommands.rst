Subcommands
***********

Explicit Registration
=====================


While subcommands will be automatically registered with their parent class as long as the parent class has a
:ref:`parameters:SubCommand` parameter, it is also possible to have more control over that process.

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
:ref:`parse_and_run()<commands:Parse & Run>` method needs to be called on the primary Command subclass.


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
