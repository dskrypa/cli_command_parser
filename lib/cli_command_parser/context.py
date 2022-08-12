"""
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

    def __enter__(self) -> Context:
        _context_stack.get().append(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        _context_stack.get().pop()

    @cached_property
    def params(self) -> Optional[CommandParameters]:
        try:
            return self.command.__class__.params(self.command)
        except AttributeError:  # self.command is None
            return None

    def get_error_handler(self) -> Union[ErrorHandler, NullErrorHandler]:
        error_handler = self.config.error_handler
        if error_handler is _NotSet:
            return extended_error_handler
        elif error_handler is None:
            return NullErrorHandler()
        else:
            return error_handler

    def _sub_context(self, command: CommandType, argv: Optional[Sequence[str]] = None, **kwargs) -> Context:
        if argv is None:
            argv = self.remaining
        return self.__class__(argv, command, parent=self, **kwargs)

    def get_parsed(self, exclude: Collection[Parameter] = (), recursive: Bool = True) -> Dict[str, Any]:
        # TODO: Document that this can provide a dict of name:value
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

    def get_parsing_value(self, param: Parameter):
        try:
            return self._parsing[param]
        except KeyError:
            self._parsing[param] = value = param._init_value_factory()
            return value

    def set_parsing_value(self, param: Parameter, value: Any):
        self._parsing[param] = value

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

    def record_action(self, param: ParamOrGroup, val_count: int = 1):
        self._provided[param] += val_count

    def num_provided(self, param: ParamOrGroup) -> int:
        return self._provided[param]

    @cached_property
    def parsed_action_flags(self) -> Tuple[int, List[ActionFlag], List[ActionFlag]]:
        parsing = self._parsing
        try:
            action_flags = sorted(p for p in self.params.action_flags if p in parsing)
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
        flags = self.parsed_always_available_action_flags if self.failed else self.parsed_action_flags[1]
        for action_flag in flags:
            self.actions_taken += 1
            yield action_flag

    @property
    def after_main_actions(self) -> Iterator[ActionFlag]:
        for action_flag in self.parsed_action_flags[2]:
            self.actions_taken += 1
            yield action_flag

    @cached_property
    def parsed_always_available_action_flags(self) -> Tuple[ActionFlag, ...]:
        parsing = self._parsing
        try:
            return tuple(p for p in self.params.always_available_action_flags if p in parsing)
        except AttributeError:  # self.command is None
            return ()

    @property
    def terminal_width(self) -> int:
        if self._terminal_width is not None:
            return self._terminal_width
        return _TERMINAL.width


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
    try:
        context = get_current_context()
    except NoActiveContext:
        return Context(argv, command_cls, **kwargs)
    else:
        if argv is None and context.command is command_cls and not kwargs:
            return context
        else:
            return context._sub_context(command_cls, argv=argv, **kwargs)


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


def get_context(command: Command) -> Context:
    try:
        return command._Command__ctx  # noqa
    except AttributeError as e:
        raise TypeError('get_context only supports Command objects') from e


def get_parsed(command: Command, to_call: Callable = None) -> Dict[str, Any]:
    parsed = get_context(command).get_parsed()
    if to_call is not None:
        sig = Signature.from_callable(to_call)
        keys = {k for k, p in sig.parameters.items() if p.kind != _Parameter.VAR_KEYWORD}
        parsed = {k: v for k, v in parsed.items() if k in keys}

    return parsed
