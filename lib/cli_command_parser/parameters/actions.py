"""
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Iterator, Iterable, Callable, Union, Sequence, TypeVar, NoReturn, List

from ..context import ctx
from ..exceptions import BadArgument, MissingArgument, InvalidChoice, TooManyArguments, ParamUsageError, ParamConflict
from ..inputs import InputType
from ..nargs import Nargs
from ..utils import _NotSet, camel_to_snake_case

if TYPE_CHECKING:
    from ..typing import OptStr, Param, T_co

__all__ = [
    'ParamAction',
    'Store',
    'Append',
    'StoreConst',
    'AppendConst',
    # 'StoreValueOrConst', 'AppendValueOrConst',
    'Count',
    'Concatenate',
    'StoreAll',
]

_PANotSet = object()

TD = TypeVar('TD')
Found = Union[int, NoReturn]


class ParamAction(ABC):
    __slots__ = ('param',)
    name: str
    default: TD = _NotSet
    accepts_values: bool = False
    accepts_consts: bool = False

    def __init_subclass__(
        cls, default: TD = _PANotSet, accepts_values: bool = None, accepts_consts: bool = None, **kwargs
    ):
        super().__init_subclass__(**kwargs)
        cls.name = camel_to_snake_case(cls.__name__)
        if default is not _PANotSet:
            cls.default = default
        if accepts_values is not None:
            cls.accepts_values = accepts_values
        if accepts_consts is not None:
            cls.accepts_consts = accepts_consts

    def __init__(self, param: Param):
        self.param = param

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        values, consts = self.accepts_values, self.accepts_consts
        return f'<{self.__class__.__name__}[{values=}, {consts=}](param={self.param.name})>'

    @property
    @abstractmethod
    def default_nargs(self) -> Nargs:
        raise NotImplementedError

    @abstractmethod
    def add_value(self, value: str, *, opt: str = None, combo: bool = False) -> Found:
        """
        Execute this action for the given Parameter and value.

        :param value: The value that was provided, if any.
        :param opt: The option string that preceded the given value in the case of optional params, or that
          represents a flag so a constant value can be stored, if any.
        :param combo: Only True when a short option was provided, where the option string was combined with
          either a real value or a sequence of 1-char combinable versions of short option strings.
        :return: The number of new values discovered
        """
        raise NotImplementedError

    def add_values(self, values: Sequence[str], *, opt: str = None, combo: bool = False) -> Found:
        added = 0
        for value in values:
            added += self.add_value(value, opt=opt, combo=combo)
        return added

    def add_const(self, *, opt: str = None, combo: bool = False) -> Found:  # noqa
        ctx.record_action(self.param)
        raise MissingArgument(self.param)

    def add_env_value(self, value: str, env_var: str):
        return self.add_value(value)

    def get_default(self, missing_default=_NotSet):
        if (default := self.param.default) is not _NotSet:
            return self.finalize_default(default)
        return self.default

    def finalize_default(self, value):
        if (type_func := self.param.type) and isinstance(type_func, InputType):
            return type_func.fix_default(value)
        return value

    def finalize_value(self, value):
        return value

    def get_maybe_poppable_values(self):
        return []

    def get_maybe_poppable_values_and_counts(self):
        values = self.get_maybe_poppable_values()
        if not values:
            return [], []
        n_values = len(values)
        satisfied = self.param.nargs.satisfied
        return values, [i for i in range(1, n_values) if satisfied(n_values - i)]

    def can_reset(self) -> bool:
        return False

    def prep_and_validate(self, values: Sequence[str], combo: bool) -> Iterator[T_co]:
        prepare_value, validate = self.param.prepare_value, self.param.validate
        for value in values:
            value = prepare_value(value, combo)
            validate(value)
            yield value

    def would_accept(self, value: str, combo: bool = False) -> bool:
        try:
            normalized = self.param.prepare_value(value, combo, True)
        except BadArgument:
            return False
        return self.param.is_valid_arg(normalized)


# region Mixins


class ValueMixin:
    __slots__ = ()
    param: Param
    get_default: Callable

    def set_value(self, value):
        if (prev := ctx.get_parsed_value(self.param)) is not _NotSet:
            raise ParamUsageError(
                self.param, f'can only be specified once - found multiple values: {prev!r}, {value!r}'
            )

        ctx.set_parsed_value(self.param, value)

    def append_value(self, value):
        parsed = ctx.get_parsed_value(self.param)
        if parsed is _NotSet:
            parsed = self.get_default()
            ctx.set_parsed_value(self.param, parsed)
        elif self.param.nargs.max_reached(parsed):
            raise TooManyArguments(self.param, f'already found {len(parsed)} values')

        parsed.append(value)

    def extend_values(self, values: Iterable[T_co]):
        parsed = ctx.get_parsed_value(self.param)
        if parsed is _NotSet:
            parsed = self.get_default()
            ctx.set_parsed_value(self.param, parsed)

        parsed.extend(values)


class ConstMixin:
    __slots__ = ()
    param: Param
    get_default: Callable
    add_const: Callable
    add_value: Callable

    def __init_subclass__(cls, append: bool = False, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._append = append

    def get_const(self, value: OptStr, opt: str = None):
        if value is None:
            return self.param.get_const(opt)
        raise BadArgument(self.param, f'does not accept values, but {value=} was provided')

    def set_const(self, const):
        parsed = ctx.get_parsed_value(self.param)
        if parsed is not _NotSet and parsed != const:
            raise ParamConflict([self.param])

        ctx.set_parsed_value(self.param, const)

    def append_const(self, const):
        parsed = ctx.get_parsed_value(self.param)
        if parsed is _NotSet:
            parsed = self.get_default()
            ctx.set_parsed_value(self.param, parsed)

        parsed.append(const)

    # def extend_consts(self, consts):
    #     parsed = ctx.get_parsed_value(self.param)
    #     if parsed is _NotSet:
    #         parsed = self.get_default()
    #         ctx.set_parsed_value(self.param, parsed)
    #
    #     parsed.extend(consts)

    def add_env_value(self, value: str, env_var: str):
        const, use_value = self.param.get_env_const(value, env_var)
        if const is _NotSet:
            return self.add_value(value)
        elif use_value:
            ctx.record_action(self.param)
            if self._append:
                self.append_const(const)
            else:
                self.set_const(const)
            return 1
        elif const:
            return self.add_const()


# endregion


class Store(ValueMixin, ParamAction, default=None, accepts_values=True):
    __slots__ = ()
    default_nargs = Nargs(1)

    def add_value(self, value: str, *, opt: str = None, combo: bool = False) -> Found:
        ctx.record_action(self.param)
        value = self.param.prepare_value(value, combo)
        self.param.validate(value)
        self.set_value(value)
        return 1

    def add_values(self, values: Sequence[str], *, opt: str = None, combo: bool = False) -> Found:
        ctx.record_action(self.param)
        if not values:
            raise MissingArgument(self.param)
        elif (val_count := len(values)) not in (nargs := self.param.nargs):
            raise BadArgument(self.param, f'expected {nargs=} values but found {val_count}')

        self.set_value([value for value in self.prep_and_validate(values, combo)])
        return val_count

    def would_accept(self, value: str, combo: bool = False) -> bool:
        if ctx.get_parsed_value(self.param) is not _NotSet:
            return False
        return super().would_accept(value, combo)


class Append(ValueMixin, ParamAction, accepts_values=True):
    __slots__ = ()
    default_nargs = Nargs('+')

    def add_value(self, value: str, *, opt: str = None, combo: bool = False) -> Found:
        ctx.record_action(self.param)
        value = self.param.prepare_value(value, combo)
        self.param.validate(value)
        self.append_value(value)
        return 1

    def add_values(self, values: Sequence[str], *, opt: str = None, combo: bool = False) -> Found:
        ctx.record_action(self.param)
        if not values:
            raise MissingArgument(self.param)
        elif (val_count := len(values)) not in (nargs := self.param.nargs):
            raise BadArgument(self.param, f'expected {nargs=} values but found {val_count}')

        self.extend_values(value for value in self.prep_and_validate(values, combo))
        return val_count

    def get_default(self, missing_default=_NotSet):
        if (default := self.param.default) is not _NotSet:
            return self.finalize_default(default)
        return []

    def finalize_default(self, value):
        if self.param.strict_default:
            return value

        if (type_func := self.param.type) and isinstance(type_func, InputType):
            fix_default = type_func.fix_default
        else:
            fix_default = None

        if not isinstance(value, str):
            try:
                next(iter(value), None)
            except TypeError:
                pass
            else:
                if fix_default:
                    return [fix_default(v) for v in value]
                elif isinstance(value, list):
                    return value[:]
                return list(value)

        return [fix_default(value)] if fix_default else [value]

    def finalize_value(self, value):
        if (val_count := len(value)) not in self.param.nargs:
            raise BadArgument(self.param, f'expected nargs={self.param.nargs} values but found {val_count}')
        return value

    def get_maybe_poppable_values(self):
        if not self.param.nargs.variable or self.param.type not in (None, str):
            return []
        return ctx.get_parsed_value(self.param)

    def can_reset(self) -> bool:
        if self.param.type not in (None, str):
            return False
        return ctx.has_parsed_value(self.param)

    def would_accept(self, value: str, combo: bool = False) -> bool:
        parsed = ctx.get_parsed_value(self.param)
        if parsed is not _NotSet and self.param.nargs.max_reached(parsed):
            return False
        return super().would_accept(value, combo)


class StoreConst(ConstMixin, ParamAction, default=None, accepts_consts=True):
    __slots__ = ()
    default_nargs = Nargs(0)

    def add_const(self, *, opt: str = None, combo: bool = False) -> Found:
        ctx.record_action(self.param)
        self.set_const(self.param.get_const(opt))
        return 1

    def add_value(self, value: str, *, opt: str = None, combo: bool = False) -> Found:
        ctx.record_action(self.param)
        self.set_const(self.get_const(value, opt))
        return 1

    def would_accept(self, value: str, combo: bool = False) -> bool:
        return False


class AppendConst(ConstMixin, ParamAction, append=True, accepts_consts=True):
    __slots__ = ()
    default_nargs = Nargs(0)

    def add_const(self, *, opt: str = None, combo: bool = False) -> Found:
        ctx.record_action(self.param)
        # TODO: Fix nargs consistency for overall vs per-arg
        self.append_const(self.param.get_const(opt))
        return 1

    def add_value(self, value: str, *, opt: str = None, combo: bool = False) -> Found:
        ctx.record_action(self.param)
        # TODO: Fix nargs consistency for overall vs per-arg
        self.append_const(self.get_const(value, opt))
        return 1

    def get_default(self, missing_default=_NotSet):
        return []

    def would_accept(self, value: str, combo: bool = False) -> bool:
        return False


# class StoreValueOrConst(ConstMixin, Store, accepts_values=True, accepts_consts=True):
#     __slots__ = ()
#     default_nargs = Nargs('?')
#
#     def add_const(self, *, opt: str = None, combo: bool = False) -> Found:
#         ctx.record_action(self.param)
#         self.set_const(self.param.get_const(opt))
#         return 1
#
#
# class AppendValueOrConst(ConstMixin, Append, append=True, accepts_values=True, accepts_consts=True):
#     __slots__ = ()
#     default_nargs = Nargs('?')
#
#     def add_const(self, *, opt: str = None, combo: bool = False) -> Found:
#         ctx.record_action(self.param)
#         self.append_const(self.param.get_const(opt))
#         return 1


class Count(ParamAction, accepts_values=True, accepts_consts=True):
    __slots__ = ()
    default_nargs = Nargs('?')

    def _add(self, value: int):
        parsed = ctx.get_parsed_value(self.param)
        if parsed is _NotSet:
            parsed = self.param.init

        ctx.set_parsed_value(self.param, parsed + value)

    def add_const(self, *, opt: str = None, combo: bool = False) -> Found:
        ctx.record_action(self.param)
        self._add(self.param.get_const(opt))
        return 1

    def add_value(self, value: str, *, opt: str = None, combo: bool = False) -> Found:
        ctx.record_action(self.param)
        value = self.param.prepare_value(value, combo)
        self.param.validate(value)
        self._add(value)
        return 1


class Concatenate(Append):
    __slots__ = ()

    def add_value(self, value: str, *, opt: str = None, combo: bool = False) -> Found:
        param = self.param
        values = value.split()
        if not param.is_valid_arg(' '.join(values)):
            ctx.record_action(param)
            raise InvalidChoice(param, value, param.choices)

        parsed = ctx.get_parsed_value(param)
        if parsed is _NotSet:
            ctx.set_parsed_value(param, values)
        else:
            parsed.extend(values)

        n_values = len(values)
        ctx.record_action(param, n_values)
        return n_values

    def finalize_default(self, value):
        return value

    def finalize_value(self, value):
        choice = ' '.join(super().finalize_value(value))
        if choice not in self.param.choices:
            raise InvalidChoice(self.param, choice, self.param.choices)
        return choice


class StoreAll(Store):
    __slots__ = ()
    default_nargs = Nargs('REMAINDER')

    def add_values(self, values: List[str], *, opt: str = None, combo: bool = False) -> Found:
        param = self.param
        ctx.record_action(param)

        if (value := ctx.get_parsed_value(param)) is not _NotSet:
            raise ParamUsageError(
                param, f'can only be specified once - found {values=} but a stored {value=} already exists'
            )

        values = [param.prepare_value(v) for v in values]
        ctx.set_parsed_value(param, values)
        return len(values)
