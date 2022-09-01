"""
Optional Parameters

:author: Doug Skrypa
"""

from __future__ import annotations

from functools import partial, update_wrapper, reduce
from operator import xor
from typing import TYPE_CHECKING, Any, Optional, Callable, Union, Tuple

from ..context import ctx
from ..exceptions import ParameterDefinitionError, BadArgument, CommandDefinitionError, ParamUsageError
from ..inputs import InputTypeFunc, normalize_input_type
from ..nargs import Nargs, NargsValue
from ..utils import _NotSet, Bool
from .base import BasicActionMixin, BaseOption, parameter_action
from .option_strings import TriFlagOptionStrings

if TYPE_CHECKING:
    from ..core import CommandType
    from ..commands import Command

__all__ = ['Option', 'Flag', 'TriFlag', 'ActionFlag', 'Counter', 'action_flag', 'before_main', 'after_main']
# TODO: envvar param to pull value from an env var (or tuple of vars, in order) if no value given, but env var is set?


class Option(BasicActionMixin, BaseOption):
    """
    A generic option that can be specified as ``--foo bar`` or by using other similar forms.

    :param option_strs: The long and/or short option prefixes for this option.  If no long prefixes are specified,
      then one will automatically be added based on the name assigned to this parameter.
    :param nargs: The number of values that are expected/required when this parameter is specified.  Defaults to 1.
      See :class:`.Nargs` for more info.
    :param action: The action to take on individual parsed values.  Actions must be defined as methods in classes
      that extend Parameter, and must be registered via :class:`.parameter_action`.  Defaults to ``store`` when
      ``nargs=1``, and to ``append`` otherwise.  A single value will be stored when ``action='store'``, and a list
      of values will be stored when ``action='append'``.
    :param default: The default value for this parameter if it is not specified.  Defaults to ``None`` if
      this parameter is not required; not used if it is required.
    :param required: Whether this parameter is required or not.  If it is required, then an exception will be
      raised if the user did not provide a value for this parameter.  Defaults to ``False``.
    :param type: A callable (function, class, etc.) that accepts a single string argument, which should be called
      on every value for this parameter to transform the value.  By default, no transformation is performed, and
      values will be strings.  If not specified, but a type annotation is detected, then that annotation will be
      used as if it was provided here.  When both are present, this argument takes precedence.
    :param kwargs: Additional keyword arguments to pass to :class:`.BaseOption`.
    """

    def __init__(
        self,
        *option_strs: str,
        nargs: NargsValue = None,
        action: str = _NotSet,
        default: Any = _NotSet,
        required: Bool = False,
        type: InputTypeFunc = None,  # noqa
        **kwargs,
    ):
        if nargs is not None:
            self.nargs = Nargs(nargs)
        if 0 in self.nargs:
            raise ParameterDefinitionError(f'Invalid nargs={self.nargs} - use Flag or Counter for Options with 0 args')
        if action is _NotSet:
            action = 'store' if self.nargs == 1 else 'append'
        elif action == 'store' and self.nargs != 1:
            raise ParameterDefinitionError(f'Invalid nargs={self.nargs} for action={action!r}')
        super().__init__(*option_strs, action=action, default=default, required=required, **kwargs)
        self.type = normalize_input_type(type, self.choices)
        if action == 'append':
            self._init_value_factory = list


# TODO: 1/2 flag, 1/2 option, like Counter, but for any value


class _Flag(BaseOption):
    nargs = Nargs(0)
    _use_opt_str: bool = False

    def __init_subclass__(cls, use_opt_str: bool = False, **kwargs):  # pylint: disable=W0222
        super().__init_subclass__(**kwargs)
        cls._use_opt_str = use_opt_str

    def __init__(self, *option_strs: str, **kwargs):
        bad = ', '.join(repr(key) for key in ('choices', 'metavar') if key in kwargs)
        if bad:
            art, s = ('', 's') if ',' in bad else ('an ', '')
            raise TypeError(f'{self.__class__.__name__}.__init__() got {art}unexpected keyword argument{s}: {bad}')
        super().__init__(*option_strs, **kwargs)

    def _init_value_factory(self):  # pylint: disable=W0221
        if self.action == 'store_const':
            return self.default
        else:
            return []

    def take_action(self, value: Optional[str], short_combo: bool = False, opt_str: str = None):
        # log.debug(f'{self!r}.take_action({value!r})')
        ctx.record_action(self)
        action_method = getattr(self, self.action)
        if value is None:
            return action_method(opt_str) if self._use_opt_str else action_method()

        raise ParamUsageError(self, f'received value={value!r} but no values are accepted for action={self.action!r}')

    def would_accept(self, value: Optional[str], short_combo: bool = False) -> bool:  # noqa
        return value is None

    def result_value(self) -> Any:
        return ctx.get_parsed_value(self)

    result = result_value


class Flag(_Flag, accepts_values=False, accepts_none=True):
    """
    A (typically boolean) option that does not accept any values.

    :param option_strs: The long and/or short option prefixes for this option.  If no long prefixes are specified,
      then one will automatically be added based on the name assigned to this parameter.
    :param action: The action to take on individual parsed values.  Actions must be defined as methods in classes
      that extend Parameter, and must be registered via :class:`.parameter_action`.  Defaults to ``store_const``, but
      accepts ``append_const`` to build a list of the specified constant.
    :param default: The default value for this parameter if it is not specified.  Defaults to ``False`` when
      ``const=True`` (the default), and to ``True`` when ``const=False``.  Defaults to ``None`` for any other
      constant.
    :param const: The constant value to store/append when this parameter is specified.  Defaults to ``True``.
    :param kwargs: Additional keyword arguments to pass to :class:`.BaseOption`.
    """

    __default_const_map = {True: False, False: True, _NotSet: True}

    def __init__(
        self, *option_strs: str, action: str = 'store_const', default: Any = _NotSet, const: Any = _NotSet, **kwargs
    ):
        if const is _NotSet:
            try:
                const = self.__default_const_map[default]
            except KeyError as e:
                cls = self.__class__.__name__
                raise ParameterDefinitionError(f"Missing parameter='const' for {cls} with default={default!r}") from e
        if default is _NotSet:
            default = self.__default_const_map.get(const)  # will be True, False, or None
        super().__init__(*option_strs, action=action, default=default, **kwargs)
        self.const = const

    @parameter_action
    def store_const(self):
        ctx.set_parsed_value(self, self.const)

    @parameter_action
    def append_const(self):
        ctx.get_parsed_value(self).append(self.const)


class TriFlag(_Flag, accepts_values=False, accepts_none=True, use_opt_str=True):
    """
    A trinary / ternary Flag.  While :class:`.Flag` only supports 1 constant when provided, with 1 default if not
    provided, this class accepts a pair of constants for the primary and alternate values to store, along with a
    separate default.

    :param option_strs: The primary long and/or short option prefixes for this option.  If no long prefixes are
      specified, then one will automatically be added based on the name assigned to this parameter.
    :param consts: A 2-tuple containing the ``(primary, alternate)`` values to store.  Defaults to ``(True, False)``.
    :param alt_prefix: The prefix to add to the assigned name for the alternate long form.  Ignored if ``alt_long`` is
      specified.  Defaults to ``no`` if ``alt_long`` is not specified.
    :param alt_long: The alternate long form to use.
    :param alt_short: The alternate short form to use.
    :param action: The action to take on individual parsed values.  Only ``store_const`` (the default) is supported.
    :param default: The default value to use if neither the primary or alternate options are provided.  Defaults
      to None.
    :param name_mode: Override the configured :ref:`configuration:Parsing Options:option_name_mode` for this TriFlag.
    :param kwargs: Additional keyword arguments to pass to :class:`.BaseOption`.
    """

    _opt_str_cls = TriFlagOptionStrings
    option_strs: TriFlagOptionStrings

    def __init__(
        self,
        *option_strs: str,
        consts: Tuple[Any, Any] = (True, False),
        alt_prefix: str = None,
        alt_long: str = None,
        alt_short: str = None,
        action: str = 'store_const',
        default: Any = None,
        **kwargs,
    ):
        if alt_short and '-' in alt_short[1:]:
            raise ParameterDefinitionError(f"Bad alt_short option - may not contain '-': {alt_short}")
        elif alt_prefix and ('=' in alt_prefix or alt_prefix.startswith('-')):
            raise ParameterDefinitionError(f"Bad alt_prefix - may not contain '=' or start with '-': {alt_prefix}")
        elif not alt_prefix and not alt_long:
            alt_prefix = 'no'

        try:
            _pos, _neg = consts
        except (ValueError, TypeError) as e:
            msg = f'Invalid consts={consts!r} - expected a 2-tuple of (positive, negative) constants to store'
            raise ParameterDefinitionError(msg) from e

        alt_opt_strs = tuple(filter(None, (alt_short, alt_long)))
        super().__init__(*option_strs, *alt_opt_strs, action=action, default=default, **kwargs)
        self.consts = consts
        self.option_strs.add_alts(alt_prefix, alt_long, alt_short)

    def __set_name__(self, command: CommandType, name: str):
        super().__set_name__(command, name)
        self.option_strs.update_alts(self, command, name)

    @parameter_action
    def store_const(self, opt_str: str):
        if opt_str in self.option_strs.alt_allowed:
            const = self.consts[1]
        else:
            const = self.consts[0]
        ctx.set_parsed_value(self, const)


class ActionFlag(Flag, repr_attrs=('order', 'before_main')):
    """
    A :class:`.Flag` that triggers the execution of a function / method / other callable when specified.

    :param option_strs: The long and/or short option prefixes for this option.  If no long prefixes are specified,
      then one will automatically be added based on the name assigned to this parameter.
    :param order: The priority / order in which this ActionFlag should be executed, relative to other ActionFlags, if
      others would also be executed.  Two ActionFlags in a given :class:`.Command` may not have the same combination
      of ``before_main`` and ``order`` values.  ActionFlags with lower ``order`` values are executed before those with
      higher values.  The ``--help`` action is implemented as an ActionFlag with ``order=float('-inf')``.
    :param func: The function to execute when this parameter is specified.
    :param before_main: Whether this ActionFlag should be executed before the :meth:`.Command.main` method or
      after it.
    :param always_available: Whether this ActionFlag should always be available to be called, even if parsing
      failed.  Only allowed when ``before_main=True``.  The intended use case is for actions like ``--help`` text.
    :param kwargs: Additional keyword arguments to pass to :class:`.Flag`.
    """

    def __init__(
        self,
        *option_strs: str,
        order: Union[int, float] = 1,
        func: Callable = None,
        before_main: Bool = True,  # noqa  # pylint: disable=W0621
        always_available: Bool = False,
        **kwargs,
    ):
        expected = {'action': 'store_const', 'default': False, 'const': _NotSet}
        found = {k: kwargs.setdefault(k, v) for k, v in expected.items()}
        bad = {k: v for k, v in found.items() if expected[k] != v}
        if bad:
            raise ParameterDefinitionError(f'Unsupported kwargs for {self.__class__.__name__}: {bad}')
        elif always_available and not before_main:
            raise ParameterDefinitionError('always_available=True cannot be combined with before_main=False')
        super().__init__(*option_strs, **kwargs)
        self.func = func
        self.order = order
        self.before_main = before_main
        self.always_available = always_available

    @property
    def func(self):
        return self._func

    @func.setter
    def func(self, func: Optional[Callable]):
        self._func = func
        if func is not None:
            if self.help is None:
                try:
                    self.help = func.__doc__
                except AttributeError:
                    pass
            update_wrapper(self, func)

    def __hash__(self) -> int:
        attrs = (self.__class__, self.name, self.command, self.func, self.order, self.before_main)
        return reduce(xor, map(hash, attrs))

    def __eq__(self, other: ActionFlag) -> bool:
        if not isinstance(other, ActionFlag):
            return NotImplemented
        return all(getattr(self, a) == getattr(other, a) for a in ('name', 'func', 'command', 'order', 'before_main'))

    def __lt__(self, other: ActionFlag) -> bool:
        if not isinstance(other, ActionFlag):
            return NotImplemented
        return (not self.before_main, self.order, self.name) < (not other.before_main, other.order, other.name)

    def __call__(self, func: Callable) -> ActionFlag:
        """
        Allows use as a decorator on the method to be called.  A given method can only be decorated with one ActionFlag.

        If stacking :class:`.Action` and :class:`.ActionFlag` decorators, the Action decorator must be first (i.e., the
        ActionFlag decorator must be above the Action decorator).
        """
        if self.func is not None:
            raise CommandDefinitionError(f'Cannot re-assign the func to call for {self}')
        self.func = func
        return self

    def __get__(self, command: Optional[Command], owner: CommandType) -> Union[ActionFlag, Callable]:
        # Allow the method to be called, regardless of whether it was specified
        if command is None:
            return self
        return partial(self.func, command)  # imitates a bound method

    def result(self) -> Optional[Callable]:
        if self.result_value():
            if self.func:
                return self.func
            raise ParameterDefinitionError(f'No function was registered for {self}')
        return None


#: Alias for :class:`ActionFlag`
action_flag = ActionFlag  # pylint: disable=C0103


def before_main(*option_strs: str, order: Union[int, float] = 1, func: Callable = None, **kwargs) -> ActionFlag:
    """An ActionFlag that will be executed before :meth:`.Command.main`"""
    return ActionFlag(*option_strs, order=order, func=func, before_main=True, **kwargs)


def after_main(*option_strs: str, order: Union[int, float] = 1, func: Callable = None, **kwargs) -> ActionFlag:
    """An ActionFlag that will be executed after :meth:`.Command.main`"""
    return ActionFlag(*option_strs, order=order, func=func, before_main=False, **kwargs)


class Counter(BaseOption, accepts_values=True, accepts_none=True):
    """
    A :class:`.Flag`-like option that counts the number of times it was specified.  Supports an optional integer value
    to explicitly increase the stored value by that amount.

    :param option_strs: The long and/or short option prefixes for this option.  If no long prefixes are specified,
      then one will automatically be added based on the name assigned to this parameter.
    :param action: The action to take on individual parsed values.  Defaults to ``append``, and no other actions
      are supported (unless this class is extended).
    :param default: The default value for this parameter if it is not specified.  This value is also be used as the
      initial value that will be incremented when this parameter is specified.  Defaults to ``0``.
    :param const: The value by which the stored value should increase whenever this parameter is specified.
      Defaults to ``1``.  If a different ``const`` value is used, and if an explicit value is provided by a user,
      the user-provided value will be added verbatim - it will NOT be multiplied by ``const``.
    :param kwargs: Additional keyword arguments to pass to :class:`.BaseOption`.
    """

    type = int
    nargs = Nargs('?')

    def __init__(self, *option_strs: str, action: str = 'append', default: int = 0, const: int = 1, **kwargs):
        if 'choices' in kwargs:
            raise TypeError(f"{self.__class__.__name__}.__init__() got an unexpected keyword argument 'choices'")
        vals = {'const': const, 'default': default}
        bad_types = ', '.join(f'{k}={v!r}' for k, v in vals.items() if not isinstance(v, self.type))
        if bad_types:
            raise ParameterDefinitionError(f'Invalid type for parameters (expected int): {bad_types}')
        super().__init__(*option_strs, action=action, default=default, **kwargs)
        self.const = const

    def _init_value_factory(self):  # pylint: disable=W0221
        return self.default

    def prepare_value(self, value: Optional[str], short_combo: bool = False, pre_action: bool = False) -> int:
        if value is None:
            return self.const
        try:
            return self.type(value)
        except (ValueError, TypeError) as e:
            combinable = self.option_strs.combinable
            if short_combo and combinable and all(c in combinable for c in value):
                return len(value) + 1  # +1 for the -short that preceded this value
            raise BadArgument(self, f'bad counter value={value!r}') from e

    @parameter_action
    def append(self, value: Optional[int]):
        if value is None:
            value = self.const
        current = ctx.get_parsed_value(self)
        ctx.set_parsed_value(self, current + value)

    def validate(self, value: Any):
        if value is None or isinstance(value, self.type):
            return
        try:
            value = self.type(value)
        except (ValueError, TypeError) as e:
            raise BadArgument(self, f'invalid value={value!r} (expected an integer)') from e
        else:
            return

    def result_value(self) -> int:
        return ctx.get_parsed_value(self)

    result = result_value
