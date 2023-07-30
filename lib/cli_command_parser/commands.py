"""
The core Command classes that are intended as the entry point for a given program.

:author: Doug Skrypa
"""

from __future__ import annotations

import logging
from abc import ABC
from contextlib import ExitStack
from typing import TYPE_CHECKING, Type, Sequence, Optional, overload

from .core import CommandMeta, get_top_level_commands, get_params
from .context import Context, ActionPhase, get_or_create_context
from .exceptions import ParamConflict
from .parser import parse_args_and_get_next_cmd

if TYPE_CHECKING:
    from .typing import Bool, CommandObj

__all__ = ['Command', 'main']
log = logging.getLogger(__name__)

Argv = Sequence[str]


class Command(ABC, metaclass=CommandMeta):
    """The main class that other Commands should extend."""

    #: The parsing Context used for this Command. Provided here for convenience - this reference to it is not used by
    #: any CLI Command Parser internals, so it is safe for subclasses to redefine / overwrite it.
    ctx: Context

    def __new__(cls):
        # By storing the Context here instead of __init__, every single subclass won't need to
        # call super().__init__(...) from their own __init__ for this step
        self = super().__new__(cls)
        self.__ctx = ctx = get_or_create_context(cls, command=self)
        if not hasattr(self, 'ctx'):
            self.ctx: Context = ctx  # noqa  # PyCharm complains this is invalid, but doesn't understand it without it
        return self

    def __repr__(self) -> str:
        cls = self.__class__
        return f'<{cls.__name__} in prog={cls.__class__.meta(cls).prog!r}>'

    # region Parse & Run

    @classmethod
    @overload
    def parse_and_run(cls: Type[CommandObj], argv: Argv = None, **kwargs) -> Optional[CommandObj]:
        ...  # These overloads indicate that an instance of the same type or another may be returned

    @classmethod
    @overload
    def parse_and_run(cls, argv: Argv = None, **kwargs) -> Optional[CommandObj]:
        ...

    @classmethod
    def parse_and_run(cls, argv=None, **kwargs):
        """
        Primary entry point for parsing arguments, resolving subcommands, and running a command.

        Calls :meth:`.parse` to parse arguments and resolve subcommands, then calls :meth:`.__call__` on the resulting
        Command instance.  Handles exceptions during parsing using the configured :class:`.ErrorHandler`.

        To be able to store a reference to the (possibly resolved subcommand) command instance, you should instead use
        the above-mentioned methods separately.

        :param argv: The arguments to parse (defaults to :data:`python:sys.argv`)
        :param kwargs: Keyword arguments to pass to :meth:`.__call__`
        :return: The Command instance with parsed arguments for which :meth:`.__call__` was already called.
        """
        ctx = get_or_create_context(cls, argv)
        with ctx.get_error_handler():
            self = cls.parse(argv)

        try:
            self
        except UnboundLocalError:  # There was an error handled during parsing, so self was not defined
            return None
        else:
            self(**kwargs)
            return self

    # endregion

    # region Parse

    @classmethod
    @overload
    def parse(cls: Type[CommandObj], argv: Argv = None) -> CommandObj:
        ...

    @classmethod
    @overload
    def parse(cls, argv: Argv = None) -> CommandObj:
        ...

    @classmethod
    def parse(cls, argv=None):
        """
        Parses the specified arguments (or :data:`sys.argv`), and resolves the final subcommand class based on the
        parsed arguments, if necessary.  Initializes the Command, but does not call any of its other methods.

        :param argv: The arguments to parse (defaults to :data:`sys.argv`)
        :return: A Command instance with parsed arguments that is ready for :meth:`.__call__` or :meth:`.main`
        """
        ctx = get_or_create_context(cls, argv)
        cmd_cls = cls
        with ExitStack() as stack:
            stack.enter_context(ctx)
            while sub_cmd := parse_args_and_get_next_cmd(ctx):
                cmd_cls = sub_cmd
                ctx = stack.enter_context(ctx._sub_context(cmd_cls))

            return cmd_cls()

    # endregion

    def __call__(self, *args, **kwargs) -> int:
        """
        Primary entry point for running a command.  Subclasses generally should not override this method.

        Handles exceptions using the configured :class:`.ErrorHandler`.  Alternate error handlers can be specified
        via the :paramref:`~.core.CommandMeta.error_handler` parameter during Command class initialization.
        To skip error handling, define the class with ``error_handler=None``.

        Calls the following methods in order:

            #. :meth:`._pre_init_actions_`
            #. :meth:`._init_command_`
            #. :meth:`._before_main_`
            #. :meth:`.main`
            #. :meth:`._after_main_`

        :param args: Positional arguments to pass to the methods listed above
        :param kwargs: Keyword arguments to pass to the methods listed above
        :return: The total number of actions that were taken
        """
        with self.__ctx as ctx, ctx.get_error_handler():
            self._pre_init_actions_(*args, **kwargs)
            self._init_command_(*args, **kwargs)
            self._before_main_(*args, **kwargs)
            try:
                self.main(*args, **kwargs)
            except BaseException:
                if ctx.config.always_run_after_main:
                    log.debug('Caught exception - running _after_main_ before propagating', exc_info=True)
                    self._after_main_(*args, **kwargs)
                raise
            else:
                self._after_main_(*args, **kwargs)

        return ctx.actions_taken

    def _pre_init_actions_(self, *args, **kwargs):
        """
        The first method called by :meth:`.__call__` (before :meth:`.main` and others).

        Validates the number of ActionFlags that were specified, and calls all of the specified
        :func:`~.options.before_main` / :obj:`~.options.action_flag` actions such as ``--help`` that were
        defined with ``before_main=True`` and ``always_available=True`` in their configured order.

        :param args: Positional arguments to pass to the :obj:`~.options.action_flag` methods
        :param kwargs: Keyword arguments to pass to the :obj:`~.options.action_flag` methods
        """
        # TODO: --help should take precedence over input validation - right now, if a Path input expecting a
        #  non-existent file receives a file that exists, that error is reported instead of showing help text
        ctx = self.__ctx
        n_flags = ctx.action_flag_count
        if n_flags and not ctx.config.multiple_action_flags and n_flags > 1:
            raise ParamConflict(ctx.all_action_flags, 'combining multiple action flags is disabled')

        if before := ctx.categorized_action_flags[ActionPhase.BEFORE_MAIN]:
            action = get_params(self).action
            if action is not None and not ctx.config.action_after_action_flags:
                raise ParamConflict([action, *before], 'combining an action with action flags is disabled')

        for param in ctx.iter_action_flags(ActionPhase.PRE_INIT):
            param.func(self, *args, **kwargs)

    def _init_command_(self, *args, **kwargs):
        """
        Called by :meth:`.__call__` after :meth:`._pre_init_actions_` and before :meth:`._before_main_`.

        Safe to override without calling ``super()._init_command_()`` - the base implementation is a placeholder
        intended to allow subclasses to perform initialization tasks.  This method is called after actions like
        ``--help`` have been processed, so more resource-intensive initialization operations or those that may have
        side effects that should not occur when the application does nothing should be placed here instead of in
        ``__init__``.

        Actions like initializing logging are recommended to be placed in this method.

        :param args: Positional arguments that were passed to :meth:`.__call__`
        :param kwargs: Keyword arguments that were passed to :meth:`.__call__`
        """
        pass

    def _before_main_(self, *args, **kwargs):
        """
        Called by :meth:`.__call__` after :meth:`._init_command_` and before :meth:`.main` is called.

        Calls all of the specified :func:`~.options.before_main` / :obj:`~.options.action_flag` actions that
        were defined with ``before_main=True`` and ``always_available=False`` in their configured order.

        :param args: Positional arguments to pass to the :obj:`~.options.action_flag` methods
        :param kwargs: Keyword arguments to pass to the :obj:`~.options.action_flag` methods
        """
        for param in self.__ctx.iter_action_flags(ActionPhase.BEFORE_MAIN):
            param.func(self, *args, **kwargs)

    def main(self, *args, **kwargs) -> Optional[int]:
        """
        Primary method that is called when running a Command.

        If any arguments were specified that are associated with triggering a method that was decorated / registered as
        a positional :class:`~.choice_map.Action`'s target method, then that method is called here.

        Commands that do not have any positional :class:`Actions<.choice_map.Action>` can override this method, and do
        **not** need to call ``super().main(*args, **kwargs)``.

        Initialization code that is common for all actions, or that should be run before :meth:`._before_main_` should
        be placed in ``__init__``.

        :param args: Positional arguments to pass to the action method
        :param kwargs: Keyword arguments to pass to the action method
        :return: The total number of actions that were taken so far
        """
        with self.__ctx as ctx:
            action = get_params(self).action
            if action is not None and (ctx.actions_taken == 0 or ctx.config.action_after_action_flags):
                ctx.actions_taken += 1
                action.target()(self, *args, **kwargs)

        return ctx.actions_taken

    def _after_main_(self, *args, **kwargs):
        """
        Called by :meth:`.__call__` after :meth:`.main` is called.  Calls all of the specified
        :func:`~.options.after_main` / :obj:`~.options.action_flag` actions that were defined with
        ``before_main=False`` in their configured order.

        :param args: Positional arguments to pass to the :obj:`~.options.action_flag` methods
        :param kwargs: Keyword arguments to pass to the :obj:`~.options.action_flag` methods
        """
        for param in self.__ctx.iter_action_flags(ActionPhase.AFTER_MAIN):
            param.func(self, *args, **kwargs)


def main(argv: Argv = None, return_command: Bool = False, **kwargs) -> Optional[CommandObj]:
    """
    Convenience function that can be used as the main entry point for a program.

    As long as only one :class:`Command` subclass is present, this function will detect it and call its
    :meth:`~Command.parse_and_run` method.  Subcommands do not count as direct subclasses of Command, so this function
    will continue to work even if subcommands are present (as long as they extend their parent command).

    If multiple direct subclasses of Command are detected, or if no direct subclasses can be found, then a RuntimeError
    will be raised.  In such cases, you must explicitly call :meth:`~Command.parse_and_run` on the command that is
    intended to be the primary entry point.

    :param argv: The sequence of arguments to parse.  Defaults to :data:`python:sys.argv` if not specified.
    :param return_command: Whether the parsed Command that ran should be returned.
    :param kwargs: Keyword arguments to pass through to :meth:`~Command.parse_and_run`
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

    command = commands[0].parse_and_run(argv, **kwargs)
    return command if return_command else None
