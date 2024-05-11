"""
Containers for option strings

:author: Doug Skrypa
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Collection, Iterator, Optional, Union

from ..config import DEFAULT_CONFIG, OptionNameMode
from ..exceptions import ParameterDefinitionError
from ..utils import _NotSet

if TYPE_CHECKING:
    from ..typing import Bool

__all__ = ['OptionStrings', 'TriFlagOptionStrings']


class OptionStrings:
    """Container for the option strings registered for a given BaseOption (or subclass thereof)."""

    __slots__ = ('name_mode', '_long', '_short', 'combinable', '_display_long')
    name_mode: Optional[OptionNameMode]
    combinable: set[str]
    _display_long: set[str]
    _long: set[str]
    _short: set[str]

    def __init__(self, option_strs: Collection[str], name_mode: Union[OptionNameMode, str, None] = _NotSet):
        self.name_mode = OptionNameMode(name_mode) if name_mode is not _NotSet else None
        long_opts, short_opts = _split_options(option_strs)
        self._display_long = self._long = long_opts
        self._short = short_opts
        self.combinable = {opt[1:] for opt in short_opts if len(opt) == 2}

    def __repr__(self) -> str:
        options = ', '.join(self.all_option_strs())
        return f'<{self.__class__.__name__}[name_mode={self.name_mode}][{options}]>'

    def has_long(self) -> Bool:
        """Whether any (primary / non-alternate, for TriFlag) long option strings were defined"""
        return self._long  # Explicit values were provided during param init

    def has_min_opts(self) -> Bool:
        """Returns a truthy value if the minimum required number of option strings have been registered"""
        return self._long or self._short

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
            option = f'--{name.replace("_", "-")}'
            self._long.add(option)
            if mode_val & 16:  # OptionNameMode.BOTH_DASH = OptionNameMode.DASH | 4 | 16
                self._display_long.add(option)
        if mode & OptionNameMode.UNDERSCORE:
            option = f'--{name}'
            self._long.add(option)
            if mode_val & 8:  # OptionNameMode.BOTH_UNDERSCORE = OptionNameMode.DASH | 4 | 8
                self._display_long.add(option)

    def get_sets(self) -> tuple[set[str], set[str]]:
        return self._long, self._short

    @property
    def long(self) -> list[str]:
        return sorted(self._long, key=_options_sort_key)

    @property
    def short(self) -> list[str]:
        return sorted(self._short, key=_options_sort_key)

    @property
    def display_long(self) -> list[str]:
        return sorted(self._display_long, key=_options_sort_key)

    def get_usage_opt(self) -> str:
        return next(self.option_strs())

    def option_strs(self) -> Iterator[str]:
        yield from self.display_long
        yield from self.short

    all_option_strs = option_strs


class TriFlagOptionStrings(OptionStrings):
    """Container for the option strings registered for a given TriFlag."""

    __slots__ = ('_alt_prefix', '_alt_long', '_alt_short')
    _alt_prefix: Optional[str]
    _alt_short: Optional[str]
    _alt_long: Union[set[str], tuple[str]]

    def has_long(self) -> Bool:
        """Whether any primary / non-alternate long option strings were defined"""
        return self._long.difference(self._alt_long)

    def has_min_opts(self) -> Bool:
        return next(self.option_strs(False), None) and next(self.option_strs(True), None)

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
            option = f'--{self._alt_prefix}-{name.replace("_", "-")}'
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
    def alt_allowed(self) -> set[str]:
        allowed = set(self._alt_long)
        if self._alt_short:
            allowed.add(self._alt_short)
            allowed.add(self._alt_short[1:])
        return allowed

    # @property
    # def long_primary(self) -> List[str]:
    #     return [opt for opt in self.long if opt not in self._alt_long]

    @property
    def display_long_primary(self) -> list[str]:
        return [opt for opt in self.display_long if opt not in self._alt_long]

    @property
    def short_primary(self) -> list[str]:
        return [opt for opt in self.short if opt != self._alt_short]

    # @property
    # def long_alt(self) -> List[str]:
    #     return sorted(self._alt_long, key=_options_sort_key)

    @property
    def display_long_alt(self) -> list[str]:
        return [opt for opt in self.display_long if opt in self._alt_long]

    @property
    def short_alt(self) -> list[str]:
        return [self._alt_short] if self._alt_short else []

    def primary_option_strs(self) -> Iterator[str]:
        yield from self.display_long_primary
        yield from self.short_primary

    def alt_option_strs(self) -> Iterator[str]:
        yield from self.display_long_alt
        yield from self.short_alt

    def get_usage_opt(self, alt: bool = False) -> str:
        return next(self.option_strs(alt))

    def option_strs(self, alt: bool = False) -> Iterator[str]:
        if alt:
            yield from self.alt_option_strs()
        else:
            yield from self.primary_option_strs()

    def all_option_strs(self) -> Iterator[str]:
        yield from self.option_strs(False)
        yield from self.option_strs(True)


def _options_sort_key(opt: str):
    """Used to sort option strings in descending length order (alphanumeric order for options with the same length)"""
    return -len(opt), opt


def _split_options(opt_strs: Collection[str]) -> tuple[set[str], set[str]]:
    """Split long and short option strings and ensure that all of the provided option strings are valid."""
    long_opts, short_opts, bad_opts, bad_short = set(), set(), [], []
    for opt in opt_strs:
        if not opt:  # Ignore None / empty strings / etc
            continue  # Only raise an exception if invalid values that were intended to be used were provided
        elif not 0 < opt.count('-', 0, 3) < 3 or opt.endswith('-') or '=' in opt:
            bad_opts.append(opt)
        elif opt.startswith('--'):
            long_opts.add(opt)
        elif '-' in opt[2:]:
            bad_short.append(opt)
        else:
            short_opts.add(opt)

    if bad_opts:
        bad = ', '.join(map(repr, bad_opts))
        raise ParameterDefinitionError(
            f"Bad option(s) - they must start with '--' or '-', may not end with '-', and may not contain '=': {bad}"
        )
    elif bad_short:
        raise ParameterDefinitionError(
            f"Bad short option(s) - they may not contain '-': {', '.join(map(repr, bad_short))}"
        )

    return long_opts, short_opts
