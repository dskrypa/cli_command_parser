Parameter Groups
****************

Parameters can be grouped so that they are mutually exclusive or mutually dependent, or just to organize them in help
text.  Arbitrary levels of nesting are supported, including mutually dependent groups inside mutually exclusive groups,
and vice versa.

Groups are defined by initializing a :class:`.ParamGroup` as a context manager, and defining the member Parameters
inside the ``with`` block.


.. _group_init_params:

.. rubric:: Initialization Parameters

:name: The name of the group to appear in help text.  Ignored if ``description`` is provided.
:description: The description (header) for this group in help text.  Defaults to ``{name} options`` if ``name`` is
  specified.  If :ref:`configuration:Usage & Help Text Options:show_group_type` is True (the default), and the group
  is mutually exclusive/dependent, then ``(mutually {type})`` will be appended to this text.  If no description or name
  are provided, and ``show_group_type`` is True, then the entire description will default to
  ``Mutually {type} options``, otherwise it will be ``Optional arguments``.
:mutually_exclusive: ``True`` if Parameters in the group are mutually exclusive, ``False`` otherwise.  I.e., if
  one Parameter in the group is provided, then no other Parameter in the group will be allowed.  Cannot be combined
  with ``mutually_dependent``.
:mutually_dependent: ``True`` if Parameters in the group are mutually dependent, ``False`` otherwise.  I.e., if
  one Parameter in the group is provided, then all other Parameters in the group must also be provided.  Cannot be
  combined with ``mutually_exclusive``.
:required: Whether at least one Parameter in the group is required or not.  If it is required, then an exception
  will be raised if the user did not provide a value for any Parameters in the group.  Defaults to ``False``.
:hide: Set this to ``True`` to hide the group and all of its members so they will not be included in usage / help
  text.


One `example <https://github.com/dskrypa/cli_command_parser/blob/main/examples/rest_api_wrapper.py>`__ use case for
a basic group is to indicate that common arguments are accepted by all subcommands::

    class ApiWrapper(Command):
        sub_cmd = SubCommand(help='The command to run')
        with ParamGroup('Common'):
            verbose = Counter('-v', help='Increase logging verbosity (can specify multiple times)')
            env = Option('-e', choices=('dev', 'qa', 'uat', 'prod'), default='prod', help='Environment to connect to')


Using that example, we can see the common options group in a subcommand's help text::

    $ rest_api_wrapper.py show -h
    usage: rest_api_wrapper.py show {foo,bar,baz} [--verbose [VERBOSE]] [--env {dev,qa,uat,prod}] [--help] [--ids IDS]

    Positional arguments:
      {foo,bar,baz}               The type of object to show

    Optional arguments:
      --help, -h                  Show this help message and exit (default: False)
      --ids IDS, -i IDS           The IDs of the objects to show

    Common options:
      --verbose [VERBOSE], -v [VERBOSE]
                                  Increase logging verbosity (can specify multiple times) (default: 0)
      --env {dev,qa,uat,prod}, -e {dev,qa,uat,prod}
                                  Environment to connect to (default: 'prod')


Mutually Exclusive
==================

In the following example, ``wait`` and ``no_wait`` are mutually exclusive - if both are provided, then an exception is
raised.  The ``tasks`` and ``verbose`` parameters are not in the group::

    class TaskRunner(Command):
        tasks = Positional(nargs='+', help='The tasks to run')

        with ParamGroup('Wait Options', mutually_exclusive=True):
            wait: int = Option('-w', default=1, help='Seconds to wait (0 or below to wait indefinitely)')
            no_wait = Flag('-W', help='Do not wait')

        verbose = Counter('-v', help='Increase logging verbosity (can specify multiple times)')


By making a group both mutually exclusive and required, we can ensure that one argument is always provided.  Given the
following `example <https://github.com/dskrypa/cli_command_parser/blob/main/examples/rest_api_wrapper.py>`__ snippet::

    class FindBaz(Find, choice='baz', help='Find baz objects'):
        with ParamGroup(description='Filter Choices', mutually_exclusive=True, required=True):
            foo = Option('-f', metavar='NAME', help='Find baz objects related to the foo object with the specified name')
            bar: int = Option('-b', metavar='ID', help='Find baz objects related to the bar object with the specified ID')

        def find_objects(self):
            if self.foo:
                ...
            else:  # self.bar was provided
                ...


Either argument can be provided, but they cannot be combined::

    $ rest_api_wrapper.py find baz -b 42 -f test
    argument conflict - the following arguments cannot be combined: --foo / -f, --bar / -b (they are mutually exclusive - only one is allowed)


And one of them must be provided::

    $ rest_api_wrapper.py find baz
    arguments missing - the following arguments are required: --foo / -f, --bar / -b


Mutually Dependent
==================

Mutually dependent groups provide a way to enforce that when one argument is provided for a Parameter in the group,
then arguments for all other Parameters in that group must also be provided.  Similar to mutually exclusive groups,
unless the group itself is marked as ``required``, none of the members will be required if no arguments are provided
for any of the other members.

An example can be found :ref:`below <mutually_dependent_example>`.


Combining Group Types
=====================

When nesting a basic group inside of a mutually exclusive group, the members of the basic group can be combined, but
none of the inner basic group members can be combined with the members of the outer exclusive group.  Given the
following `example <https://github.com/dskrypa/cli_command_parser/blob/main/examples/rest_api_wrapper.py>`__ snippet::

    class Sync(ApiWrapper, help='Sync group members'):
        dry_run = Flag('-D', help='Print the actions that would be taken instead of taking them')
        with ParamGroup(mutually_exclusive=True, required=True):
            all = Flag('-a', help='Sync all groups')
            with ParamGroup():  # --role and --group can be combined, but neither can be combined with --all
                role = Option('-r', default='all', choices=('all', 'admin', 'user'), help='Sync members with this role')
                group = Option('-g', help='Sync members for this group')

        def main(self):
            prefix = '[DRY RUN] Would sync' if self.dry_run else 'Syncing'
            roles = ['admin', 'user'] if self.role == 'all' else [self.role]
            groups = [self.group] if self.group else ['foo', 'bar', 'baz']
            for group in groups:
                for role in roles:
                    log.info(f'{prefix} group={group} members with role={role}')


We can see that a member needs to be provided::

    $ rest_api_wrapper.py sync
    arguments missing - the following arguments are required: --all / -a, {--role / -r,--group / -g}

The inner group members can be combined::

    $ examples/rest_api_wrapper.py sync -g foo -r admin
    Syncing group=foo members with role=admin

And neither can be combined with the mutually exclusive ``--all`` Parameter::

    $ rest_api_wrapper.py sync -g foo -a
    argument conflict - the following arguments cannot be combined: --all / -a, {--role / -r,--group / -g} (they are mutually exclusive - only one is allowed)

Any of the valid combos can be combined with the Parameter outside of the group::

    $ rest_api_wrapper.py sync -g foo -D
    [DRY RUN] Would sync group=foo members with role=admin
    [DRY RUN] Would sync group=foo members with role=user

    $ rest_api_wrapper.py sync -aD
    [DRY RUN] Would sync group=foo members with role=admin
    [DRY RUN] Would sync group=foo members with role=user
    [DRY RUN] Would sync group=bar members with role=admin
    [DRY RUN] Would sync group=bar members with role=user
    [DRY RUN] Would sync group=baz members with role=admin
    [DRY RUN] Would sync group=baz members with role=user


.. _mutually_dependent_example:

Similarly, it is also possible to nest mutually dependent groups inside mutually exclusive groups.  Using a refactored
version of the same example::

    class Sync(ApiWrapper, help='Sync group members'):
        dry_run = Flag('-D', help='Print the actions that would be taken instead of taking them')
        with ParamGroup(mutually_exclusive=True, required=True):
            all = Flag('-a', help='Sync all groups')
            with ParamGroup(mutually_dependent=True):
                role = Option('-r', choices=('all', 'admin', 'user'), help='Sync members with this role')
                group = Option('-g', help='Sync members for this group')


We can see the resulting output::

    $ rest_api_wrapper.py sync -g foo
    argument missing - the following argument is required: --role / -r (because --group/-g was provided)

    $ rest_api_wrapper.py sync -r admin
    argument missing - the following argument is required: --group / -g (because --role/-r was provided)

    $ rest_api_wrapper.py sync -r admin -g foo
    Syncing group=foo members with role=admin

    $ rest_api_wrapper.py sync -r admin -g foo -a
    argument conflict - the following arguments cannot be combined: --all / -a, {--role / -r,--group / -g} (they are mutually exclusive - only one is allowed)


How it Works
------------

The nesting of exclusive / dependent (and basic) groups can work either way, and they can be nested multiple levels
deep.  They can also contain nested groups of the same mutual type.

Mutually Exclusive Outer Group
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Given a mutually exclusive group ``A`` that contains a mutually dependent group ``B``, if any member of ``B`` is
provided, then all members of ``B`` must be provided, but no other members of ``A`` (that are not members of ``B``) may
be provided.

Given a mutually exclusive group ``A`` that contains parameters ``x`` and ``y`` and a normal group ``B``, which
contains parameters ``c`` and ``d``, then similar rules apply.  It is possible to provide any one of ``x``, ``y``,
``c``, or ``d``, but only ``c`` and ``d`` can be combined.

Mutually Dependent Outer Group
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Given a mutually dependent group ``C`` that contains a mutually exclusive group ``D``, if any member of ``C`` is
provided, then all members of ``C`` (that are not members of ``D``) must be provided, and one and only one member of
``D`` must be provided.

Given a mutually dependent group ``A`` that contains parameters ``x`` and ``y`` and a normal group ``B``, which
contains parameters ``c`` and ``d``, then similar rules apply.  If any of ``x``, ``y``, ``c``, or ``d`` are provided,
then ``x`` and ``y`` must always be provided, and one or both of ``c`` and ``d`` must be provided.

Examples
^^^^^^^^

The following `example <https://github.com/dskrypa/cli_command_parser/blob/main/examples/grouped_action_flags.py>`__
demonstrates combinations in both directions for nested mutually exclusive / dependent groups using
:ref:`ActionFlags<parameters:ActionFlag>` that simply print their corresponding letter::

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
