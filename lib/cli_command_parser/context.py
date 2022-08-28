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
from inspect import Signature, Parameter as _Parameter
from typing import TYPE_CHECKING, Any, Callable, Union, Sequence, Optional, Iterator, Collection, cast
from typing import Dict, Tuple, List

try:
    from functools import cached_property
except ImportError:
    from .compat import cached_property

from .config import CommandConfig, DEFAULT_CONFIG
from .error_handling import ErrorHandler, NullErrorHandler, extended_error_handler
from .exceptions import NoActiveContext
from .utils import Bool, _NotSet, Terminal

if TYPE_CHECKING:
    from .core import CommandType, AnyConfig
    from .command_parameters import CommandParameters
    from .commands import Command
    from .parameters import Parameter, ParamOrGroup, ActionFlag

__all__ = ['Context', 'ctx', 'get_current_context', 'get_or_create_context', 'get_context', 'get_parsed']

_context_stack = ContextVar('cli_command_parser.context.stack', default=[])
_TERMINAL = Terminal()


class Context(AbstractContextManager):  # Extending AbstractContextManager to make PyCharm's type checker happy
    """
    The parsing context.

    Holds user input while parsing, and holds the parsed values.  Handles config overrides / hierarchy for settings that
    affect parser behavior.
    """

    config: CommandConfig

    def __init__(
        self,
        argv: Optional[Sequence[str]] = None,
        command: Optional[CommandType] = None,
        parent: Optional[Context] = None,
        config: AnyConfig = None,
        terminal_width: int = None,
        **kwargs,
    ):
        self.argv = sys.argv[1:] if argv is None else argv
        self.remaining = list(self.argv)
        self.command = command
        self.parent = parent
        self.failed = False
        self.config = _normalize_config(config, kwargs, parent, command)
        self._terminal_width = terminal_width
        if parent is not None:
            self._parsing = parent._parsing.copy()
            self.unknown = parent.unknown.copy()
            self._provided = parent._provided.copy()
        else:
            self._parsing = {}
            self.unknown = {}
            self._provided = defaultdict(int)
        self.actions_taken = 0

    # region Internal Methods

    def _sub_context(self, command: CommandType, argv: Optional[Sequence[str]] = None, **kwargs) -> Context:
        if argv is None:
            argv = self.remaining
        return self.__class__(argv, command, parent=self, **kwargs)

    def __enter__(self) -> Context:
        _context_stack.get().append(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        _context_stack.get().pop()

    def __contains__(self, param: Union[ParamOrGroup, str, Any]) -> bool:
        try:
            self._parsing[param]
        except KeyError:
            if isinstance(param, str):
                try:
                    next((v for p, v in self._parsing.items() if p.name == param))
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

    def get_parsed(self, exclude: Collection[Parameter] = (), recursive: Bool = True) -> Dict[str, Any]:
        """
        Returns all of the parsed arguments as a dictionary.

        The :ref:`get_parsed() <advanced:Parsed Args as a Dictionary>` helper function provides an easier way to access
        this functionality.

        :param exclude: Parameter objects that should be excluded from the returned results
        :param recursive: Whether parsed arguments should be recursively gathered from parent Commands
        :return: A dictionary containing all of the arguments that were parsed.  The keys in the returned dict match
          the names assigned to the Parameters in the Command associated with this Context.
        """
        with self:
            if recursive and self.parent:
                parsed = self.parent.get_parsed(exclude, recursive)
            else:
                parsed = {}

            params = self.params
            if params:
                for group in (params.positionals, params.options, (params.pass_thru,)):
                    for param in group:
                        if param and param not in exclude:
                            parsed[param.name] = param.result_value()

        return parsed

    @cached_property
    def params(self) -> Optional[CommandParameters]:
        """
        The :class:`.CommandParameters` object that contains the categorized Parameters from the Command associated
        with this Context.
        """
        try:
            return self.command.__class__.params(self.command)
        except AttributeError:  # self.command is None
            return None

    def get_error_handler(self) -> Union[ErrorHandler, NullErrorHandler]:
        """Returns the :class:`.ErrorHandler` configured to be used."""
        error_handler = self.config.error_handler
        if error_handler is _NotSet:
            return extended_error_handler
        elif error_handler is None:
            return NullErrorHandler()
        else:
            return error_handler

    # region Parsing

    def get_parsing_value(self, param: Parameter):
        """Not intended to be called by users.  Used by Parameters to access their parsed values."""
        try:
            return self._parsing[param]
        except KeyError:
            self._parsing[param] = value = param._init_value_factory()
            return value

    def set_parsing_value(self, param: Parameter, value: Any):
        """Not intended to be called by users.  Used by Parameters during parsing to store parsed values."""
        self._parsing[param] = value

    def record_action(self, param: ParamOrGroup, val_count: int = 1):
        """
        Not intended to be called by users.  Used by Parameters during parsing to indicate that they were provided.
        """
        self._provided[param] += val_count

    def num_provided(self, param: ParamOrGroup) -> int:
        """Not intended to be called by users.  Used by Parameters during parsing to handle nargs."""
        return self._provided[param]

    # endregion

    # region Actions

    @cached_property
    def parsed_action_flags(self) -> Tuple[int, List[ActionFlag], List[ActionFlag]]:
        """
        Not intended to be accessed by users.  Returns a tuple containing the total number of action flags provided, the
        action flags to run before main, and the action flags to run after main.
        """
        parsing = self._parsing
        try:
            action_flags = [p for p in self.params.action_flags if p in parsing]  # already sorted in CommandParameters
        except AttributeError:  # self.command is None
            return 0, [], []

        if not action_flags:
            return 0, [], []

        num_flags = len(action_flags)
        for i, flag in enumerate(action_flags):
            if not flag.before_main:
                return num_flags, action_flags[:i], action_flags[i:]
        return num_flags, action_flags, []

    @property
    def before_main_actions(self) -> Iterator[ActionFlag]:
        """
        Not intended to be accessed by users.  Iterator that yields action flags to be executed before main while
        incrementing the counter of actions taken.
        """
        flags = self.parsed_always_available_action_flags if self.failed else self.parsed_action_flags[1]
        for action_flag in flags:
            self.actions_taken += 1
            yield action_flag

    @property
    def after_main_actions(self) -> Iterator[ActionFlag]:
        """
        Not intended to be accessed by users.  Iterator that yields action flags to be executed after main while
        incrementing the counter of actions taken.
        """
        for action_flag in self.parsed_action_flags[2]:
            self.actions_taken += 1
            yield action_flag

    @cached_property
    def parsed_always_available_action_flags(self) -> Tuple[ActionFlag, ...]:
        """
        Not intended to be accessed by users.  The action flags like the one for ``--help`` that should be executed
        regardless of whether errors were encountered during parsing.
        """
        parsing = self._parsing
        try:
            return tuple(p for p in self.params.always_available_action_flags if p in parsing)
        except AttributeError:  # self.command is None
            return ()

    # endregion


def _normalize_config(
    config: AnyConfig, kwargs: Dict[str, Any], parent: Optional[Context], command: Optional[CommandType]
) -> CommandConfig:
    if config is not None:
        if kwargs:
            raise ValueError(f'Cannot combine config={config!r} with keyword config arguments={kwargs}')
        elif isinstance(config, CommandConfig):
            return config
        kwargs = config

    parents = []
    if parent and parent.config:
        parents.append(parent.config)
    if command is not None:
        cmd_cfg = command.__class__.config(command)
        if cmd_cfg:
            parents.append(cmd_cfg)

    return CommandConfig(parents=parents, **kwargs)


class ContextProxy:
    """
    Proxy for the currently active :class:`Context` object.  Allows usage similar to the ``request`` object in Flask.

    This class should not be instantiated by users - use the common :data:`ctx` instance.
    """

    __slots__ = ()

    def __getattr__(self, attr: str):
        return getattr(get_current_context(), attr)

    def __setattr__(self, attr: str, value):
        return setattr(get_current_context(), attr, value)

    def __eq__(self, other) -> bool:
        return get_current_context() == other

    def __contains__(self, item) -> bool:
        return item in get_current_context()

    def __enter__(self):
        return get_current_context().__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        return get_current_context().__exit__(exc_type, exc_val, exc_tb)

    @property
    def terminal_width(self) -> int:
        try:
            return get_current_context().terminal_width
        except NoActiveContext:
            return _TERMINAL.width

    @property
    def config(self) -> CommandConfig:
        try:
            return get_current_context().config
        except NoActiveContext:
            return DEFAULT_CONFIG


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
    except (AttributeError, IndexError):
        if silent:
            return None
        raise NoActiveContext('There is no active context') from None


def get_or_create_context(command_cls: CommandType, argv: Sequence[str] = None, **kwargs) -> Context:
    """
    Used internally by Commands to re-use an existing user-activated Context, or to create a new Context if there was
    no active Context.
    """
    try:
        context = get_current_context()
    except NoActiveContext:
        return Context(argv, command_cls, **kwargs)
    else:
        if argv is None and context.command is command_cls and not kwargs:
            return context
        else:
            return context._sub_context(command_cls, argv=argv, **kwargs)


def get_context(command: Command) -> Context:
    """
    :param command: An initialized Command object
    :return: The Context associated with the given Command
    """
    try:
        return command._Command__ctx  # noqa
    except AttributeError as e:
        raise TypeError('get_context only supports Command objects') from e


def get_parsed(command: Command, to_call: Callable = None) -> Dict[str, Any]:
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
    :return: A dictionary containing all of the (optionally filtered) arguments that were parsed.  The keys in the
      returned dict match the names assigned to the Parameters in the given Command.
    """
    parsed = get_context(command).get_parsed()
    if to_call is not None:
        sig = Signature.from_callable(to_call)
        keys = {k for k, p in sig.parameters.items() if p.kind != _Parameter.VAR_KEYWORD}
        parsed = {k: v for k, v in parsed.items() if k in keys}

    return parsed


# endregion
