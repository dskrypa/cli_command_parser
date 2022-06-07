"""
:author: Doug Skrypa
"""

import sys
from collections import defaultdict
from contextlib import AbstractContextManager
from contextvars import ContextVar
from typing import TYPE_CHECKING, Any, Union, Sequence, Optional, Iterator, Collection, Callable, cast
from typing import Dict, Tuple, List

try:
    from functools import cached_property
except ImportError:
    from .compat import cached_property

from .config import CommandConfig, ShowDefaults, OptionNameMode
from .error_handling import ErrorHandler, NullErrorHandler, extended_error_handler
from .exceptions import NoActiveContext
from .utils import Bool, _NotSet

if TYPE_CHECKING:
    from .core import CommandType
    from .command_parameters import CommandParameters
    from .formatting.params import ParamHelpFormatter
    from .parameters import Parameter, ParamOrGroup, ActionFlag

__all__ = ['Context', 'ctx', 'get_current_context']

_context_stack = ContextVar('cli_command_parser.context.stack', default=[])


class ConfigOption:
    def __init__(self, default: Any = None):
        self.default = default

    def __set_name__(self, owner, name: str):
        self.name = name

    def get_value(self, ctx: 'Context', ctx_cls):
        try:
            return ctx.__dict__[self.name]
        except KeyError:
            parent = ctx.parent
            if parent:
                option = ctx_cls.__dict__[self.name]  # type: ConfigOption
                return option.get_value(parent, ctx_cls)
            raise

    def __get__(self, ctx: Optional['Context'], ctx_cls) -> Optional[Bool]:
        if ctx is None:
            return self
        try:
            return self.get_value(ctx, ctx_cls)
        except KeyError:
            pass

        command = ctx.command
        try:
            config = command.__class__.config(command)
        except AttributeError:
            if self.default is not None:
                return self.default
            return getattr(CommandConfig(), self.name)
        else:
            return getattr(config, self.name)

    def __set__(self, ctx: 'Context', value: Optional[Bool]):
        if value is not self.default:
            ctx.__dict__[self.name] = value


class Context(AbstractContextManager):  # Extending AbstractContextManager to make PyCharm's type checker happy
    """
    The parsing context.

    Holds user input while parsing, and holds the parsed values.  Handles config overrides / hierarchy for settings that
    affect parser behavior.
    """

    error_handler = ConfigOption(_NotSet)
    always_run_after_main = ConfigOption()
    multiple_action_flags = ConfigOption()
    action_after_action_flags = ConfigOption()
    ignore_unknown = ConfigOption()
    allow_missing = ConfigOption()
    allow_backtrack = ConfigOption()
    option_name_mode = ConfigOption()
    use_type_metavar = ConfigOption()
    show_defaults = ConfigOption()
    show_group_tree = ConfigOption()
    show_group_type = ConfigOption()
    param_formatter = ConfigOption()
    extended_epilog = ConfigOption()
    show_docstring = ConfigOption()
    # strict_action_punctuation = ConfigOption()
    # strict_sub_command_punctuation = ConfigOption()

    def __init__(
        self,
        argv: Optional[Sequence[str]] = None,
        command: Optional['CommandType'] = None,
        parent: Optional['Context'] = None,
        *,
        error_handler: Optional[ErrorHandler] = _NotSet,
        always_run_after_main: Bool = None,
        multiple_action_flags: Bool = None,
        action_after_action_flags: Bool = None,
        ignore_unknown: Bool = None,
        allow_missing: Bool = None,
        allow_backtrack: Bool = None,
        option_name_mode: Union[OptionNameMode, str] = None,
        use_type_metavar: Bool = None,
        show_defaults: Union[ShowDefaults, str] = None,
        show_group_tree: Bool = None,
        show_group_type: Bool = None,
        param_formatter: Callable[['ParamOrGroup'], 'ParamHelpFormatter'] = None,
        extended_epilog: Bool = None,
        show_docstring: Bool = None,
        # strict_action_punctuation: Bool = None,
        # strict_sub_command_punctuation: Bool = None,
    ):
        self.argv = sys.argv[1:] if argv is None else argv
        self.remaining = list(self.argv)
        self.command = command
        self.parent = parent
        self.failed = False
        if parent is not None:
            self._parsing = parent._parsing.copy()
            self.unknown = parent.unknown.copy()
            self._provided = parent._provided.copy()
        else:
            self._parsing = {}
            self.unknown = {}
            self._provided = defaultdict(int)
        self.actions_taken = 0

        # Command config overrides
        self.error_handler = error_handler
        self.always_run_after_main = always_run_after_main

        self.multiple_action_flags = multiple_action_flags
        self.action_after_action_flags = action_after_action_flags

        self.ignore_unknown = ignore_unknown
        self.allow_missing = allow_missing
        self.allow_backtrack = allow_backtrack
        self.option_name_mode = option_name_mode

        self.use_type_metavar = use_type_metavar
        if show_defaults is not None:
            self.show_defaults = ShowDefaults(show_defaults)
        self.show_group_tree = show_group_tree
        self.show_group_type = show_group_type
        self.param_formatter = param_formatter
        self.extended_epilog = extended_epilog
        self.show_docstring = show_docstring

        # self.strict_action_punctuation = strict_action_punctuation
        # self.strict_sub_command_punctuation = strict_sub_command_punctuation

    def __enter__(self) -> 'Context':
        _context_stack.get().append(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        _context_stack.get().pop()

    @cached_property
    def params(self) -> Optional['CommandParameters']:
        try:
            return self.command.__class__.params(self.command)
        except AttributeError:  # self.command is None
            return None

    def get_error_handler(self) -> Union[ErrorHandler, NullErrorHandler]:
        error_handler = self.error_handler
        if error_handler is _NotSet:
            return extended_error_handler
        elif error_handler is None:
            return NullErrorHandler()
        else:
            return error_handler

    def _sub_context(self, command: 'CommandType', argv: Optional[Sequence[str]] = None) -> 'Context':
        if argv is None:
            argv = self.remaining
        return self.__class__(argv, command, parent=self)

    def get_parsed(self, exclude: Collection['Parameter'] = (), recursive: Bool = True) -> Dict[str, Any]:
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

    def get_parsing_value(self, param: 'Parameter'):
        try:
            return self._parsing[param]
        except KeyError:
            self._parsing[param] = value = param._init_value_factory()
            return value

    def set_parsing_value(self, param: 'Parameter', value: Any):
        self._parsing[param] = value

    def __contains__(self, param: Union['ParamOrGroup', str, Any]) -> bool:
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

    def record_action(self, param: 'ParamOrGroup', val_count: int = 1):
        self._provided[param] += val_count

    def num_provided(self, param: 'ParamOrGroup') -> int:
        return self._provided[param]

    @cached_property
    def parsed_action_flags(self) -> Tuple[int, List['ActionFlag'], List['ActionFlag']]:
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
    def before_main_actions(self) -> Iterator['ActionFlag']:
        flags = self.parsed_always_available_action_flags if self.failed else self.parsed_action_flags[1]
        for action_flag in flags:
            self.actions_taken += 1
            yield action_flag

    @property
    def after_main_actions(self) -> Iterator['ActionFlag']:
        for action_flag in self.parsed_action_flags[2]:
            self.actions_taken += 1
            yield action_flag

    @cached_property
    def parsed_always_available_action_flags(self) -> Tuple['ActionFlag', ...]:
        parsing = self._parsing
        try:
            return tuple(p for p in self.params.always_available_action_flags if p in parsing)
        except AttributeError:  # self.command is None
            return ()


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


class ContextProxy:
    """
    Proxy for the currently active :class:`Context` object.  Allows usage similar to the ``request`` object in Flask.

    This class should not be instantiated by users - use the common :data:`ctx` instance.
    """

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


ctx: Context = cast(Context, ContextProxy())
