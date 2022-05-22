Advanced Usage
==============

Post-Run & Context
------------------

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
        'ActionFlag#2671379799232': False
    }

    >>> foo.ctx.argv
    ['test', 'one', '-B']


The Context object stores information about the Command's configuration, the parameters defined in that Command
(organized in a :class:`.CommandParameters` object), the input, and a dictionary containing the parsed values.  The
``ActionFlag#2671379799232`` entry in the above example is the automatically added :class:`.ActionFlag` that represents
the ``--help`` action::

    >>> foo.ctx.params.action_flags
    [ActionFlag('ActionFlag#2671379799232', action='store_const', const=True, default=False, required=False, help='Show this help message and exit', order=-inf, before_main=True)]

    >>> foo.ctx.params.action_flags[0].func
    <function lib.cli_command_parser.actions.help_action(self)>


The name is automatically generated to avoid potential name conflicts with other parameters / methods in Commands.  It
will not always have the same number in the name.

Since its :paramref:`.ActionFlag.order` is negative infinity, the :func:`~.actions.help_action` will always
take precedence over any other ActionFlag.  There is special handling in the parser for specifically allowing that
action to be processed when parsing would otherwise fail.


Mixing Actions & ActionFlags
----------------------------

The `build_docs.py <https://github.com/dskrypa/cli_command_parser/blob/main/bin/build_docs.py>`__ script that is used
to build the documentation for this project is an example of a Command that includes both :ref:`Action` methods and
ActionFlags.  Additionally, some of the methods even have the two decorators stacked so that they can be called either
way.

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
    usage: build_docs.py {clean,backup} [--verbose [VERBOSE]] [--dry_run] [--clean] [--update] [--open] [--help]

    Build documentation using Sphinx

    Actions:
      {clean,backup}
        (default)                 Run sphinx-build
        clean                     Clean the docs directory
        backup                    Test the RST backup

    Optional arguments:
      --verbose [VERBOSE], -v [VERBOSE]
                                  Increase logging verbosity (can specify multiple times) (default: 0)
      --dry_run, -D               Print the actions that would be taken instead of taking them (default: False)
      --clean, -c                 Clean the docs directory before building docs (default: False)
      --update, -u                Update RST files (default: False)
      --open, -o                  Open the docs in the default web browser after running sphinx-build (default: False)
      --help, -h                  Show this help message and exit (default: False)


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


Nested ParamGroups
------------------

It is possible to nest :ref:`ParamGroups<ParamGroup>` so that a mutually exclusive group contains a mutually
dependent group, and vice versa.  This applies to any nesting depth.

Given a mutually exclusive group ``A`` that contains a mutually dependent group ``B``, if any member of ``B`` is
provided, then all members of ``B`` must be provided, but no other members of ``A`` (that are not members of ``B``) may
be provided.

Given a mutually dependent group ``C`` that contains a mutually exclusive group ``D``, if any member of ``C`` is
provided, then all members of ``C`` (that are not members of ``D``) must be provided, and one and only one member of
``D`` must be provided.

The following `example <https://github.com/dskrypa/cli_command_parser/blob/main/examples/grouped_action_flags.py>`__
will demonstrate this with :ref:`ActionFlags<ActionFlag>` that simply print their corresponding letter::

    class GroupedFlags(Command):
        with ParamGroup(mutually_exclusive=True):
            @before_main('-a', order=1)
            def action_a(self):
                print('a')

            @before_main('-b', order=2)
            def action_b(self):
                print('b')

            with ParamGroup(mutually_dependent=True):
                @before_main('-c', order=3)
                def action_c(self):
                    print('c')

                @before_main('-d', order=4)
                def action_d(self):
                    print('d')

        with ParamGroup(mutually_dependent=True):
            @after_main('-w', order=1)
            def action_w(self):
                print('w')

            @after_main('-x', order=2)
            def action_x(self):
                print('x')

            with ParamGroup(mutually_exclusive=True):
                @after_main('-y', order=3)
                def action_y(self):
                    print('y')

                @after_main('-z', order=4)
                def action_z(self):
                    print('z')

        def main(self):
            print('main')


Example output for the mutually dependent group nested inside the mutually exclusive group::

    $ grouped_action_flags.py -a
    a
    main

    $ grouped_action_flags.py -ab
    argument conflict - the following arguments cannot be combined: --action_a / -a, --action_b / -b (they are mutually exclusive - only one is allowed)

    $ grouped_action_flags.py -abc
    argument conflict - the following arguments cannot be combined: --action_a / -a, --action_b / -b, {--action_c / -c,--action_d / -d} (they are mutually exclusive - only one is allowed)

    $ grouped_action_flags.py -c
    argument missing - the following argument is required: --action_d / -d (because --action_c/-c was provided)

    $ grouped_action_flags.py -cd
    c
    d
    main


Example output for the mutually exclusive group nested inside the mutually dependent group::

    $ grouped_action_flags.py -w
    arguments missing - the following arguments are required: --action_x / -x, {--action_y / -y,--action_z / -z} (because --action_w/-w was provided)

    $ grouped_action_flags.py -wx
    argument missing - the following argument is required: {--action_y / -y,--action_z / -z} (because --action_w/-w, --action_x/-x were provided)

    $ grouped_action_flags.py -wxy
    main
    w
    x
    y

    $ grouped_action_flags.py -wxyz
    argument conflict - the following arguments cannot be combined: --action_y / -y, --action_z / -z (they are mutually exclusive - only one is allowed)
