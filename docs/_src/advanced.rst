Advanced Usage
**************

Dynamic Parameter Defaults
==========================

In most cases, a simple default value for a given Parameter is sufficient, but sometimes it can be helpful to
dynamically generate a default based on the runtime environment or the value of other parsed arguments.

Most Parameters that support a using a :ref:`parameters:parameters:default_cb` also support registering a method in a
Command as their default callback.  A very simple example that references another Parameter::

    class MyCommand(Command):
        foo = Flag('-f')
        bar = Option('-b')

        @bar.register_default_cb
        def _bar_default_cb(self):
            return str(self.foo)


In the above example, if ``--bar baz`` was provided, then within MyCommand, ``self.bar`` would be ``'baz'``.  If no
value was provided, then it would be the string ``'True'`` or ``'False'``, depending on whether ``--foo`` was specified.


Post-Run & Context
==================

While Commands are intended to be self-contained, it is possible to interact with them after calling
:meth:`.Command.parse_and_run`, which returns the instance of the executed Command.  Example::

    >>> class Foo(Command):
    ...     bar = Flag('--no-bar', '-B', default=True)
    ...     baz = Positional(nargs='+')
    ...
    ...     def main(self):
    ...         print(f'{self.bar=}, {self.baz=}')
    ...

    >>> foo = Foo.parse_and_run(['test', 'one', '-B'])
    self.bar=False, self.baz=['test', 'one']

    >>> foo
    <__main__.Foo at 0x26dfcad6e00>


Parameter values are still accessible, as they were from inside the command::

    >>> foo.bar
    False


While it is also accessible while running, it's easier to inspect the parsing :class:`~.context.Context` in an
interactive terminal after parsing and running::

    >>> foo.ctx
    <lib.cli_command_parser.context.Context at 0x26dfa94fbb0>

    >>> foo.ctx.params
    <CommandParameters[command=Foo, positionals=1, options=2]>

    >>> foo.ctx.get_parsed()
    {
        'baz': ['test', 'one'],
        'bar': False,
        'help': False
    }

    >>> foo.ctx.argv
    ['test', 'one', '-B']


The Context object stores information about the Command's configuration, the parameters defined in that Command
(organized in a :class:`.CommandParameters` object), the input, and a dictionary containing the parsed values.  The
``help`` entry in the above example is the automatically added :class:`.ActionFlag` that represents
the ``--help`` action::

    >>> foo.ctx.params.action_flags
    [ActionFlag('help', action='store_const', const=True, default=False, required=False, help='Show this help message and exit', order=-inf, before_main=True)]

    >>> foo.ctx.params.action_flags[0].func
    <function lib.cli_command_parser.actions.help_action(self)>


The name is automatically generated to avoid potential name conflicts with other parameters / methods in Commands.  It
will not always have the same number in the name.

Since its :paramref:`.ActionFlag.order` is negative infinity, the :func:`~.actions.help_action` will always
take precedence over any other ActionFlag.  There is special handling in the parser for specifically allowing that
action to be processed when parsing would otherwise fail.


Accessing Raw Argument Values
=============================

Parsed Args as a Dictionary
---------------------------

A :func:`.get_parsed` helper function exists for retrieving a dictionary of parsed arguments without needing to deal
with the ``ctx`` attribute like in the above example.  The get_parsed helper function will continue to work, even if
a given command overrides the ``ctx`` attribute with a different value.

Example using the same Command as above::

    >>> get_parsed(foo)
    {
        'baz': ['test', 'one'],
        'bar': False,
        'help': False
    }


As an added convenience, this helper function accepts a :class:`python:collections.abc.Callable` object to filter the
parsed dict to only the keys that match that callable's signature.  Only VAR_KEYWORD parameters (i.e., ``**kwargs``) are
excluded - if any parameters of the given callable cannot be passed as a keyword argument, that must be handled after
calling get_parsed.

Example::

    >>> def test(bar, **kwargs):
    ...     pass
    ...

    >>> get_parsed(foo, test)
    {'bar': False}


Parameters with Overridden Names
--------------------------------

In some cases, subcommands may have Parameters with names that override those defined in parent Commands.  A common
example of this occurs when multiple levels of subcommands exist, where each level has a ``sub_cmd = SubCommand()``.

In such cases, it is sometimes necessary for a parent Command to know the raw parsed value for that Parameter.  The
:func:`.get_raw_arg` function simplifies the process of accessing that value.

Given the following simplified example Commands::

        class Foo(Command):
            sub_cmd = SubCommand()

        class Bar(Foo):
            sub_cmd = Positional()


We can see that accessing the ``sub_cmd`` attribute directly returns the parsed subcommand's result::

    >>> cmd = Foo.parse(['bar', 'baz'])

    >>> cmd.sub_cmd
    'baz'


The raw parsed value for both levels can be retrieved using :func:`.get_raw_arg`::

    >>> get_raw_arg(cmd, Foo.sub_cmd)
    ['bar']

    >>> get_raw_arg(cmd, Bar.sub_cmd)
    'baz'


Note that the raw value for some Parameters like SubCommand may be a list instead of a string.  This is due to the way
that values containing spaces are supported.

From within a Command instance method, ``self`` would be used instead of the ``cmd`` variable from the above examples.
E.g.::

    def main(self):
        value = get_raw_arg(self, Foo.sub_cmd)
        print(value)


Alternatively, it is possible to define Parameters with double-underscore names to take advantage of native name
mangling.  Doing do results in direct access within a given Command returning the raw value that was parsed at that
level.  Example::

    >>> class Foo(Command):
    ...     __sub_cmd = SubCommand()
    ...     def _init_command_(self):
    ...         print(f'Foo: {self.__sub_cmd}')
    ...
    ... class Bar(Foo):
    ...     __sub_cmd = Positional()
    ...     def main(self):
    ...         print(f'Bar: {self.__sub_cmd}')
    ...

    >>> Foo.parse_and_run(['bar', 'baz'])
    Foo: bar
    Bar: baz


In the above example, if ``__sub_cmd`` had been named ``sub_cmd`` instead, then the output would have been::

    Foo: baz
    Bar: baz



Mixing Actions & ActionFlags
============================

The `build_docs.py <https://github.com/dskrypa/cli_command_parser/blob/main/bin/build_docs.py>`__ script that is used
to build the documentation for this project is an example of a Command that includes both :ref:`parameters:Action`
methods and ActionFlags.  Additionally, some of the methods even have the two decorators stacked so that they can be
called either way.

Example snippet::

    class BuildDocs(Command, description='Build documentation using Sphinx'):
        action = Action()
        verbose = Counter('-v', help='Increase logging verbosity (can specify multiple times)')
        dry_run = Flag('-D', help='Print the actions that would be taken instead of taking them')

        def __init__(self):
            # Initialize logging, etc
            ...

        @action(default=True, help='Run sphinx-build')
        def sphinx_build(self):
            # Call sphinx-build in a subprocess
            ...

        @before_main('-c', help='Clean the docs directory before building docs', order=1)
        @action(help='Clean the docs directory')
        def clean(self):
            # Clean up the build dir to remove old generated RST files / HTML
            ...

        @before_main('-u', help='Update RST files', order=2)
        def update(self):
            # Re-generate RST files for API docs
            ...

        @after_main('-o', help='Open the docs in the default web browser after running sphinx-build')
        def open(self):
            ...

        @action('backup', help='Test the RST backup')
        def backup_rsts(self):
            # Backup the existing auto-generated RST files
            ...


The help text (note that ``clean`` appears in both the ``Actions`` section and the optional args section)::

    $ build_docs.py -h
    usage: build_docs.py {clean,backup} [--verbose [VERBOSE]] [--dry-run] [--clean] [--update] [--open] [--help]

    Build documentation using Sphinx

    Actions:
      {clean,backup}
        (default)                 Run sphinx-build
        clean                     Clean the docs directory
        backup                    Test the RST backup

    Optional arguments:
      --verbose [VERBOSE], -v [VERBOSE]
                                  Increase logging verbosity (can specify multiple times) (default: 0)
      --dry-run, -D               Print the actions that would be taken instead of taking them
      --clean, -c                 Clean the docs directory before building docs
      --update, -u                Update RST files
      --open, -o                  Open the docs in the default web browser after running sphinx-build
      --help, -h                  Show this help message and exit


If the script is called with ``build_docs.py clean`` or ``build_docs.py backup``, then only the ``clean`` or ``backup``
method would be called, respectively.  If neither action was specified, then the ``sphinx_build`` method would be
called because it is marked as the default action (``@action(default=True, ...``).

When called without a positional action, but with action flags specified, then each of the methods enabled via
specified flags and ``sphinx_build`` will be called.  For example, running ``build_docs.py -uco`` would result in
the following methods being called in the following order:

- ``clean`` (before main, order=1)
- ``update`` (before main, order=2)
- ``sphinx_build`` (main, default action)
- ``open`` (after main)

Higher order values result in being called later, when specified.

It is technically possible to call the same method both via action and flag, such as ``build_docs.py clean -c``.
Nothing in this library will prevent that.  If this is problematic, but you want to stack decorators like this, then
you should include a check in your application to prevent it from being run twice.
