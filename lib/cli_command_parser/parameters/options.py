"""
Optional Parameters

:author: Doug Skrypa
"""

from __future__ import annotations

import logging
from abc import ABC
from functools import partial, update_wrapper
from typing import TYPE_CHECKING, Any, Callable, Literal, NoReturn, Optional, TypeVar, Union

from ..exceptions import BadArgument, CommandDefinitionError, ParameterDefinitionError, ParamUsageError, ParserExit
from ..inputs import normalize_input_type
from ..nargs import Nargs, NargsValue
from ..typing import T_co, TypeFunc
from ..utils import _NotSet, str_to_bool
from .actions import Append, AppendConst, Count, Store, StoreConst
from .base import AllowLeadingDashProperty, BaseOption
from .option_strings import TriFlagOptionStrings

if TYPE_CHECKING:
    from ..typing import Bool, ChoicesType, CommandCls, CommandMethod, CommandObj, InputTypeFunc, LeadingDash, OptStr

__all__ = [
    'Option',
    'Flag',
    'TriFlag',
    'ActionFlag',
    'Counter',
    'action_flag',
    'before_main',
    'after_main',
    'help_action',
]
log = logging.getLogger(__name__)

TD = TypeVar('TD')
TC = TypeVar('TC')
TA = TypeVar('TA')
ConstAct = Literal['store_const', 'append_const']


class Option(BaseOption[Union[T_co, TD]], actions=(Store, Append)):
    """
    A generic option that can be specified as ``--foo bar`` or by using other similar forms.

    :param option_strs: The long and/or short option prefixes for this option.  If no long prefixes are specified,
      then one will automatically be added based on the name assigned to this parameter.
    :param nargs: The number of values that are expected/required when this parameter is specified.  Defaults to ``+``
      when ``action='append'``, and to ``1`` otherwise. See :class:`.Nargs` for more info.
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
    :param choices: A container that holds the specific values that users must pick from.  By default, any value is
      allowed.
    :param allow_leading_dash: Whether string values may begin with a dash (``-``).  By default, if a value begins with
      a dash, it is only accepted if it appears to be a negative numeric value.  Use ``True`` / ``always`` /
      ``AllowLeadingDash.ALWAYS`` to allow any value that begins with a dash (as long as it is not an option string for
      an Option/Flag/etc).  To reject all values beginning with a dash, including numbers, use ``False`` / ``never`` /
      ``AllowLeadingDash.NEVER``.
    :param kwargs: Additional keyword arguments to pass to :class:`.BaseOption`.
    """

    default: TD
    allow_leading_dash = AllowLeadingDashProperty()

    def __init__(
        self,
        *option_strs: str,
        nargs: NargsValue = None,
        action: Literal['store', 'append'] = None,
        default: TD = _NotSet,
        required: Bool = False,
        type: InputTypeFunc = None,  # noqa
        choices: ChoicesType = None,
        allow_leading_dash: LeadingDash = None,
        **kwargs,
    ):
        if nargs_provided := nargs is not None:
            nargs = Nargs(nargs)
            if 0 in nargs:
                nargs = nargs._orig
                details = 'use Flag or Counter for Options that can be specified without a value'
                if isinstance(nargs, range) and nargs.start == 0 and nargs.step != nargs.stop:
                    suffix = f', {nargs.step}' if nargs.step != 1 else ''
                    details = f'try using range({nargs.step}, {nargs.stop}{suffix}) instead, or {details}'
                raise ParameterDefinitionError(f'Invalid {nargs=} - {details}')

        if not action:
            if nargs_provided:
                action = 'store' if nargs == 1 else 'append'
            else:
                action = 'store'
        elif nargs_provided and action == 'store' and nargs != 1:
            raise ParameterDefinitionError(f'Invalid {nargs=} for {action=}')

        super().__init__(*option_strs, action=action, default=default, required=required, **kwargs)
        if not nargs_provided:
            nargs = self.action.default_nargs

        self.nargs = nargs
        self.type = normalize_input_type(type, choices)
        self.allow_leading_dash = allow_leading_dash

    def _handle_bad_action(self, action: str) -> NoReturn:
        if action in ('store_const', 'append_const'):
            raise ParameterDefinitionError(f'Invalid {action=} for {self.__class__.__name__} - use Flag instead')
        super()._handle_bad_action(action)


class Flag(BaseOption[Union[TD, TC]], actions=(StoreConst, AppendConst)):
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
    :param type: A callable (function, class, etc.) that accepts a single string argument and returns a boolean value,
      which should be called on environment variable values, if any are configured for this Flag via
      :paramref:`.BaseOption.env_var`.  It should return a truthy value if any action should be taken (i.e., if the
      constant should be stored/appended), or a falsey value for no action to be taken.  The
      :func:`default function<.str_to_bool>` handles parsing ``1`` / ``true`` / ``yes`` and similar as ``True``,
      and ``0`` / ``false`` / ``no`` and similar as ``False``.  If :paramref:`use_env_value` is ``True``, then this
      function should return either the default or constant value instead.
    :param strict_env: When ``True`` (the default), if an :paramref:`.BaseOption.env_var` is used as the source of a
      value for this parameter and that value is invalid, then parsing will fail.  When ``False``, invalid values from
      environment variables will be ignored (and a warning message will be logged).
    :param use_env_value: If ``True``, when an :paramref:`.BaseOption.env_var` is used as the source of a value for
      this Flag, the parsed value will be stored as this Flag's value (it must match either the default or constant
      value).  If ``False`` (the default), then the parsed value will be used to determine whether this Flag's normal
      action should be taken as if it was specified via a CLI argument.
    :param kwargs: Additional keyword arguments to pass to :class:`.BaseOption`.
    """

    nargs = Nargs(0)
    type = staticmethod(str_to_bool)  # Without staticmethod, this would be interpreted as a normal method
    use_env_value: bool = False
    __default_const_map = {True: False, False: True, _NotSet: True}
    default: TD
    const: TC

    def __init__(
        self,
        *option_strs: str,
        action: ConstAct = 'store_const',
        default: TD = _NotSet,
        default_cb=_NotSet,
        const: TC = _NotSet,
        type: TypeFunc = None,  # noqa
        **kwargs,
    ):
        if const is _NotSet:
            try:
                const = self.__default_const_map[default]
            except KeyError as e:
                raise ParameterDefinitionError(
                    f"A 'const' value is required for {self.__class__.__name__} since {default=} is not True or False"
                ) from e
        if default_cb is not _NotSet:
            cls_name = self.__class__.__name__
            raise ParameterDefinitionError(f"The 'default_cb' arg is not supported for {cls_name} parameters")
        if default is _NotSet:
            default = self.__default_const_map.get(const, _NotSet)  # will be True or False
        if default is False:  # Avoid surprises for custom non-truthy values
            kwargs.setdefault('show_default', False)
        super().__init__(*option_strs, action=action, default=default, **kwargs)
        self.const = const
        if type is not None:
            self.type = type

    def register_default_cb(self, method):
        raise ParameterDefinitionError(f'{self.__class__.__name__}s do not support default callback methods')

    def get_env_const(self, value: str, env_var: str) -> tuple[Union[TC, TD], bool]:
        try:
            parsed = self.type(value)
        except Exception as e:
            raise ParamUsageError(self, f'unable to parse {value=} from {env_var=}: {e}') from e
        if self.use_env_value and parsed != self.const and parsed != self.default:
            raise BadArgument(self, f'invalid value={parsed!r} from {env_var=}')
        return parsed, self.use_env_value


class TriFlag(BaseOption[Union[TD, TC, TA]], ABC, actions=(StoreConst, AppendConst)):
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
    :param alt_help: The help text to display with the alternate option strings.
    :param action: The action to take on individual parsed values.  Only ``store_const`` (the default) is supported.
    :param default: The default value to use if neither the primary or alternate options are provided.  Defaults
      to None.
    :param name_mode: Override the configured :ref:`configuration:Parsing Options:option_name_mode` for this TriFlag.
    :param type: A callable (function, class, etc.) that accepts a single string argument and returns a boolean value,
      which should be called on environment variable values, if any are configured for this TriFlag via
      :paramref:`.BaseOption.env_var`.  It should return a truthy value if the primary constant should be stored, or a
      falsey value if the alternate constant should be stored.  The :func:`default function<.str_to_bool>` handles
      parsing ``1`` / ``true`` / ``yes`` and similar as ``True``, and ``0`` / ``false`` / ``no`` and similar
      as ``False``.  If :paramref:`use_env_value` is ``True``, then this function should return the primary or
      alternate constant or the default value instead.
    :param strict_env: When ``True`` (the default), if an :paramref:`.BaseOption.env_var` is used as the source of a
      value for this parameter and that value is invalid, then parsing will fail.  When ``False``, invalid values from
      environment variables will be ignored (and a warning message will be logged).
    :param use_env_value: If ``True``, when an :paramref:`.BaseOption.env_var` is used as the source of a value for
      this TriFlag, the parsed value will be stored as this TriFlag's value (it must match the primary or alternate
      constant, or the default value).  If ``False`` (the default), then the parsed value will be used to determine
      whether this TriFlag's normal action should be taken as if it was specified via a CLI argument.
    :param kwargs: Additional keyword arguments to pass to :class:`.BaseOption`.
    """

    nargs = Nargs(0)
    type = staticmethod(str_to_bool)  # Without staticmethod, this would be interpreted as a normal method
    use_env_value: bool = False
    _default_cb_ok = True
    _opt_str_cls = TriFlagOptionStrings
    option_strs: TriFlagOptionStrings
    alt_help: OptStr = None
    default: TD
    consts: tuple[TC, TA]

    def __init__(
        self,
        *option_strs: str,
        consts: tuple[TC, TA] = (True, False),
        alt_prefix: str = None,
        alt_long: str = None,
        alt_short: str = None,
        alt_help: str = None,
        action: ConstAct = 'store_const',
        default: TD = _NotSet,
        default_cb: Callable[[], TD] = None,
        type: TypeFunc = None,  # noqa
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
            msg = f'Invalid {consts=} - expected a 2-tuple of (positive, negative) constants to store'
            raise ParameterDefinitionError(msg) from e

        if default is _NotSet and default_cb is None:
            if not kwargs.get('required', False):
                default = None
        else:
            self._default_cb_ok = False
        if default in consts:
            raise ParameterDefinitionError(
                f'Invalid {default=} with {consts=} - the default must not match either value'
            )

        alt_opt_strs = (opt for opt in (alt_short, alt_long) if opt)
        super().__init__(*option_strs, *alt_opt_strs, action=action, default=default, default_cb=default_cb, **kwargs)
        self.consts = consts
        self.option_strs.add_alts(alt_prefix, alt_long, alt_short)
        if alt_help:
            self.alt_help = alt_help
        if type is not None:
            self.type = type

    def __set_name__(self, command: CommandCls, name: str):
        super().__set_name__(command, name)
        self.option_strs.update_alts(name)

    def register_default_cb(self, method: CommandMethod) -> CommandMethod:
        if self._default_cb_ok and self.default is not _NotSet:
            self.default = _NotSet  # The default was set by __init__ - remove it so the method can be registered
        return super().register_default_cb(method)

    def get_const(self, opt_str: OptStr = None) -> Union[TC, TA]:
        if opt_str in self.option_strs.alt_allowed:
            return self.consts[1]
        else:
            return self.consts[0]

    def get_env_const(self, value: str, env_var: str) -> tuple[Union[TC, TA, TD], bool]:
        try:
            parsed = self.type(value)
        except Exception as e:
            raise ParamUsageError(self, f'unable to parse {value=} from {env_var=}: {e}') from e
        if self.use_env_value:
            if parsed not in self.consts and parsed != self.default:
                raise BadArgument(self, f'invalid value={parsed!r} from {env_var=}')
            return parsed, True
        else:
            const = self.consts[0] if parsed else self.consts[1]
            return const, True


# region Action Flag


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
        if bad := {k: fv for k, ev in expected.items() if (fv := kwargs.setdefault(k, ev)) != ev}:
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
        result = hash(self.__class__)
        for attr in (self.name, self.command, self.func, self.order, self.before_main):
            result ^= hash(attr)
        return result

    def __eq__(self, other: ActionFlag) -> bool:
        if not isinstance(other, ActionFlag):
            return NotImplemented
        return all(getattr(self, a) == getattr(other, a) for a in ('name', 'func', 'command', 'order', 'before_main'))

    def __lt__(self, other: ActionFlag) -> bool:
        if not isinstance(other, ActionFlag):
            return NotImplemented
        # noinspection PyTypeChecker
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

    def __get__(self, command: Optional[CommandObj], owner: CommandCls) -> Union[ActionFlag, Callable]:
        # Allow the method to be called, regardless of whether it was specified
        if command is None:
            return self
        # Note: If func is None, then CommandParameters._process_action_flags raises ParameterDefinitionError
        return partial(self.func, command)  # imitates a bound method


#: Alias for :class:`ActionFlag`
action_flag = ActionFlag  # pylint: disable=C0103


def before_main(*option_strs: str, order: Union[int, float] = 1, func: Callable = None, **kwargs) -> ActionFlag:
    """An ActionFlag that will be executed before :meth:`.Command.main`"""
    return ActionFlag(*option_strs, order=order, func=func, before_main=True, **kwargs)


def after_main(*option_strs: str, order: Union[int, float] = 1, func: Callable = None, **kwargs) -> ActionFlag:
    """An ActionFlag that will be executed after :meth:`.Command.main`"""
    return ActionFlag(*option_strs, order=order, func=func, before_main=False, **kwargs)


@action_flag(
    '--help', '-h', order=float('-inf'), name='help', always_available=True, help='Show this help message and exit'
)
def help_action(self):
    """The ``--help`` / ``-h`` action.  Prints help text, then exits."""
    cls = self.__class__
    print(cls.__class__.params(cls).formatter.format_help())
    raise ParserExit


# endregion


class Counter(BaseOption[int], actions=(Count,)):
    """
    A :class:`.Flag`-like option that counts the number of times it was specified.  Supports an optional integer value
    to explicitly increase the stored value by that amount.

    :param option_strs: The long and/or short option prefixes for this option.  If no long prefixes are specified,
      then one will automatically be added based on the name assigned to this parameter.
    :param action: The action to take on individual parsed values.  Defaults to ``append``, and no other actions
      are supported (unless this class is extended).
    :param init: The initial value that will be incremented when this parameter is specified.  Defaults to ``0``.
    :param default: The default value for this parameter if it is not specified.  Defaults to ``0`` unless this
      Parameter is required.
    :param const: The value by which the stored value should increase whenever this parameter is specified.
      Defaults to ``1``.  If a different ``const`` value is used, and if an explicit value is provided by a user,
      the user-provided value will be added verbatim - it will NOT be multiplied by ``const``.
    :param kwargs: Additional keyword arguments to pass to :class:`.BaseOption`.
    """

    type = int
    nargs = Nargs('?')
    init: int
    default: int
    const: int

    def __init__(
        self,
        *option_strs: str,
        action: str = 'count',
        init: int = 0,
        const: int = 1,
        default: int = _NotSet,
        default_cb: Callable[[], int] = None,
        required: bool = False,
        **kwargs,
    ):
        type_check_vals = {'const': const, 'init': init}
        if default is not _NotSet:
            type_check_vals['default'] = default
        elif not required and default_cb is None:
            default_cb = _counter_default  # This makes it easier to allow a method to override it
        if bad_types := ', '.join(f'{k}={v!r}' for k, v in type_check_vals.items() if not isinstance(v, self.type)):
            raise ParameterDefinitionError(f'Invalid type for parameters (expected int): {bad_types}')
        super().__init__(
            *option_strs, action=action, default=default, default_cb=default_cb, required=required, **kwargs
        )
        self.init = init
        self.const = const

    def register_default_cb(self, method: CommandMethod) -> CommandMethod:
        if self.default_cb and self.default_cb.func is _counter_default:
            self.default_cb = None
        return super().register_default_cb(method)

    def prepare_value(self, value: Optional[str], short_combo: bool = False, pre_action: bool = False) -> int:
        try:
            return self.type(value)
        except (ValueError, TypeError) as e:
            combinable = self.option_strs.combinable
            if short_combo and combinable and all(c in combinable for c in value):
                return len(value) + 1  # +1 for the -short that preceded this value
            raise BadArgument(self, f'bad counter {value=}') from e

    def validate(self, value: Any, joined: Bool = False):
        if value is None or isinstance(value, self.type):
            return
        try:
            value = self.type(value)
        except (ValueError, TypeError) as e:
            raise BadArgument(self, f'invalid {value=} (expected an integer)') from e
        else:
            return


def _counter_default():
    return 0
