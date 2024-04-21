Commands
********

Commands provide a way to organize CLI applications in an intuitively object-oriented way.

Having parameters defined as attributes in the class results in a better developer experience when writing code that
references those attributes in an IDE.  You can take advantage of type annotations and variable name completion.
Changing the name of a parameter can take advantage of builtin renaming tools, instead of needing to hunt for
references to ``args.foo`` to be updated, for example.  Further, there's no need to keep function signatures up to date
with parameters defined in decorators.

Since subcommands can extend their parent command, they can take advantage of standard class inheritance to share
common parameters, methods, and initialization steps with minimal extra work or code.


Defining Commands
=================

All commands must extend the :class:`.Command` class.

Multiple keyword-only arguments are supported when defining a subclass of Command (or a subclass thereof).  Some of
these options provide a way to include additional :ref:`configuration:Command Metadata` in help text / documentation,
while other :ref:`configuration:Configuration Options` exist to control error handling and parsing / formatting.

:gh_examples:`Example command <hello_world.py>` that uses some of those options::

    class HelloWorld(
        Command,
        description='Simple greeting example',
        epilog='Contact <example@fake.org> with any issues'
    ):
        name = Option('-n', default='World', help='The person to say hello to')

        def main(self):
            print(f'Hello {self.name}!')


Command Methods & Attributes
============================

The primary method used to define what should happen when a command is run is ``main``.  Simple commands don't need
to implement anything else::

    class HelloWorld(Command):
        def main(self):
            print('Hello World!')


The only other method names that are used by the base :class:`.Command` class\ [1]_ are ``parse`` and ``parse_and_run``,
which are classmethods that are automatically used during parsing and Command initialization.  Any\ [2]_ other attribute
or method can be defined and used without affecting functionality.


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


:func:`~.commands.main` automatically\ [3]_ finds the top-level Command that you defined, parses arguments from
:data:`python:sys.argv`, and runs your command.

There's no need to call ``parse`` or :meth:`~.Command.parse_and_run` directly, but ``parse_and_run`` can be used as
a drop-in replacement for :func:`~.commands.main` for a specific Command.  Using the same Echo command as in the
above example::

    if __name__ == '__main__':
        Echo.parse_and_run()


By default, :func:`~.commands.main` and :meth:`~.Command.parse_and_run` will use :data:`python:sys.argv` as the source
of arguments to parse.  If desired for testing purposes, or if there is a need to modify arguments before letting them
be parsed, a list of strings may also be provided when using either approach::

    >>> class Foo(Command):
    ...     bar = Flag('--no-bar', '-B', default=True)
    ...     baz = Positional(nargs='+')
    ...
    ...     def main(self):
    ...         print(f'{self.bar=}, {self.baz=}')
    ...

    >>> Foo.parse_and_run(['test', 'one', '-B'])
    self.bar=False, self.baz=['test', 'one']


----

.. [1] The listed methods are the only ones other than ``main`` in the Command interface that do not have ``__dunder__``
       or ``_sunder_`` names.  AsyncCommand (see `Asyncio Applications`_) defines one more.
.. [2] Almost any.  A :ref:`ctx <advanced:Post-Run & Context>` attribute is defined for convenience, but is 100% safe
       to override.  See :ref:`commands:Overriding Command Methods` for more info about other methods.
.. [3] The :func:`~.commands.main` function selects the top-level class that is known to extend :class:`.Command`,
       and calls the :meth:`~.Command.parse_and_run` classmethod on that discovered command class.  For more info
       about how :func:`~.commands.main` picks that class and handles multiple commands, see its API documentation.

----


Asyncio Applications
====================

Commands in applications that use :doc:`asyncio <python:library/asyncio>` should extend :class:`~.AsyncCommand` instead
of :class:`~.Command`.  The ``main`` method within Command classes that extend AsyncCommand should generally be defined
as an ``async`` method / :ref:`coroutine <python:coroutine>`.  For example::

    class MyAsyncCommand(AsyncCommand):
        async def main(self):
            ...


To run an AsyncCommand, both :func:`~.commands.main` and :meth:`~.AsyncCommand.parse_and_run` can be used as if running
a synchronous :class:`~.Command` (as described `above <#parse-run>`__).  The asynchronous version of
:meth:`~.AsyncCommand.parse_and_run` handles calling :func:`python:asyncio.run`.

For applications that need more direct control over how the event loop is run, :meth:`~.AsyncCommand.parse_and_await`
can be used instead.

All of the `supported _sunder_ methods <#supported-sunder-methods>`__ may be overridden with either synchronous or
async versions, and :ref:`parameters:Action` methods may similarly be defined either way as well.


Advanced
========

Inheritance
-----------

One of the benefits of defining Commands as classes is that we can take advantage of the standard inheritance that
Python already provides for common Parameters, methods, or initialization steps.

The preferred way to define a subcommand takes advantage of this in that it can be defined by
:ref:`extending a parent Command <subcommands:Automatic Registration>`.  This helps to avoid parameter name conflicts,
and it enables users to provide common options anywhere in their CLI arguments without needing to be aware of parser
behavior or how nested commands were defined.

Some of the benefits of being able to use inheritance for Commands, and some of the patterns that it enables, that
may require more work with other parsers:

- Logger configuration and other common initialization tasks can be handled once, automatically for all subcommands.
- Parent Commands can define common properties and methods used (or overridden) by its subcommands.

    - A parent Command may define a ``main`` method that calls a method that each subcommand is expected to implement
      for subcommand-specific implementations.
    - If a parent Command's ``main`` implementation is able to do what is necessary for all subcommands except for one,
      only that one needs to override its parent's implementation.
- If multiple subcommands share a set of common Parameters between each other that would not make sense to be defined
  on the parent Command, and are not shared by other subcommands, then an intermediate subclass of their parent Command
  :ref:`can be defined with those common Parameters <subcommands:Shared Common Parameters>`, which those subcommands
  would then extend instead.


Overriding Command Methods
--------------------------

The number of methods defined in the base :class:`.Command` class is intentionally low in order to allow subclasses the
freedom to define whatever attributes and methods that they need.  The :meth:`~.Command.__call__`,
:meth:`~.Command.parse`, and :meth:`~.Command.parse_and_run` methods are not intended to be overridden.

Some ``_sunder_``\ [4]_ methods are intended to be overridden, some are not intended to be overridden, and others may
be safe to override in some situations, but should otherwise be called via ``super()`` to maintain normal functionality.


Overriding ``main``
^^^^^^^^^^^^^^^^^^^

The vast majority of commands can safely override :meth:`.Command.main` without calling ``super().main()``.
If, however, a command uses positional :ref:`parameters:Action` methods, then that command should either not define
a ``main`` method (i.e., it should not override :meth:`.Command.main`) or it should include a call of ``super().main()``
to maintain the expected behavior.  The default implementation of the ``main`` method returns an int representing the
number of :ref:`parameters:Action` methods that were called, which can be used by subclasses calling ``super().main()``
to adjust their behavior based on that result.


Supported ``_sunder_`` Methods
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- ``_pre_init_actions_``: Not intended to be overridden.  Handles ``--help`` (and similar special actions, if defined)
  and some :obj:`.action_flag` validation.
- ``_init_command_``: Intended to be overridden - the base implementation does not do anything.  See
  `Using _init_command_`_ for more info.
- ``_before_main_``: If any ``before_main`` :obj:`action_flags<.action_flag>` are defined, the original implementation
  should be called via ``super()._before_main_()``.  When not using any action flags, this method can safely be
  overridden without calling the original.  See `Using _before_main_`_ for more info.
- ``_after_main_``: Similar to ``_before_main_``, the need to call the original via ``super()`` depends on the presence
  of ``after_main`` action flags.  This method may be used analogously to a ``finally:`` clause for a command if
  the :ref:`always_run_after_main<configuration:Error Handling Options>` option is enabled / True.


Initialization Methods
^^^^^^^^^^^^^^^^^^^^^^

Using ``_init_command_``
""""""""""""""""""""""""

The recommended way to handle initializing logging, or other common initialization steps, is to do so
in :meth:`.Command._init_command_` - example::

    class BaseCommand(Command):
        sub_cmd = SubCommand(help='The command to run')
        verbose = Counter('-v', help='Increase logging verbosity (can specify multiple times)')

        def _init_command_(self):
            log_fmt = '%(asctime)s %(levelname)s %(name)s %(lineno)d %(message)s' if self.verbose > 1 else '%(message)s'
            level = logging.DEBUG if self.verbose else logging.INFO
            logging.basicConfig(level=level, format=log_fmt)


There is no need to call ``super()._init_command_()`` within the method - its default implementation does nothing.  This
method is intended to be overridden.

The primary reason that this method is provided is to improve user experience when they specify ``--help`` or an
invalid command.  Any initialization steps will incur some level of overhead, and generally no initialization
should be necessary if the user is looking for help text or if they did not provide valid arguments.  Any extra work
that is not necessary will result in a (potentially very perceptibly) slower response, regardless of the parsing
library that is used.

This method is called after :meth:`.Command._pre_init_actions_` and before :meth:`.Command._before_main_`.


Using ``_before_main_``
"""""""""""""""""""""""

Before ``_init_command_`` was available, this was the recommended way to handle initialization steps.  That is no
longer the case.

.. important::
    If ``_before_main_`` is overridden, it is important to make sure that ``super()._before_main_()`` is called from
    within it.  If the ``super()...`` call is missed, then most :ref:`before_main action flags<parameters:ActionFlag>`
    will not be processed.  ``--help`` and other ``always_available`` :ref:`ActionFlags<actionflag_init_params>`
    are not affected by this method.

This method is called after :meth:`.Command._init_command_` and before :meth:`.Command.main`.


Using ``__init__``
""""""""""""""""""

If you don't mind the extra overhead before ``--help``, or if you have ``always_available``
:ref:`ActionFlags<actionflag_init_params>` that require the same initialization steps as the rest of the Command,
then you can include those initialization steps in ``__init__`` instead.  The base :class:`.Command` class
has no ``__init__`` method, so there is no need to call ``super().__init__()`` if you define it - example::

    class Base(Command):
        sub_cmd = SubCommand()
        verbose = Counter('-v', help='Increase logging verbosity (can specify multiple times)')

        def __init__(self):
            log_fmt = '%(asctime)s %(levelname)s %(name)s %(lineno)d %(message)s' if self.verbose > 1 else '%(message)s'
            level = logging.DEBUG if self.verbose else logging.INFO
            logging.basicConfig(level=level, format=log_fmt)


----

.. [4] Why ``_sunder_`` names? Mostly for the same reason that `the Enum module uses them
       <https://stackoverflow.com/a/52006681/19070573>`__.
