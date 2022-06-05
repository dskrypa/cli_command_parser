Configuration
*************

Configuration options can be specified as keyword arguments when
:ref:`initializing Commands<commands:Initializing Commands>`.  It is also possible to provide either a dictionary of
options or an instance of :class:`.CommandConfig`.


Command Metadata
================

The following options cannot be provided in a CommandConfig object or ``config`` dictionary, and must be specified as
keyword arguments when defining a Command subclass.  All of these options are optional:

:choice: SubCommand value that should be mapped to this command, if different than this class's (lower case)
  name.  Only used when the Command is a subcommand of another Command.
:prog: The name of the program (default: ``sys.argv[0]``)
:usage: Usage message to be printed with help text or when incorrect arguments are provided (default:
  auto-generated)
:description: Description of what the program does.  If the Command contains a class-level docstring, then that
  value will be used unless this parameter is provided.
:epilog: Text to follow parameter descriptions
:help: Help text to be displayed as a SubCommand option.  Ignored for top-level commands.
:config: A :class:`python:dict` or :class:`.CommandConfig` object containing the config options to use.  May not
  be combined with separate kwargs that would be stored in a CommandConfig object.


Configuration Options
=====================

Configuration options supported by :class:`.CommandConfig`.  For convenience, they may also be specified as keyword
arguments when defining a Command subclass:


Error Handling Options
----------------------

:error_handler: The :class:`~.error_handling.ErrorHandler` to be used by :meth:`.Command.__call__` to wrap
  :meth:`.Command.main`, or None to disable error handling.  (default:
  :obj:`~.error_handling.extended_error_handler`)
:always_run_after_main: Whether :meth:`.Command._after_main_` should always be called, even if an exception
  was raised in :meth:`.Command.main` (similar to a ``finally`` block) (default: False)


ActionFlag Options
------------------

:multiple_action_flags: Whether multiple action_flag methods are allowed to run if they are all specified
  (default: True)
:action_after_action_flags: Whether action_flag methods are allowed to be combined with a positional Action
  method in a given CLI invocation (default: True)


Parsing Options
---------------

:ignore_unknown: Whether unknown arguments should be ignored (default: False / raise an exception when unknown
  arguments are encountered)
:allow_missing: Whether missing required arguments should be allowed (default: False / raise an exception when
  they are missing)
:allow_backtrack: Whether the parser is allowed to backtrack or not when a Positional parameter follows a
  parameter with variable :class:`.Nargs`, and not enough arguments are available to fulfil that Positional's
  requirements (default: True)


Usage & Help Text Options
-------------------------

:add_help: Whether the ``--help`` / ``-h`` action_flag should be added (default: True)
:use_type_metavar: Whether the metavar for Parameters that accept values should default to the name of the
  specified type (default: False / the name of the parameter)
:show_defaults: Whether default values for Parameters should be automatically included in help text or not,
  and related settings.  Acceptable values are defined as
  `enum flags <https://docs.python.org/3/library/enum.html#flag>`__ that can be combined.  May be overridden on a
  per-Parameter level by using the :ref:`show_default<common_init_params>` param. See :class:`.ShowDefaults` for
  more info.
:show_group_tree: Whether there should be a visual indicator in help text for the parameters that are members
  of a given group.  See :ref:`documentation:Group Formatting` for more info.  (default: False)
:show_group_type: Whether mutually exclusive / dependent groups should include that fact in their
  descriptions (default: True)
:command_formatter: A callable that accepts 2 arguments, a :class:`.Command` class (not object) and a
  :class:`.CommandParameters` object, and returns a :class:`.CommandHelpFormatter` (or a class that implements the
  same methods).
:param_formatter: A callable that accepts a :class:`.Parameter` or :class:`.ParamGroup` and returns a
  :class:`.ParamHelpFormatter` (or a class that implements the same methods).
:extended_epilog: Whether the program version, author email, and documentation URL should be included in the
  help text epilog, if they were successfully detected (default: True)
:show_docstring: Whether the top level script's docstring should be included in generated documentation
  (default: True)
