"""
The core Command classes that are intended as the entry point for a given program.

:author: Doug Skrypa
"""

import logging
from contextlib import ExitStack
from typing import Type, TypeVar, Sequence, Optional, Union
from warnings import warn

from .actions import help_action
from .command_parameters import CommandParameters
from .config import CommandConfig
from .context import Context
from .error_handling import ErrorHandler, NullErrorHandler, extended_error_handler
from .exceptions import CommandDefinitionError, UsageError, NoSuchOption, ParamsMissing, ParamConflict
from .parser import CommandParser
from .utils import _NotSet, Bool, ProgramMetadata, cached_class_property

__all__ = ['Command', 'CommandType']
log = logging.getLogger(__name__)

CommandType = TypeVar('CommandType', bound=Type['Command'])
CommandObj = TypeVar('CommandObj', bound='Command')


class Command:
    """
    The main class that other Commands should extend.
    """

    # region Initialization
    # fmt: off
    params: CommandParameters           # Must declare here for PyCharm's type checker to work properly
    _config_: CommandConfig = None      # Configured Command options
    __meta: ProgramMetadata = None      # Metadata used in help text
    __abstract: Bool = True             # False if viable for containing sub commands
    # fmt: on

    def __init_subclass__(
        cls: CommandType,
        choice: str = None,
        prog: str = None,
        usage: str = None,
        description: str = None,
        epilog: str = None,
        help: str = None,  # noqa
        abstract: Bool = False,
        config: CommandConfig = None,
        **kwargs,
    ):
        """
        :param choice: SubCommand value that maps to this command
        :param prog: The name of the program (default: ``sys.argv[0]``)
        :param usage: Usage message (default: auto-generated)
        :param description: Description of what the program does
        :param epilog: Text to follow parameter descriptions
        :param help: Help text to be displayed as a SubCommand option.  Ignored for top-level commands.
        :param error_handler: The :class:`ErrorHandler<command_parser.error_handling.ErrorHandler>` to be used by
          :meth:`.run` to wrap :meth:`.main`
        :param bool add_help: Whether the --help / -h action_flag should be added
        :param bool action_after_action_flags: Whether action_flag methods are allowed to be combined with a positional
          Action method in a given CLI invocation
        :param bool multiple_action_flags: Whether multiple action_flag methods are allowed to run if they are all
          specified
        :param ignore_unknown: Whether unknown arguments should be allowed (default: raise an exception when unknown
          arguments are encountered)
        :param allow_missing: Whether missing required arguments should be allowed (default: raise an exception when
          required arguments are missing)
        :param abstract: Set to True to prevent a command from being considered to be a parent that may contain sub
          commands
        """
        if cls.__meta is None or prog or usage or description or epilog:  # Inherit from parent when possible
            cls.__meta = ProgramMetadata(prog=prog, usage=usage, description=description, epilog=epilog)

        if config is not None:
            if kwargs:
                raise CommandDefinitionError(f'Cannot combine {config=} with keyword config arguments={kwargs}')
            cls._config_ = config
        elif kwargs or (cls._config_ is None and not abstract):
            if cls._config_ is not None:  # Inherit existing configs and override specified values
                kwargs = cls._config_.as_dict() | kwargs
            cls._config_ = CommandConfig(**kwargs)

        if (config := cls._config_) is not None:
            if config.add_help and not hasattr(cls, '_Command__help'):
                cls.__help = help_action

        cls.__abstract = abstract

        if parent := next((c for c in cls.mro()[1:] if issubclass(c, Command) and not c.__abstract), None):
            if (sub_cmd := parent.params.sub_command) is not None:
                sub_cmd.register_command(choice, cls, help)
            elif choice:
                warn(f'{choice=} was not registered for {cls} because its {parent=} has no SubCommand parameter')
        elif choice:
            warn(f'{choice=} was not registered for {cls} because it has no parent Command')

    @cached_class_property
    def params(cls: CommandType) -> CommandParameters:  # noqa
        # The parent here is different than in __init_subclass__ to allow ActionFlag inheritance
        parent = next((c for c in cls.mro()[1:] if issubclass(c, Command) and c is not Command), None)
        return CommandParameters(cls, parent)

    @classmethod
    def __get_error_handler(cls) -> Union[ErrorHandler, NullErrorHandler]:
        if (config := cls._config_) is not None:
            error_handler = config.error_handler
        else:
            error_handler = _NotSet

        if error_handler is _NotSet:
            return extended_error_handler
        elif error_handler is None:
            return NullErrorHandler()
        else:
            return error_handler

    def __new__(cls, ctx: Context):
        # By storing the Context here instead of __init__, every single sub class won't need to
        # call super().__init__(...) from their own __init__ for this step
        self = super().__new__(cls)
        self.__ctx = ctx
        self.__dict__.setdefault('ctx', ctx)
        return self

    # endregion

    @classmethod
    def parse_and_run(cls, argv: Sequence[str] = None, *args, **kwargs) -> Optional[CommandObj]:
        """
        Primary entry point for parsing arguments, resolving sub-commands, and running a command.  Calls :meth:`.parse`
        to parse arguments and resolve sub-commands, then calls :meth:`.run` on the resulting Command instance.  Handles
        exceptions during parsing using the configured :class:`ErrorHandler
        <command_parser.error_handling.ErrorHandler>`.

        To be able to store a reference to the (possibly resolved sub-command) command instance, you should instead use
        the above mentioned methods separately.

        :param argv: The arguments to parse (defaults to :data:`sys.argv`)
        :param args: Positional arguments to pass to :meth:`.run`
        :param kwargs: Keyword arguments to pass to :meth:`.run`
        :return: The Command instance with parsed arguments for which :meth:`.run` was already called.
        """
        with cls.__get_error_handler():
            self = cls.parse(argv)

        try:
            run = self.run
        except UnboundLocalError:  # There was an error handled during parsing, so self was not defined
            return None
        else:
            run(*args, **kwargs)
            return self

    @classmethod
    def parse(cls, argv: Sequence[str] = None) -> CommandObj:
        """
        Parses the specified arguments (or :data:`sys.argv`), and resolves the final sub-command class based on the
        parsed arguments, if necessary.

        :param argv: The arguments to parse (defaults to :data:`sys.argv`)
        :return: A Command instance with parsed arguments that is ready for :meth:`.run` or :meth:`.main`
        """
        cmd_cls = cls
        with ExitStack() as stack:
            ctx = Context(argv, cmd_cls)
            stack.enter_context(ctx)
            while sub_cmd := CommandParser.parse_args(ctx):
                cmd_cls = sub_cmd
                ctx = Context(ctx.remaining, cmd_cls, parent=ctx)
                stack.enter_context(ctx)

        return cmd_cls(ctx)

    def run(self, *args, **kwargs) -> int:
        """
        Primary entry point for running a command.  Subclasses generally should not override this method.

        Handles exceptions using the configured :class:`~.error_handling.ErrorHandler`.  Alternate error handlers can
        be specified via the :paramref:`~Command.__init_subclass__.error_handler` parameter during Command class
        initialization.  To skip error handling, define the class with ``error_handler=None``.

        Calls 3 methods in order: :meth:`._before_main_`, :meth:`.main`, and :meth:`._after_main_`.

        :param args: Positional arguments to pass to :meth:`._before_main_`, :meth:`.main`, and :meth:`._after_main_`
        :param kwargs: Keyword arguments to pass to :meth:`._before_main_`, :meth:`.main`, and :meth:`._after_main_`
        :return: The total number of actions that were taken
        """
        with self.__ctx, self.__get_error_handler():
            self._before_main_(*args, **kwargs)
            self.main(*args, **kwargs)
            self._after_main_(*args, **kwargs)

        return self.__ctx.actions_taken

    def _before_main_(self, *args, **kwargs):
        """
        Called by :meth:`.run` before :meth:`.main` is called.  Validates the number of ActionFlags that were specified,
        and calls all of the specified :obj:`~.parameters.before_main` / :obj:`~.parameters.action_flag` actions
        that were defined with ``before_main=True`` in their configured order.

        :param args: Positional arguments to pass to the :obj:`~.parameters.action_flag` methods
        :param kwargs: Keyword arguments to pass to the :obj:`~.parameters.action_flag` methods
        """
        ctx = self.__ctx
        n_flags, before, after = ctx.parsed_action_flags
        if n_flags and not self._config_.multiple_action_flags and n_flags > 1:
            raise ParamConflict(before + after, 'combining multiple action flags is disabled')

        for param in ctx.before_main_actions:
            param.func(self, *args, **kwargs)

    def main(self, *args, **kwargs) -> Optional[int]:
        """
        Primary method that is called when running a Command.

        If any arguments were specified that are associated with triggering a method that was decorated / registered as
        a positional :class:`~.parameters.Action`'s target method, then that method is called here.

        Commands that do not have any positional :class:`Actions<.parameters.Action>` can override this method, and do
        **not** need to call ``super().main(*args, **kwargs)``.

        Initialization code that is common for all actions, or that should be run before :meth:`._before_main_` should be
        placed in ``__init__``.

        :param args: Positional arguments to pass to the action method
        :param kwargs: Keyword arguments to pass to the action method
        :return: The total number of actions that were taken so far
        """
        with self.__ctx as ctx:
            action = self.params.action
            if action is not None and (ctx.actions_taken == 0 or ctx.action_after_action_flags):
                # TODO: Error on action when ctx.action_after_action_flags is False?
                ctx.actions_taken += 1
                action.result(ctx)(self, *args, **kwargs)

        return ctx.actions_taken

    def _after_main_(self, *args, **kwargs):
        """
        Called by :meth:`.run` after :meth:`.main` is called.  Calls all of the specified
        :obj:`~.parameters.after_main` / :obj:`~.parameters.action_flag` actions that were defined with
        ``before_main=False`` in their configured order.

        :param args: Positional arguments to pass to the :obj:`~.parameters.action_flag` methods
        :param kwargs: Keyword arguments to pass to the :obj:`~.parameters.action_flag` methods
        """
        for param in self.__ctx.after_main_actions:
            param.func(self, *args, **kwargs)
