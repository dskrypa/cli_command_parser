"""
:author: Doug Skrypa
"""

import sys
from collections import defaultdict
from functools import cached_property
from threading import local
from typing import TYPE_CHECKING, Any, Union, Sequence, Optional, Type, Iterator, Collection

from .parameters import Parameter, ParamOrGroup, Param, ActionFlag, SubCommand, Action
from .utils import Bool

if TYPE_CHECKING:
    from .commands import CommandType
    from .command_parameters import CommandParameters

__all__ = ['Context']


class ConfigOption:
    def __set_name__(self, owner, name: str):
        self.name = name

    def get_value(self, ctx: 'Context', ctx_cls):
        try:
            return ctx.__dict__[self.name]
        except KeyError:
            if parent := ctx.parent:
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
        try:
            config = ctx.command._config_
        except AttributeError:
            return None
        else:
            return getattr(config, self.name)

    def __set__(self, ctx: 'Context', value: Optional[Bool]):
        if value is not None:
            ctx.__dict__[self.name] = value


class Context:
    _local = local()
    ignore_unknown = ConfigOption()
    # parse_unknown = ConfigOption()
    allow_missing = ConfigOption()
    multiple_action_flags = ConfigOption()
    action_after_action_flags = ConfigOption()

    def __init__(
        self,
        argv: Optional[Sequence[str]] = None,
        command: Optional['CommandType'] = None,
        parent: Optional['Context'] = None,
        *,
        ignore_unknown: Bool = None,
        # parse_unknown: Bool = None,
        allow_missing: Bool = None,
        multiple_action_flags: Bool = None,
        action_after_action_flags: Bool = None,
    ):
        self.argv = sys.argv[1:] if argv is None else argv
        self.remaining = list(self.argv)
        self.command = command
        self.parent = parent
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
        self.ignore_unknown = ignore_unknown
        # self.parse_unknown = parse_unknown
        self.allow_missing = allow_missing
        self.multiple_action_flags = multiple_action_flags
        self.action_after_action_flags = action_after_action_flags

    @classmethod
    def get_current(cls, silent: bool = False) -> Optional['Context']:
        try:
            return cls._local.stack[-1]
        except (AttributeError, IndexError) as e:
            if silent:
                return None
            raise RuntimeError('There is no active context') from e

    def __enter__(self) -> 'Context':
        self._local.__dict__.setdefault('stack', []).append(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._local.stack.pop()

    @cached_property
    def params(self) -> Optional['CommandParameters']:
        try:
            return self.command.params
        except AttributeError:  # self.command is None
            return None

    def get_parsed(self, exclude: Collection[Parameter] = (), recursive: Bool = True) -> dict[str, Any]:
        if recursive and (parent := self.parent):
            parsed = parent.get_parsed(exclude, recursive)
        else:
            parsed = {}

        if params := self.params:
            for group in (params.positionals, params.options, (params.pass_thru,)):
                for param in group:
                    if param and param not in exclude:
                        parsed[param.name] = param.result_value(self)

        return parsed

    def get_parsing_value(self, param: Parameter):
        try:
            return self._parsing[param]
        except KeyError:
            self._parsing[param] = value = param._init_value_factory()
            return value

    def set_parsing_value(self, param: Parameter, value: Any):
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

    def missing(self) -> list[Parameter]:
        params = self.params
        # ignore = (SubCommand, Action)
        ignore = SubCommand
        missing: list[Parameter] = [
            p for p in params.positionals if p.required and self.num_provided(p) == 0 and not isinstance(p, ignore)
        ]
        missing.extend(p for p in params.options if p.required and self.num_provided(p) == 0)
        return missing

    @cached_property
    def parsed_action_flags(self) -> tuple[int, list['ActionFlag'], list['ActionFlag']]:
        parsing = self._parsing
        try:
            action_flags = sorted(p for p in self.params.action_flags if p in parsing)
        except AttributeError:  # self.command is None
            return 0, [], []

        if (num_flags := len(action_flags)) == 0:
            return 0, [], []

        for i, flag in enumerate(action_flags):
            if not flag.before_main:
                return num_flags, action_flags[:i], action_flags[i:]
        return num_flags, action_flags, []

    @property
    def before_main_actions(self) -> Iterator['ActionFlag']:
        for action_flag in self.parsed_action_flags[1]:
            self.actions_taken += 1
            yield action_flag

    @property
    def after_main_actions(self) -> Iterator['ActionFlag']:
        for action_flag in self.parsed_action_flags[2]:
            self.actions_taken += 1
            yield action_flag
