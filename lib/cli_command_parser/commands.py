"""
The core Command classes that are intended as the entry point for a given program.

:author: Doug Skrypa
"""

import logging
from abc import ABC
from contextlib import ExitStack
from typing import TypeVar, Sequence, Optional

from .core import CommandMeta, CommandType, get_top_level_commands
from .context import Context, get_current_context
from .exceptions import ParamConflict, NoActiveContext

__all__ = ['Command', 'CommandType', 'main']
log = logging.getLogger(__name__)

CommandObj = TypeVar('CommandObj', bound='Command')


class Command(ABC, metaclass=CommandMeta):
    """
    The main class that other Commands should extend.
    """

    ctx: Context  # The parsing Context used for this Command

    def __new__(cls):
        ctx = _get_or_create_context(cls)
        # By storing the Context here instead of __init__, every single sub class won't need to
        # call super().__init__(...) from their own __init__ for this step
        self = super().__new__(cls)
        self.__ctx = ctx
        self.__dict__.setdefault('ctx', ctx)
        return self

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
        ctx = _get_or_create_context(cls, argv)
        with ctx.get_error_handler():
            self = cls.parse(argv)

        try:
            self
        except UnboundLocalError:  # There was an error handled during parsing, so self was not defined
            return None
        else:
            self(*args, **kwargs)
            return self

    @classmethod
    def parse(cls, argv: Sequence[str] = None) -> CommandObj:
        """
        Parses the specified arguments (or :data:`sys.argv`), and resolves the final sub-command class based on the
        parsed arguments, if necessary.

        :param argv: The arguments to parse (defaults to :data:`sys.argv`)
        :return: A Command instance with parsed arguments that is ready for :meth:`.run` or :meth:`.main`
        """
        from .parser import CommandParser

        ctx = _get_or_create_context(cls, argv)
        cmd_cls = cls
        with ExitStack() as stack:
            stack.enter_context(ctx)
            sub_cmd = CommandParser.parse_args()
            while sub_cmd:
                cmd_cls = sub_cmd
                ctx = stack.enter_context(ctx._sub_context(cmd_cls))
                sub_cmd = CommandParser.parse_args()

            return cmd_cls()

    def __call__(self, *args, **kwargs) -> int:
        """
        Primary entry point for running a command.  Subclasses generally should not override this method.

        Handles exceptions using the configured :class:`~.error_handling.ErrorHandler`.  Alternate error handlers can
        be specified via the :paramref:`~.core.CommandMeta.__new__.error_handler` parameter during Command class
        initialization.  To skip error handling, define the class with ``error_handler=None``.

        Calls 3 methods in order: :meth:`._before_main_`, :meth:`.main`, and :meth:`._after_main_`.

        :param args: Positional arguments to pass to :meth:`._before_main_`, :meth:`.main`, and :meth:`._after_main_`
        :param kwargs: Keyword arguments to pass to :meth:`._before_main_`, :meth:`.main`, and :meth:`._after_main_`
        :return: The total number of actions that were taken
        """
        with self.__ctx as ctx, ctx.get_error_handler():
            self._before_main_(*args, **kwargs)
            self.main(*args, **kwargs)
            self._after_main_(*args, **kwargs)

        return ctx.actions_taken

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
        if n_flags and not ctx.multiple_action_flags and n_flags > 1:
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

        Initialization code that is common for all actions, or that should be run before :meth:`._before_main_` should
        be placed in ``__init__``.

        :param args: Positional arguments to pass to the action method
        :param kwargs: Keyword arguments to pass to the action method
        :return: The total number of actions that were taken so far
        """
        with self.__ctx as ctx:
            cls = self.__class__
            action = cls.__class__.params(cls).action  # noqa
            if action is not None and (ctx.actions_taken == 0 or ctx.action_after_action_flags):
                # TODO: Error on action when ctx.action_after_action_flags is False?
                ctx.actions_taken += 1
                action.result()(self, *args, **kwargs)

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


def _get_or_create_context(cls: CommandType, argv: Sequence[str] = None) -> Context:
    try:
        ctx = get_current_context()
    except NoActiveContext:
        return Context(argv, cls)
    else:
        if argv is None and ctx.command is cls:
            return ctx
        else:
            return ctx._sub_context(cls, argv=argv)


def main(argv: Sequence[str] = None, *args, **kwargs):
    """
    Convenience function that can be used as the main entry point for a program.

    As long as only one :class:`Command` subclass is present, this function will detect it and call its
    :meth:`~Command.parse_and_run` method.  Sub-commands do not count as direct subclasses of Command, so this function
    will continue to work even if sub-commands are present (as long as they extend their parent command).

    If multiple direct subclasses of Command are detected, or if no direct subclasses can be found, then a RuntimeError
    will be raised.  In such cases, you must explicitly call :meth:`~Command.parse_and_run` on the command that is
    intended to be the primary entry point.

    All arguments are passed through to :meth:`~Command.parse_and_run`

    :raises: :class:`RuntimeError` if multiple subclasses are detected, or if no subclasses could be found.
    """
    commands = get_top_level_commands()
    if len(commands) != 1:
        error_base = 'Unable to automatically pick a Command subclass to use as the main program entry point -'
        if commands:
            cmds_str = ', '.join(c.__qualname__ for c in commands)
            raise RuntimeError(
                f'{error_base} found {len(commands)} commands: {cmds_str}\n'
                'You need to call <MyCommand>.parse_and_run() explicitly for the intended command.'
            )
        else:
            raise RuntimeError(
                f'{error_base} no commands were found.\n'
                'Verify that the intended command has been imported, or call <MyCommand>.parse_and_run() explicitly.'
            )

    return commands[0].parse_and_run(argv, *args, **kwargs)  # noqa
