"""
Containers for option strings

:author: Doug Skrypa
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Collection, Union, Iterator, List, Set

from ..config import OptionNameMode
from ..exceptions import ParameterDefinitionError

if TYPE_CHECKING:
    from ..core import CommandType
    from .base import BaseOption
    from .options import TriFlag

__all__ = ['OptionStrings', 'TriFlagOptionStrings']


class OptionStrings:
    __slots__ = ('name_mode', '_long', '_short', 'combinable', '_display_long')

    def __init__(self, option_strs: Collection[str], name_mode: Union[OptionNameMode, str] = None):
        self.name_mode = OptionNameMode(name_mode) if name_mode is not None else None
        self._display_long = self._long = {opt for opt in option_strs if opt.startswith('--')}
        self._short = short_opts = {opt for opt in option_strs if 1 == opt.count('-', 0, 2)}
        self.combinable = {opt[1:] for opt in short_opts if len(opt) == 2}
        bad_opts = ', '.join(opt for opt in short_opts if '-' in opt[1:])
        if bad_opts:
            raise ParameterDefinitionError(f"Bad short option(s) - may not contain '-': {bad_opts}")

    @classmethod
    def _sort_options(cls, options: Collection[str]):
        return sorted(options, key=lambda opt: (-len(opt), opt))

    def update(self, param: BaseOption, command: CommandType, name: str):
        if self._long:
            return

        mode = self.name_mode if self.name_mode is not None else param._config(command).option_name_mode
        mode_val: int = mode._value_  # This Flag doesn't subclass int due to breakage in 3.11
        if mode_val & 4:
            self._display_long = self._display_long.copy()
        if mode & OptionNameMode.DASH:
            option = '--{}'.format(name.replace('_', '-'))
            self._long.add(option)
            if mode_val & 16:  # OptionNameMode.BOTH_DASH = OptionNameMode.DASH | 4 | 16
                self._display_long.add(option)
        if mode & OptionNameMode.UNDERSCORE:
            option = f'--{name}'
            self._long.add(option)
            if mode_val & 8:  # OptionNameMode.BOTH_UNDERSCORE = OptionNameMode.DASH | 4 | 8
                self._display_long.add(option)

    @property
    def long(self) -> List[str]:
        return self._sort_options(self._long)

    @property
    def short(self) -> List[str]:
        return self._sort_options(self._short)

    @property
    def display_long(self) -> List[str]:
        return self._sort_options(self._display_long)

    def option_strs(self) -> Iterator[str]:
        yield from self.display_long
        yield from self.short


class TriFlagOptionStrings(OptionStrings):
    __slots__ = ('_alt_prefix', '_alt_long', '_alt_short')

    def add_alts(self, prefix: Optional[str], long: Optional[str], short: Optional[str]):
        self._alt_prefix = prefix  # noqa
        self._alt_long = (long,) if long else set()  # noqa
        self._alt_short = short  # noqa

    def update_alts(self, param: TriFlag, command: CommandType, name: str):
        if self._alt_long:
            return

        mode = self.name_mode if self.name_mode is not None else param._config(command).option_name_mode
        mode_val: int = mode._value_  # This Flag doesn't subclass int due to breakage in 3.11
        if mode & OptionNameMode.DASH:
            option = '--{}-{}'.format(self._alt_prefix, name.replace('_', '-'))
            self._alt_long.add(option)
            self._long.add(option)
            if mode_val & 16:  # OptionNameMode.BOTH_DASH = OptionNameMode.DASH | 4 | 16
                self._display_long.add(option)
        if mode & OptionNameMode.UNDERSCORE:
            option = f'--{self._alt_prefix}_{name}'
            self._alt_long.add(option)
            self._long.add(option)
            if mode_val & 8:  # OptionNameMode.BOTH_UNDERSCORE = OptionNameMode.DASH | 4 | 8
                self._display_long.add(option)

    @property
    def alt_allowed(self) -> Set[str]:
        allowed = set(self._alt_long)
        short = self._alt_short
        if short:
            allowed.add(short)
            allowed.add(short[1:])
        return allowed

    # @property
    # def long_primary(self) -> List[str]:
    #     return [opt for opt in self.long if opt not in self._alt_long]

    @property
    def display_long_primary(self) -> List[str]:
        return [opt for opt in self.display_long if opt not in self._alt_long]

    @property
    def short_primary(self) -> List[str]:
        return [opt for opt in self.short if opt != self._alt_short]

    # @property
    # def long_alt(self) -> List[str]:
    #     return self._sort_options(self._alt_long)

    @property
    def display_long_alt(self) -> List[str]:
        return [opt for opt in self.display_long if opt in self._alt_long]

    @property
    def short_alt(self) -> List[str]:
        return [self._alt_short] if self._alt_short else []

    def primary_option_strs(self) -> Iterator[str]:
        yield from self.display_long_primary
        yield from self.short_primary

    def alt_option_strs(self) -> Iterator[str]:
        yield from self.display_long_alt
        yield from self.short_alt
