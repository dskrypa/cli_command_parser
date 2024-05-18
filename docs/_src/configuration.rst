Configuration
*************

Configuration options can be specified as keyword arguments when
:ref:`initializing Commands<commands:Defining Commands>`.  It is also possible to provide either a dictionary of
options or an instance of :class:`.CommandConfig`.


Command Metadata
================

The following options cannot be provided in a CommandConfig object or ``config`` dictionary, and must be specified as
keyword arguments when defining a Command subclass.  All of these options are optional:

:choice: SubCommand value that should be mapped to this command, if different than this class's (lower, camel case)
  name.  Only used when the Command is a subcommand of another Command.  If necessary, it is possible to prevent
  automatic registration as a subcommand choice entirely by using ``choice=None`` (additionally, no value should be
  provided for ``choices``).
:choices: SubCommand values to map to this command.  Similar to ``choice``, but accepts multiple values.  A mapping
  of ``{choice: help text}`` may be provided to customize the help text displayed for each choice.
:prog: The name of the program (default: based on ``sys.argv[0]`` or entry_points or the name of the file in which the
  Command was defined)
:doc_name: The name of the program / title to use in documentation
:usage: Usage message to be printed with help text or when incorrect arguments are provided (default:
  auto-generated)
:description: Description of what the program does.  If the Command contains a class-level docstring, then that
  value will be used unless this parameter is provided.
:epilog: Text to follow parameter descriptions
:help: Help text to be displayed as a SubCommand option.  Ignored for top-level commands.
:config: A :class:`python:dict` or :class:`.CommandConfig` object containing the config options (see below) to use.
  May not be combined with separate kwargs that would be stored in a CommandConfig object.


Configuration Options
=====================

Configuration options supported by :class:`.CommandConfig`.  For convenience, they may also be specified as keyword
arguments when defining a Command subclass:


Error Handling Options
----------------------

:error_handler: The :class:`.ErrorHandler` to be used by :meth:`.Command.__call__` to wrap :meth:`.Command.main`, or
  None to disable error handling.  Defaults to :obj:`~.error_handling.extended_error_handler`.  See
  :doc:`error_handlers` for more details.
:always_run_after_main: Whether :meth:`.Command._after_main_` should always be called, even if an exception
  was raised in :meth:`.Command.main` (similar to a ``finally`` block) (default: False)


Parameter Options
-----------------

:allow_annotation_type: Whether inferring Parameter types from type annotations should be enabled (default: True).
  When enabled/allowed, if a type annotation is detected for a given Parameter, then it will be used as if that type
  had been specified via ``type=...``.  When both an annotation and an explicit ``type=...`` are present, then the
  ``type`` argument takes precedence.  When disabled, type annotations will not be inspected.  If no ``type`` is
  specified, then the default type (usually ``str``) for that Parameter will be used.


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
:option_name_mode: How the default long form that is added for Option/Flag/Counter/etc. Parameters should handle
  underscores/dashes.  See :class:`.OptionNameMode` for more details.  Defaults to using underscores to match the
  attribute name.  May be overridden on a per-Parameter basis with :ref:`parameters:Options:name_mode`.
:reject_ambiguous_pos_combos: [EXPERIMENTAL] Whether ambiguous combinations of positional choices should result in an
  :class:`.AmbiguousParseTree` error.  Defaults to False.  Some combinations of positional parameter choices may pass
  this check, but still be problematic during parsing.  Since this is still experimental, there may be false positives.
  If a false positive is detected, this should be set back to ``False`` to disable the check (and please report it in
  the `issue tracker <https://github.com/dskrypa/cli_command_parser/issues>`__ so it can be fixed!).
:ambiguous_short_combos: How potentially ambiguous combinations of short forms of Option/Flag/etc. Parameters should
  be handled.  See :class:`.AmbiguousComboMode` for more details.  Defaults to allowing potentially ambiguous combos
  to exist as long as they are provided in their entirety.  May be configured to behave more like argparse (ignore
  any potential problems and perform a best effort parse), or to be strict and reject potentially ambiguous short forms
  from even being defined.


Usage & Help Text Options
-------------------------

Options that affect what is shown in the usage and help text output.  Some of these options also affect RST
documentation generation as well.


:add_help: Whether the ``--help`` / ``-h`` action_flag should be added (default: True)
:use_type_metavar: Whether the metavar for Parameters that accept values should default to the name of the
  specified type (default: False / the name of the parameter)
:show_defaults: Whether default values for Parameters should be automatically included in help text or not,
  and related settings.  Acceptable values are defined as
  `enum flags <https://docs.python.org/3/library/enum.html#flag>`__ that can be combined.  May be overridden on a
  per-Parameter level by using the :ref:`parameters:parameters:show_default` param. See :class:`.ShowDefaults` for
  more info.
:show_env_vars: Whether Parameters that support reading their values from environment variables should include the
  variables' names in their help text.  May be overridden on a per-Parameter level by using the
  :ref:`parameters:options:show_env_var` param.
:cmd_alias_mode: Controls how subcommand aliases (alternate :ref:`choices<subcommand_cls_params>` specified for a
  given Command class that is registered as a subcommand / subclass of another Command) should be displayed in help
  text and documentation.  Supports :class:`.SubcommandAliasHelpMode` values (or string equivalents).  Alternatively,
  a :meth:`format string<.ChoiceGroup.prepare_aliases>` for aliases may be provided here.
:sort_choices: Whether Parameter `choices` values and Action / Subcommand choices should be sorted (default: False)
:choice_delim: Delimiter to use between choices in usage / help text.  Defaults to ``|``.
:show_group_tree: Whether there should be a visual indicator in help text for the parameters that are members
  of a given group.  See :ref:`documentation:Group Formatting` for more info.  (default: False)
:group_tree_spacers: The spacer characters to use at the beginning of each line when ``show_group_tree`` is True.
  Must be a 3-tuple (or other sequence with 3 items) of spacer strings to be used for
  (mutually exclusive, mutually dependent, other) group members, respectively.  See
  :attr:`.CommandConfig.group_tree_spacers` for more information about the default values.
:show_group_type: Whether mutually exclusive / dependent groups should include that fact in their
  descriptions (default: True)
:command_formatter: A callable that accepts 2 arguments, a :class:`.Command` class (not object) and a
  :class:`.CommandParameters` object, and returns a :class:`.CommandHelpFormatter` (or a class that implements the
  same methods).
:param_formatter: A callable that accepts a :class:`.Parameter` or :class:`.ParamGroup` and returns a
  :class:`.ParamHelpFormatter` (or a class that implements the same methods).
:extended_epilog: Whether the program version, author email, and documentation URL should be included in the
  help text :ref:`epilog <documentation:Help Text Breakdown>`, if they were successfully detected (default: True).
:usage_column_width: Width (in characters) for the :ref:`usage column <documentation:Help Text Breakdown>` in help text.
  Defaults to 30.
:strict_usage_column_width: Whether the ``usage_column_width`` should be enforced for parameters with usage text parts
  that exceed it.  By default, that setting only defines where the parameter descriptions begin.
  See :ref:`documentation:Parameter List Formatting` for more details.  Defaults to False.
:wrap_usage_str: Wrap the basic :ref:`usage line <documentation:Help Text Breakdown>` after the specified number of
  characters, or automatically based on terminal size if ``True`` is specified instead (default: False).


Documentation Generation Options
--------------------------------

Options that only affect RST documentation generation.

:show_docstring: Whether the top level script's docstring should be included in generated documentation
  (default: True)
:show_inherited_descriptions: Whether inherited descriptions should be included in subcommand sections of generated
  documentation (default: False)
:sub_cmd_doc_depth: Maximum subcommand depth to include in generated documentation (default: include all)
