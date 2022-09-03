Subcommands
***********

Subcommands provide a way of organizing Commands by separating distinct functionalities and options that are specific
to those functionalities.

For a :class:`.Command` to support subcommands, it must have a :class:`.SubCommand` Parameter.  If other
:ref:`Positional Parameters<parameters:Positionals>` are present in the Command, the position of the SubCommand
Parameter determines the relative position for the argument(s) that select which subcommand should be executed.

A given Command may only contain one SubCommand Parameter, but multiple Commands can be registered with it as
subcommands, and each of those subcommands can have their own SubCommand Parameter.  It is possible to have multiple
levels of nested subcommands.

.. _subcommand_init_params:

**Initialization parameters for SubCommand Parameters:**

:title: The title to use for help text sections containing the choices for the Parameter.  Defaults to
  ``Subcommands``.
:description: The description to be used in help text for the Parameter.
:local_choices: If some choices should be handled in the Command that the SubCommand Parameter is in, they should
  be specified here.  Supports either a mapping of ``{choice: help text}`` or a collection of choice values.
:nargs: Not supported.  Automatically calculated / maintained based on registered choices (subcommand target
  Commands).
:type: Not supported.
:choices: Not supported - all other choices are populated by registering subcommands.



Automatic Registration
======================

Given a :class:`.Command` class has a :class:`.SubCommand` Parameter, any classes that extend that Command will
automatically be registered as subcommands of the Command that they extend.

.. _subcommand_cls_params:

When defining a subcommand class that extends a base Command, in addition to the other options that are supported when
:ref:`initializing Commands<commands:Initializing Commands>`, the following keyword-only parameters may also be
provided along with the class that it extends:

:choice: The value a user must provide to choose the target subcommand.  Spaces are supported.  By default, the
  lower-case (snake_case) name of the subcommand class is used.  I.e., if the class is called ``Foo``, then the
  automatically generated choice value will be ``foo``.  If the class is called ``FooBar``, then the choice will be
  ``foo_bar``.
:choices: If multiple choices should be supported as aliases for selecting a given target subcommand, they can be
  provided via ``choices`` instead of ``choice``.
:help: The help text to display for the subcommand when viewing the parent Command's help text.


Given the following overly-simplistic
`basic example <https://github.com/dskrypa/cli_command_parser/blob/main/examples/basic_subcommand.py>`__::

    class Base(Command):
        sub_cmd = SubCommand()

    class Foo(Base, help='Print foo'):
        def main(self):
            print('foo')

    class Bar(Base, help='Print bar'):
        def main(self):
            print('bar')


We can see from the help text that it is aware of its subcommands::

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



Inheritance
===========

One of the benefits of defining Commands as classes is that we can take advantage of the standard inheritance that
Python already provides for common Parameters, methods, or initialization steps.

Using _before_main_
-------------------

The current recommended way to handle initializing logging, or other common initialization steps, is to do so
in :meth:`.Command._before_main_` - example::

    class BaseCommand(Command):
        sub_cmd = SubCommand(help='The command to run')
        verbose = Counter('-v', help='Increase logging verbosity (can specify multiple times)')

        def _before_main_(self):
            super()._before_main_()
            log_fmt = '%(asctime)s %(levelname)s %(name)s %(lineno)d %(message)s' if self.verbose > 1 else '%(message)s'
            level = logging.DEBUG if self.verbose else logging.INFO
            logging.basicConfig(level=level, format=log_fmt)


.. important::
    It is important to make sure that ``super()._before_main_()`` is called from ``_before_main_`` if it is
    overwritten.  If the ``super()...`` call is missed, then ``--help`` or other
    :ref:`before_main action flags<parameters:ActionFlag>` will not be processed.

The primary reason for this recommendation is to avoid the overhead of those initialization steps if a user specifies
``--help`` or an invalid command, to improve the user experience by providing a faster response.  Any extra work that
is not necessary will result in a slower response, regardless of the parsing library that is used.


Using __init__
--------------

If your program uses other :ref:`ActionFlags<parameters:ActionFlag>`, or if you don't mind the extra overhead before
``--help``, then you can include the initialization steps in ``__init__`` instead.  The base :class:`.Command` class
has no ``__init__`` method, so there is no need to call ``super().__init__()`` if you define it - example::

    class Base(Command):
        sub_cmd = SubCommand()
        verbose = Counter('-v', help='Increase logging verbosity (can specify multiple times)')

        def __init__(self):
            log_fmt = '%(asctime)s %(levelname)s %(name)s %(lineno)d %(message)s' if self.verbose > 1 else '%(message)s'
            level = logging.DEBUG if self.verbose else logging.INFO
            logging.basicConfig(level=level, format=log_fmt)



Nested Subcommands
==================

Using the example script that is a `fake wrapper around a hypothetical REST API
<https://github.com/dskrypa/cli_command_parser/blob/main/examples/rest_api_wrapper.py>`__, we can see an example of
two levels of subcommands, and another way that we can take advantage of inheritance::

    class ApiWrapper(Command):
        sub_cmd = SubCommand(help='The command to run')
        with ParamGroup('Common'):
            verbose = Counter('-v', help='Increase logging verbosity (can specify multiple times)')
            env = Option('-e', choices=('dev', 'qa', 'uat', 'prod'), default='prod', help='Environment to connect to')
        ...

    class Show(ApiWrapper, help='Show an object'):
        ...

    # region Find subcommands

    class Find(ApiWrapper, help='Find objects'):
        sub_cmd = SubCommand(help='What to find')
        limit: int = Option('-L', default=10, help='The number of results to show')

        def main(self):
            for obj in self.find_objects():
                print(obj)

        def find_objects(self):
            raise NotImplementedError

    class FindFoo(Find, choice='foo', help='Find foo objects'):
        query = Positional(help='Find foo objects that match the specified query')

        def find_objects(self):
            log.debug(f'Would have run query={self.query!r} in env={self.env}, returning fake results')
            return ['a', 'b', 'c']

    class FindBar(Find, choice='bar', help='Find bar objects'):
        pattern = Option('-p', help='Pattern to find')
        show_all = Flag('--all', '-a', help='Show all (default: only even)')

        def find_objects(self):
            objects = {chr(i): i % 2 == 0 for i in range(97, 123)}
            if not self.show_all:
                objects = {c: even for c, even in objects.items() if even}
            if self.pattern:
                objects = {c: even for c, even in objects.items() if fnmatch(c, self.pattern)}
            return objects

    class FindBaz(Find, choices=('baz', 'bazs'), help='Find baz objects'):
        ...

    # endregion


In that example, both the ``Show`` and ``Find`` subcommands share the common logging initialization, and they share the
common ``env`` Option for selecting an environment to connect to::

    $ rest_api_wrapper.py -h
    usage: rest_api_wrapper.py {show,sync,find} [--verbose [VERBOSE]] [--env {dev,qa,uat,prod}] [--help]

    Subcommands:
      {show,sync,find}
        show                      Show an object
        sync                      Sync group members
        find                      Find objects

    Optional arguments:
      --help, -h                  Show this help message and exit (default: False)

    Common options:
      --verbose [VERBOSE], -v [VERBOSE]
                                  Increase logging verbosity (can specify multiple times) (default: 0)
      --env {dev,qa,uat,prod}, -e {dev,qa,uat,prod}
                                  Environment to connect to (default: 'prod')


Since the different types of objects have different criteria for finding them, it helps to split the ``Find``
subcommand further so that each one only has the Parameters relevant for finding objects of that type.  To avoid name
conflicts with other type-specific subcommands related to the same types, each ``Find`` subcommand uses a prefix for
its name, and the ``choice=`` param to specify what should be provided on the CLI::

    $ rest_api_wrapper.py find -h
    usage: rest_api_wrapper.py find {foo,bar,baz} [--verbose [VERBOSE]] [--env {dev,qa,uat,prod}] [--help] [--limit LIMIT]

    Subcommands:
      {foo,bar,baz}
        foo                       Find foo objects
        bar                       Find bar objects
        baz                       Find baz objects

    ...


We're able to take advantage of inheritance again in ``Find`` where we only need to define ``main`` once, and we can
have each subcommand define the method that is called by ``main`` to produce results.



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



Shared Common Parameters
========================

In some situations, use cases arise for subcommands that are similar to each other but not to other subcommands of the
same parent Command.  In these cases, it may be desirable to define the Parameters that are common to those similar
subcommands in a common base class so they don't need to be repeated in each subcommand class.

This can be accomplished by defining a subclass of the target parent Command (which contains the :class:`.SubCommand`
Parameter that should be used to register the similar subcommands) that also extends :class:`python:abc.ABC` to store
the common Parameters.

A `full example <https://github.com/dskrypa/cli_command_parser/blob/main/examples/complex/shared_params.py>`__ is
available in the examples directory, but the basic pattern is the same as the following simplified example::

    from abc import ABC
    from cli_command_parser import Command, SubCommand, Option

    class Base(Command):
        sub_cmd = SubCommand()

    class Common(Base, ABC):
        a = Option()
        b = Option()

    class Foo(Common):
        c = Option()

    class Bar(Common):
        d = Option()


Given the above example, ``Foo`` and ``Bar`` will be automatically registered as subcommands of ``Base``.  They will
both inherit Options ``a`` and ``b`` from ``Common``, but ``Common`` will not be available as a subcommand choice (it
won't be shown in help text, and it will not be selectable during parsing).

.. note::

    It is not currently possible to use a mixin class to define reusable common Parameters.
