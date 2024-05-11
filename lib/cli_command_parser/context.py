"""
The parsing Context used internally for tracking parsed arguments and configuration overrides.

:author: Doug Skrypa
"""
# pylint: disable=R0801

from __future__ import annotations

import sys
from collections import defaultdict
from contextlib import AbstractContextManager
from contextvars import ContextVar
from enum import Enum
from functools import cached_property
from inspect import Parameter as _Parameter, Signature
from typing import TYPE_CHECKING, Any, Callable, Collection, Iterator, Optional, Sequence, Union, cast

from .config import DEFAULT_CONFIG, CommandConfig
from .error_handling import ErrorHandler, NullErrorHandler, extended_error_handler
from .exceptions import NoActiveContext
from .utils import Terminal, _NotSet

if TYPE_CHECKING:
    from .command_parameters import CommandParameters
    from .commands import Command
    from .parameters import ActionFlag, Option, Parameter
    from .typing import AnyConfig, Bool, CommandObj, CommandType, OptStr, ParamOrGroup, PathLike, StrSeq  # noqa

__all__ = ['Context', 'ctx', 'get_current_context', 'get_or_create_context', 'get_context', 'get_parsed', 'get_raw_arg']

_context_stack = ContextVar('cli_command_parser.context.stack')
_TERMINAL = Terminal()

Argv = Optional['StrSeq']


class Context(AbstractContextManager):  # Extending AbstractContextManager to make PyCharm's type checker happy
    """
    The parsing context.

    Holds user input while parsing, and holds the parsed values.  Handles config overrides / hierarchy for settings that
    affect parser behavior.
    """

    config: CommandConfig
    prog: OptStr = None
    allow_argv_prog: Bool = True
    _command_obj: CommandObj = None
    _terminal_width: Optional[int]
    _provided: dict[ParamOrGroup, int]

    def __init__(
        self,
        argv: Argv = None,
        command_cls: Optional[CommandType] = None,
        *,
        parent: Optional[Context] = None,
        config: AnyConfig = None,
        terminal_width: int = None,
        allow_argv_prog: Bool = None,
        command: Optional[CommandObj] = None,
        **kwargs,
    ):
        self.command_cls = command_cls
        self.command = command
        self.parent = parent
        self.actions_taken = 0
        self.config = _normalize_config(config, kwargs, parent, command_cls)
        if parent:
            self._set_argv(parent.prog, argv)
            self._parsed = parent._parsed.copy()
            self._provided = parent._provided.copy()
            self._terminal_width = parent._terminal_width if terminal_width is None else terminal_width
            self.allow_argv_prog = parent.allow_argv_prog if allow_argv_prog is None else allow_argv_prog
        else:
            self._set_argv(None, argv)
            self._parsed = {}
            self._provided = defaultdict(int)
            self._terminal_width = terminal_width
            if allow_argv_prog is not None:
                self.allow_argv_prog = allow_argv_prog

    # region Internal Methods

    @classmethod
    def for_prog(cls, prog: PathLike, *args, **kwargs) -> Context:
        self = cls(*args, **kwargs)
        self.prog = getattr(prog, 'name', prog)
        return self

    def _set_argv(self, prog: OptStr, argv: Argv):
        if prog:
            self.prog = prog
            self.argv = sys.argv[1:] if argv is None else argv
        elif argv is None:
            self.prog, *self.argv = sys.argv
        else:
            self.argv = argv
        self.remaining = list(self.argv)

    def _sub_context(
        self, command_cls: CommandType, argv: Argv = None, command: CommandObj = None, **kwargs
    ) -> Context:
        return self.__class__(
            self.remaining if argv is None else argv,
            command_cls,
            parent=self,
            command=self.command if command is None else command,
            **kwargs,
        )

    def __repr__(self) -> str:
        command = getattr(self.command_cls, '__name__', None)
        prog, argv, allow_argv_prog = self.prog, self.argv, self.allow_argv_prog
        return f'<{self.__class__.__name__}[{command=!s}, {prog=}, {allow_argv_prog=}, {argv=}]>'

    def __enter__(self) -> Context:
        try:
            _context_stack.get().append(self)
        except LookupError:
            _context_stack.set([self])
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        _context_stack.get().pop()

    def __contains__(self, param: Union[ParamOrGroup, str, Any]) -> bool:
        try:
            self._parsed[param]
        except KeyError:
            if isinstance(param, str):
                try:
                    next((v for p, v in self._parsed.items() if p.name == param))
                except StopIteration:
                    return False
                else:
                    return True
            return False
        else:
            return True

    # endregion

    @property
    def terminal_width(self) -> int:
        """Returns the current terminal width as the number of characters that fit on a single line."""
        if self._terminal_width is not None:
            return self._terminal_width
        return _TERMINAL.width

    def get_parsed(
        self,
        command: Command = None,
        *,
        exclude: Collection[Parameter] = (),
        recursive: Bool = True,
        default: Any = None,
        include_defaults: Bool = True,
    ) -> dict[str, Any]:
        """
        Returns all of the parsed arguments as a dictionary.

        The :ref:`get_parsed() <advanced:Parsed Args as a Dictionary>` helper function provides an easier way to access
        this functionality.

        :param command: An initialized Command object for which arguments were already parsed.
        :param exclude: Parameter objects that should be excluded from the returned results
        :param recursive: Whether parsed arguments should be recursively gathered from parent Commands
        :param default: The default value to use for parameters that raise :class:`.MissingArgument` when attempting to
          obtain their result values.
        :param include_defaults: Whether default values should be included in the returned results.  If False, only
          user-provided values will be included.
        :return: A dictionary containing all of the arguments that were parsed.  The keys in the returned dict match
          the names assigned to the Parameters in the Command associated with this Context.
        """
        if command is None:
            command = self.command
        with self:
            if recursive and self.parent:
                parsed = self.parent.get_parsed(
                    command, exclude=exclude, recursive=recursive, default=default, include_defaults=include_defaults
                )
            else:
                parsed = {}

            # TODO: Add way to get a nested dict with ParamGroup names as the keys of the nested sections?
            if self.params:
                for param in self.params.iter_params(exclude):
                    if include_defaults or param in self._parsed:
                        parsed[param.name] = param.result(command, default)

        return parsed

    @cached_property
    def params(self) -> Optional[CommandParameters]:
        """
        The :class:`.CommandParameters` object that contains the categorized Parameters from the Command associated
        with this Context.
        """
        if self.command_cls is not None:
            return self.command_cls.__class__.params(self.command_cls)
        return None

    def get_error_handler(self) -> Union[ErrorHandler, NullErrorHandler]:
        """Returns the :class:`.ErrorHandler` configured to be used."""
        if (error_handler := self.config.error_handler) is _NotSet:
            return extended_error_handler
        elif error_handler is None:
            return NullErrorHandler()
        else:
            return error_handler

    # region Parsing Methods - Generally not intended to be called by users

    def has_parsed_value(self, param: Parameter) -> bool:
        return param in self._parsed

    def get_parsed_value(self, param: Parameter, default=_NotSet):
        """Not intended to be called by users.  Used by Parameters to access their parsed values."""
        return self._parsed.get(param, default)

    def set_parsed_value(self, param: Parameter, value: Any):
        """Not intended to be called by users.  Used by Parameters during parsing to store parsed values."""
        self._parsed[param] = value

    def pop_parsed_value(self, param: Parameter):
        """Not intended to be called by users.  Used by Parameters during parsing if backtracking is necessary."""
        self._provided[param] = 0
        return self._parsed.pop(param)

    def roll_back_parsed_values(self, param: Parameter, count: int):
        """Not intended to be called by users.  Used during parsing as part of backtracking."""
        values = self._parsed[param]
        self._parsed[param] = values[:-count]
        self._provided[param] -= count
        return values[-count:]

    def record_action(self, param: ParamOrGroup, val_count: int = 1):
        """
        Not intended to be called by users.  Used by Parameters during parsing to indicate that they were provided.
        """
        self._provided[param] += val_count

    def num_provided(self, param: ParamOrGroup) -> int:
        """Not intended to be called by users.  Used by Parameters during parsing to handle nargs."""
        return self._provided[param]

    def get_missing(self) -> list[Parameter]:
        """Not intended to be called by users.  Used during parsing to determine if any Parameters are missing."""
        return [p for p in self.params.required_check_params() if not self._provided[p]]

    def missing_options_with_env_var(self) -> Iterator[Option]:
        """Yields Option parameters that have an environment variable configured, and did not have any CLI values."""
        yield from (p for p in self.params.options if p.env_var and not self._provided[p])

    # endregion

    # region Actions

    @cached_property
    def _parsed_action_flags(self) -> tuple[int, list[ActionFlag], list[ActionFlag]]:
        """
        Not intended to be accessed by users.  Returns a tuple containing the total number of action flags provided, the
        action flags to run before main, and the action flags to run after main.
        """
        try:
            before_main, after_main = self.params.split_action_flags  # Each part is already sorted
        except AttributeError:  # self.command_cls is None
            return 0, [], []

        parsed = self._parsed
        before_main = [p for p in before_main if p in parsed] if before_main else []
        after_main = [p for p in after_main if p in parsed] if after_main else []
        return len(before_main) + len(after_main), before_main, after_main

    @property
    def action_flag_count(self) -> int:
        """Not intended to be accessed by users.  Returns the count of parsed action flags."""
        return self._parsed_action_flags[0]

    @cached_property
    def all_action_flags(self) -> list[ActionFlag]:
        """Not intended to be accessed by users.  Returns all parsed action flags."""
        _, before_main, after_main = self._parsed_action_flags
        return before_main + after_main

    @cached_property
    def categorized_action_flags(self) -> dict[ActionPhase, Sequence[ActionFlag]]:
        """
        Not intended to be accessed by users.  Returns a dict of parsed action flags, categorized by the
        :class:`ActionPhase` during which they will run.
        """
        _, before_main, after_main = self._parsed_action_flags
        init_actions, before_actions = [], []
        for flag in before_main:
            if flag.always_available:
                init_actions.append(flag)
            else:
                before_actions.append(flag)

        return {
            ActionPhase.PRE_INIT: init_actions,
            ActionPhase.BEFORE_MAIN: before_actions,
            ActionPhase.AFTER_MAIN: after_main,
        }

    def iter_action_flags(self, phase: ActionPhase) -> Iterator[ActionFlag]:
        """
        Not intended to be called by users.  Iterator that yields action flags to be executed during the specified
        phase while incrementing the counter of actions taken.

        :param phase: The current :class:`ActionPhase`
        """
        for action_flag in self.categorized_action_flags[phase]:
            self.actions_taken += 1
            yield action_flag

    # endregion


def _normalize_config(
    config: AnyConfig, kwargs: dict[str, Any], parent: Context | None, command: CommandType | None
) -> CommandConfig:
    if config is not None:
        if kwargs:
            raise TypeError(f'Cannot combine {config=} with keyword config arguments={kwargs}')
        elif isinstance(config, CommandConfig):
            return config
        kwargs = config

    if parent:
        for key, val in parent.config._data.items():
            kwargs.setdefault(key, val)

    return CommandConfig(parent=command.__class__.config(command) if command is not None else None, **kwargs)


class ActionPhase(Enum):
    PRE_INIT = 0
    BEFORE_MAIN = 1
    AFTER_MAIN = 2

    # def __next__(self) -> ActionPhase:
    #     try:
    #         return self._value2member_map_[self._value_ + 1]  # noqa
    #     except KeyError:
    #         raise StopIteration


class ContextProxy:
    """
    Proxy for the currently active :class:`Context` object.  Allows usage similar to the ``request`` object in Flask.

    This class should not be instantiated by users - use the common :data:`ctx` instance.
    """

    __slots__ = ()

    # region Generic Proxy Methods

    def __getattr__(self, attr: str):
        return getattr(get_current_context(), attr)

    def __setattr__(self, attr: str, value):
        return setattr(get_current_context(), attr, value)

    def __eq__(self, other) -> bool:
        return get_current_context() == other

    def __contains__(self, item) -> bool:
        return item in get_current_context()

    def __enter__(self) -> Context:
        # The current context is already active, so there's no need to re-enter it - it can just be returned
        return get_current_context()

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    # endregion

    # region Proxied Parsing Methods

    def has_parsed_value(self, param: Parameter) -> bool:
        return get_current_context().has_parsed_value(param)

    def get_parsed_value(self, param: Parameter):
        return get_current_context().get_parsed_value(param)

    def set_parsed_value(self, param: Parameter, value: Any):
        get_current_context().set_parsed_value(param, value)

    def record_action(self, param: ParamOrGroup, val_count: int = 1):
        get_current_context().record_action(param, val_count)

    def num_provided(self, param: ParamOrGroup) -> int:
        return get_current_context().num_provided(param)

    # endregion

    # region Properties with Inactive Handlers

    @property
    def terminal_width(self) -> int:
        if context := get_current_context(True):
            return context.terminal_width
        else:
            return _TERMINAL.width

    @property
    def config(self) -> CommandConfig:
        if context := get_current_context(True):
            return context.config
        else:
            return DEFAULT_CONFIG

    # endregion


ctx: Context = cast(Context, ContextProxy())


# region Public / Semi-Public Functions


def get_current_context(silent: bool = False) -> Optional[Context]:
    """
    Get the currently active parsing context.

    :param silent: If True, allow this function to return ``None`` if there is no active :class:`Context`
    :return: The active :class:`Context` object
    :raises: :class:`~.exceptions.NoActiveContext` if there is no active Context and ``silent=False`` (default)
    """
    try:
        return _context_stack.get()[-1]
    except (LookupError, IndexError):
        if silent:
            return None
        raise NoActiveContext('There is no active context') from None


def get_or_create_context(
    command_cls: CommandType, argv: Argv = None, *, command: CommandObj = None, **kwargs
) -> Context:
    """
    Used internally by Commands to re-use an existing user-activated Context, or to create a new Context if there was
    no active Context.
    """
    if not (context := get_current_context(True)):
        return Context(argv, command_cls, command=command, **kwargs)
    elif argv is None and command is None and context.command_cls is command_cls and not kwargs:
        return context
    else:
        return context._sub_context(command_cls, argv=argv, command=command, **kwargs)


def get_context(command: Command) -> Context:
    """
    :param command: An initialized Command object
    :return: The Context associated with the given Command
    """
    try:
        return command._Command__ctx  # noqa
    except AttributeError as e:
        raise TypeError('get_context only supports Command objects') from e


def get_parsed(
    command: Command, to_call: Callable = None, default: Any = None, include_defaults: Bool = True
) -> dict[str, Any]:
    """
    Provides a way to obtain all of the arguments that were parsed for the given Command as a dictionary.

    If the parsed arguments are intended to be used to call a particular function/method, or to initialize a particular
    class, then that callable can be provided as the ``to_call`` parameter to filter the parsed arguments to only the
    ones that would be accepted by it.  It will not be called by this function.

    If the callable accepts any :attr:`VAR_KEYWORD <python:inspect.Parameter.kind>` parameters (i.e., ``**kwargs``),
    then those param names will not be used for filtering.  That is, if the command has a Parameter named ``kwargs``
    and the callable accepts ``**kwargs``, the ``kwargs`` key will not be included in the argument dict returned by
    this function.  If any of the parameters of the given callable cannot be passed as a keyword argument (i.e.,
    :attr:`POSITIONAL_ONLY or VAR_POSITIONAL <python:inspect.Parameter.kind>`), then they must be handled after calling
    this function.  They will be included in the returned dict.

    :param command: An initialized Command object for which arguments were already parsed.
    :param to_call: A :class:`callable <python:collections.abc.Callable>` (function, method, class, etc.) that should
      be used to filter the parsed arguments.  If provided, then only the keys that match the callable's signature will
      be included in the returned dictionary of parsed arguments.
    :param default: The default value to use for parameters that raise :class:`.MissingArgument` when attempting to
      obtain their result values.
    :param include_defaults: Whether default values should be included in the returned results.  If False, only
      user-provided values will be included.
    :return: A dictionary containing all of the (optionally filtered) arguments that were parsed.  The keys in the
      returned dict match the names assigned to the Parameters in the given Command.
    """
    parsed = get_context(command).get_parsed(command, default=default, include_defaults=include_defaults)
    if to_call is not None:
        sig = Signature.from_callable(to_call)
        keys = {k for k, p in sig.parameters.items() if p.kind != _Parameter.VAR_KEYWORD}
        parsed = {k: v for k, v in parsed.items() if k in keys}

    return parsed


def get_raw_arg(command: Command, parameter: Parameter) -> Any:
    """Retrieve the raw parsed argument value(s) provided for the given Parameter"""
    return get_context(command).get_parsed_value(parameter)


# endregion
