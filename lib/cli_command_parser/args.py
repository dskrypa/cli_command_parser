"""
:author: Doug Skrypa
"""

import sys
from collections import defaultdict
from functools import cached_property
from typing import Any, Union, Sequence, Optional, Type, Iterator

from .parameters import Parameter, ParamOrGroup, Param, ActionFlag

__all__ = ['Args']


class Args:
    """
    Stores the raw and parsed arguments.

    Keeps track of the actions that were taken before/during/after :meth:`~.commands.Command.main`

    :param args: The arguments that should be parsed (default: :data:`sys.argv`)
    """

    def __init__(self, args: Optional[Sequence[str]]):
        self.raw = sys.argv[1:] if args is None else args
        self.remaining = self.raw
        self._parsed = {}
        self._provided = defaultdict(int)
        self.actions_taken = 0

    def __repr__(self) -> str:
        provided = dict(self._provided)
        return f'<{self.__class__.__name__}[parsed={self._parsed}, remaining={self.remaining}, {provided=}]>'

    def record_action(self, param: 'ParamOrGroup', val_count: int = 1):
        self._provided[param] += val_count

    def num_provided(self, param: 'ParamOrGroup') -> int:
        return self._provided[param]

    def __contains__(self, param: Union['ParamOrGroup', str, Any]) -> bool:
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

    def __getitem__(self, param: Union['Parameter', str]):
        try:
            return self._parsed[param]
        except KeyError:
            if isinstance(param, str):
                try:
                    return next((v for p, v in self._parsed.items() if p.name == param))
                except StopIteration:
                    raise KeyError(f'{param=} was not provided / parsed') from None
            else:
                self._parsed[param] = value = param._init_value_factory()
                return value

    def __setitem__(self, param: 'Parameter', value):
        self._parsed[param] = value

    def find_all(self, param_type: Type['Param']) -> dict['Param', Any]:
        return {param: val for param, val in self._parsed.items() if isinstance(param, param_type)}

    @cached_property
    def _action_flags(self) -> tuple[dict['ActionFlag', Any], list['ActionFlag'], list['ActionFlag']]:
        action_flags = self.find_all(ActionFlag)
        before = []
        after = []
        for flag in action_flags:
            if flag.before_main:
                before.append(flag)
            else:
                after.append(flag)

        return action_flags, sorted(before), sorted(after)

    @property
    def action_flags(self) -> dict['ActionFlag', Any]:
        return self._action_flags[0]

    @property
    def before_main_actions(self) -> Iterator['ActionFlag']:
        for action_flag in self._action_flags[1]:
            self.actions_taken += 1
            yield action_flag

    @property
    def after_main_actions(self) -> Iterator['ActionFlag']:
        for action_flag in self._action_flags[2]:
            self.actions_taken += 1
            yield action_flag
