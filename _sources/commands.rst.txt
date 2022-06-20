Commands
********

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
=====================

All commands must extend the :class:`.Command` class.

Multiple keyword-only arguments are supported when defining a subclass of Command (or a subclass thereof).  Some
options provide a way to include additional :ref:`configuration:Command Metadata` in help text / documentation, while
other :ref:`configuration:Configuration Options` exist to control error handling and parsing / formatting.

`Example command <https://github.com/dskrypa/cli_command_parser/blob/main/examples/hello_world.py>`__ that uses some of
those options::

    class HelloWorld(
        Command,
        description='Simple greeting example',
        epilog='Contact <example@fake.org> with any issues'
    ):
        name = Option('-n', default='World', help='The person to say hello to')

        def main(self):
            print(f'Hello {self.name}!')


Command Methods
===============

Simple commands can define ``main`` as the primary method for that command::

    class HelloWorld(Command):
        def main(self):
            print('Hello World!')


If, however, a command uses :ref:`parameters:Action` methods, then :meth:`.Command.main` should not be overridden (or
it should include a call of ``super().main()``) to maintain the expected behavior.

To run code before / after :meth:`.Command.main`, the :meth:`.Command._before_main_` and :meth:`.Command._after_main_`
methods may be overridden, respectively.  Similar to the relationship between :meth:`.Command.main` and
:ref:`parameters:Action` methods, if :ref:`parameters:ActionFlag` methods are used, the corresponding before / after
main method must either not be overridden, or it must call the overridden method via ``super()...`` to maintain the
expected behavior.


Parse & Run
===========

When only one :class:`~.commands.Command` direct subclass is present, the :func:`~.commands.main` convenience function
can be used as the primary entry point for the program::

    from cli_command_parser import Command, Positional, main

    class Echo(Command):
        text = Positional(nargs='*', help='The text to print')

        def main(self):
            print(' '.join(self.text))

    if __name__ == '__main__':
        main()


The primary alternative is to use :meth:`~.Command.parse_and_run` - using the same Echo command as in the above
example::

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
