"""
Containers for option strings

:author: Doug Skrypa
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Collection, Union, Iterator, List, Set, Tuple

from ..config import OptionNameMode, DEFAULT_CONFIG
from ..exceptions import ParameterDefinitionError

if TYPE_CHECKING:
    from ..typing import Bool

__all__ = ['OptionStrings', 'TriFlagOptionStrings']


class OptionStrings:
    __slots__ = ('name_mode', '_long', '_short', 'combinable', '_display_long')
    name_mode: Optional[OptionNameMode]
    combinable: Set[str]
    _display_long: Set[str]
    _long: Set[str]
    _short: Set[str]

    def __init__(self, option_strs: Collection[str], name_mode: Union[OptionNameMode, str] = None):
        self.name_mode = OptionNameMode(name_mode) if name_mode is not None else None
        self._display_long = self._long = {opt for opt in option_strs if opt.startswith('--')}
        self._short = short_opts = {opt for opt in option_strs if 1 == opt.count('-', 0, 2)}
        self.combinable = {opt[1:] for opt in short_opts if len(opt) == 2}
        bad_opts = ', '.join(opt for opt in short_opts if '-' in opt[1:])
        if bad_opts:
            raise ParameterDefinitionError(f"Bad short option(s) - may not contain '-': {bad_opts}")

    def __repr__(self) -> str:
        options = ', '.join(self.all_option_strs())
        return f'<{self.__class__.__name__}[name_mode={self.name_mode}][{options}]>'

    @classmethod
    def _sort_options(cls, options: Collection[str]):
        return sorted(options, key=lambda opt: (-len(opt), opt))

    def has_long(self) -> Bool:
        """Whether any (primary / non-alternate, for TriFlag) long option strings were defined"""
        return self._long  # Explicit values were provided during param init

    def update(self, name: str):
        """
        Called by :meth:`.BaseOption.__set_name__` to add the assigned name to the long option strings for this param.
        """
        if self.has_long():
            return

        mode = self.name_mode or DEFAULT_CONFIG.option_name_mode
        mode_val: int = mode._value_  # noqa # This Flag doesn't subclass int due to breakage in 3.11
        if mode_val & 4:  # any option was set
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

    all_option_strs = option_strs


class TriFlagOptionStrings(OptionStrings):
    __slots__ = ('_alt_prefix', '_alt_long', '_alt_short')
    _alt_prefix: Optional[str]
    _alt_short: Optional[str]
    _alt_long: Union[Set[str], Tuple[str]]

    def has_long(self) -> Bool:
        """Whether any primary / non-alternate long option strings were defined"""
        return self._long.difference(self._alt_long)

    def add_alts(self, prefix: Optional[str], long: Optional[str], short: Optional[str]):
        self._alt_prefix = prefix
        self._alt_long = (long,) if long else set()
        self._alt_short = short

    def update_alts(self, name: str):
        """
        Called by :meth:`.TriFlag.__set_name__` to add the assigned name to the alt long option strings for this param.
        """
        if self._alt_long:
            return

        mode = self.name_mode or DEFAULT_CONFIG.option_name_mode
        mode_val: int = mode._value_  # noqa # This Flag doesn't subclass int due to breakage in 3.11
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

    def option_strs(self, alt: bool = False) -> Iterator[str]:
        if alt:
            yield from self.alt_option_strs()
        else:
            yield from self.primary_option_strs()

    def all_option_strs(self) -> Iterator[str]:
        yield from self.option_strs(False)
        yield from self.option_strs(True)
