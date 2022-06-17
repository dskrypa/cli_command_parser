"""
Optional Parameters

:author: Doug Skrypa
"""

from __future__ import annotations

from functools import partial, update_wrapper, reduce
from operator import xor
from typing import TYPE_CHECKING, Any, Optional, Callable, Union

from ..context import ctx
from ..exceptions import ParameterDefinitionError, BadArgument, CommandDefinitionError
from ..inputs import InputTypeFunc, normalize_input_type
from ..nargs import Nargs, NargsValue
from ..utils import _NotSet, Bool
from .base import BasicActionMixin, BaseOption, parameter_action

if TYPE_CHECKING:
    from ..core import CommandType
    from ..commands import Command

__all__ = ['Option', 'Flag', 'ActionFlag', 'Counter', 'action_flag', 'before_main', 'after_main']


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
        # TODO: nargs=? + required/not behavior?
        super().__init__(*option_strs, action=action, default=default, required=required, **kwargs)
        self.type = normalize_input_type(type, self.choices)
        if action == 'append':
            self._init_value_factory = list


class Flag(BaseOption, accepts_values=False, accepts_none=True):
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
    nargs = Nargs(0)

    def __init__(
        self, *option_strs: str, action: str = 'store_const', default: Any = _NotSet, const: Any = _NotSet, **kwargs
    ):
        if 'choices' in kwargs:
            raise TypeError(f"{self.__class__.__name__}.__init__() got an unexpected keyword argument 'choices'")
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

    def _init_value_factory(self):  # pylint: disable=W0221
        if self.action == 'store_const':
            return self.default
        else:
            return []

    @parameter_action
    def store_const(self):
        ctx.set_parsing_value(self, self.const)

    @parameter_action
    def append_const(self):
        ctx.get_parsing_value(self).append(self.const)

    def would_accept(self, value: Optional[str], short_combo: bool = False) -> bool:
        return value is None

    def result_value(self) -> Any:
        return ctx.get_parsing_value(self)

    result = result_value


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
            combinable = self.short_combinable
            if short_combo and combinable and all(c in combinable for c in value):
                return len(value) + 1  # +1 for the -short that preceded this value
            raise BadArgument(self, f'bad counter value={value!r}') from e

    @parameter_action
    def append(self, value: Optional[int]):
        if value is None:
            value = self.const
        current = ctx.get_parsing_value(self)
        ctx.set_parsing_value(self, current + value)

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
        return ctx.get_parsing_value(self)

    result = result_value
