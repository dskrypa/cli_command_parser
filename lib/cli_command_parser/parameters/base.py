"""
Base classes and helpers for Parameters and Groups

:author: Doug Skrypa
"""
# pylint: disable=R0801

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from contextvars import ContextVar
from functools import partial, update_wrapper
from itertools import chain
from typing import TYPE_CHECKING, Any, Type, Generic, Optional, Callable, Collection, Union, List, FrozenSet

try:
    from functools import cached_property  # pylint: disable=C0412
except ImportError:
    from ..compat import cached_property

from ..config import CommandConfig, OptionNameMode
from ..context import Context, ctx, get_current_context, ParseState
from ..exceptions import ParameterDefinitionError, BadArgument, MissingArgument, InvalidChoice
from ..exceptions import ParamUsageError, NoActiveContext, UnsupportedAction
from ..inputs import InputType, normalize_input_type
from ..inputs.choices import _ChoicesBase, Choices, ChoiceMap as ChoiceMapInput
from ..inputs.exceptions import InputValidationError, InvalidChoiceError
from ..nargs import Nargs
from ..typing import Bool, T_co
from ..utils import _NotSet, get_descriptor_value_type
from .option_strings import OptionStrings

if TYPE_CHECKING:
    from types import MethodType
    from ..core import CommandType
    from ..commands import Command
    from ..formatting.params import ParamHelpFormatter
    from .groups import ParamGroup

__all__ = ['Parameter', 'BasePositional', 'BaseOption']

_group_stack = ContextVar('cli_command_parser.parameters.base.group_stack', default=[])


class parameter_action:  # pylint: disable=C0103
    """
    Decorator that is used to register :paramref:`Parameter.__init__.action` handler methods to store values that are
    provided for that type of :class:`Parameter`.  The name of the decorated method is used as the ``action`` name.

    :param method: The method that should be used to handle storing values
    """

    def __init__(self, method: MethodType):
        self.method = method
        update_wrapper(self, method)

    def __set_name__(self, parameter_cls: Type[Parameter], name: str):
        """
        Registers the decorated method in the Parameter subclass's _actions dict, then replaces the action decorator
        with the original method.

        Since `__set_name__` is called on descriptors before their containing class's parent's `__init_subclass__` is
        called, name action/method name conflicts are handled by imitating a name mangled dunder attribute that will be
        unique to each subclass.  The mangled name is replaced with the friendlier `_actions` in
        :meth:`Parameter.__init_subclass__`.
        """
        try:
            actions = getattr(parameter_cls, f'_{parameter_cls.__name__}__actions')
        except AttributeError:
            actions = set()
            setattr(parameter_cls, f'_{parameter_cls.__name__}__actions', actions)

        actions.add(name)

    def __call__(self, *args, **kwargs) -> int:
        result = self.method(*args, **kwargs)
        return 1 if result is None else result

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return partial(self.__call__, instance)


class ParamBase(ABC):
    """
    Base class for :class:`Parameter` and :class:`.ParamGroup`.

    :param name: The name to use for this parameter.  Defaults to the name assigned to this parameter.
    :param required: Whether this parameter is required or not.  If it is required, then an exception will be
      raised if the user did not provide a value for this parameter.  Defaults to ``False``.
    :param help: A brief description of this parameter that will appear in ``--help`` text.
    :param hide: If ``True``, this parameter will not be included in usage / help messages.  Defaults to ``False``.
    """

    __name: str = None              #: Always the name of the attr that points to this object
    _name: str = None               #: An explicitly provided name, or the name of the attr that points to this object
    group: ParamGroup = None        #: The group this object is a member of, if any
    command: CommandType = None     #: The :class:`.Command` this object is a member of
    required: Bool = False          #: Whether this param/group is required
    help: str = None                #: The description for this param/group that will appear in ``--help`` text
    hide: Bool = False              #: Whether this param/group should be hidden in ``--help`` text
    missing_hint: str = None        #: Hint to provide if this param/group is missing

    def __init__(self, name: str = None, required: Bool = False, help: str = None, hide: Bool = False):  # noqa
        self.required = required
        self.name = name
        self.help = help
        self.hide = hide
        group = get_active_param_group()
        if group:
            group.register(self)  # noqa  # This sets self.group = group

    @property
    def name(self) -> str:
        name = self._name
        if name is not None:
            return name
        return f'{self.__class__.__name__}#{id(self)}'

    @name.setter
    def name(self, value: Optional[str]):
        if value is not None:
            self._name = value

    def __set_name__(self, command: CommandType, name: str):
        self.command = command
        if self._name is None:
            self.name = name
        self.__name = name

    def __hash__(self) -> int:
        return hash(self.__class__) ^ hash(self.__name) ^ hash(self.name) ^ hash(self.command)

    def _ctx(self, command: Command = None) -> Context:
        try:
            return get_current_context()
        except NoActiveContext:
            pass
        if command is None:
            command = self.command
        try:
            return command._Command__ctx
        except AttributeError:
            pass
        raise NoActiveContext('There is no active context')

    def _config(self, command: Command = None) -> CommandConfig:
        if command is None:
            command = self.command
        try:
            return self._ctx(command).config
        except NoActiveContext:
            return command.__class__.config(command)

    # region Usage / Help Text

    @cached_property
    def formatter(self) -> ParamHelpFormatter:
        from ..formatting.params import ParamHelpFormatter  # Here due to circular dependency

        try:
            formatter_factory = self._config().param_formatter or ParamHelpFormatter
        except AttributeError:  # self.command is None
            formatter_factory = ParamHelpFormatter

        return formatter_factory(self)  # noqa

    @property
    @abstractmethod
    def show_in_help(self) -> bool:
        raise NotImplementedError

    def format_usage(self, *args, **kwargs) -> str:
        """Convenience method for calling :meth:`.ParamHelpFormatter.format_usage`"""
        return self.formatter.format_usage(*args, **kwargs)

    def format_help(self, *args, **kwargs) -> str:
        """Convenience method for calling :meth:`.ParamHelpFormatter.format_help`"""
        return self.formatter.format_help(*args, **kwargs)

    # endregion


class Parameter(ParamBase, Generic[T_co], ABC):
    """
    Base class for all other parameters.  It is not meant to be used directly.

    Custom parameter classes should generally extend :class:`BasePositional` or :class:`BaseOption` instead of this,
    otherwise additional handling may be necessary in the parser.

    :param action: The action to take on individual parsed values.  Actions must be defined as methods in classes
      that extend Parameter, and must be registered via :class:`parameter_action`.
    :param name: The name to use for this parameter.  Defaults to the name assigned to this parameter.
    :param default: The default value for this parameter if it is not specified.  Defaults to ``None`` if this
      parameter is not required; not used if it is required.
    :param required: Whether this parameter is required or not.  If it is required, then an exception will be
      raised if the user did not provide a value for this parameter.  Defaults to ``False``.
    :param metavar: The name to use as a placeholder for values in usage / help messages.
    :param help: A brief description of this parameter that will appear in ``--help`` text.
    :param hide: If ``True``, this parameter will not be included in usage / help messages.  Defaults to ``False``.
    :param show_default: Override the :attr:`.CommandConfig.show_defaults` setting for this parameter to always or
      never include the default value in usage / help messages.  Default: follow the ``show_defaults`` setting.
    """

    # region Attributes & Initialization

    # Class attributes
    _actions: FrozenSet[str] = frozenset()          #: The actions supported by this Parameter
    _positional: bool = False                       #: Whether this Parameter is positional or not
    _repr_attrs: Optional[Collection[str]] = None   #: Attributes to include in ``repr()`` output
    accepts_none: bool = False                      #: Whether this Parameter can be provided without a value
    accepts_values: bool = True                     #: Whether this Parameter can be provided with at least 1 value
    # Instance attributes with class defaults
    metavar: str = None
    nargs: Nargs = Nargs(1)                         # Set in subclasses
    type: Optional[Callable[[str], T_co]] = None    # Only set here if not set by __init__ in Option/Positional
    show_default: bool = None

    def __init_subclass__(
        cls, accepts_values: bool = None, accepts_none: bool = None, repr_attrs: Collection[str] = None
    ):
        """
        :param accepts_values: Indicates whether a given subclass of Parameter accepts values, or not.  :class:`.Flag`
          is an example of a class that does not accept values.
        :param accepts_none: Indicates whether a given subclass of Parameter accepts being specified without a value,
          like :class:`.Flag` and :class:`.Counter`.
        :param repr_attrs: Additional attributes to include in the repr.
        """
        actions = set(cls._actions)  # Inherit actions from parent
        actions.update(getattr(cls, '_BasicActionMixin__actions', ()))  # Inherit from mixin, if present
        try:
            actions.update(getattr(cls, f'_{cls.__name__}__actions'))
        except AttributeError:
            pass
        else:
            delattr(cls, f'_{cls.__name__}__actions')
        cls._actions = frozenset(actions)
        if accepts_values is not None:
            cls.accepts_values = accepts_values
        if accepts_none is not None:
            cls.accepts_none = accepts_none
        if repr_attrs is not None:
            cls._repr_attrs = repr_attrs

    def __init__(  # pylint: disable=R0913
        self,
        action: str,
        name: str = None,
        default: Any = _NotSet,
        required: Bool = False,
        metavar: str = None,
        help: str = None,  # noqa
        hide: Bool = False,
        show_default: Bool = None,
    ):
        if action not in self._actions:
            raise ParameterDefinitionError(
                f'Invalid action={action!r} for {self.__class__.__name__} - valid actions: {sorted(self._actions)}'
            )
        if required and default is not _NotSet:
            raise ParameterDefinitionError(
                f'Invalid combination of required=True with default={default!r} for {self.__class__.__name__} -'
                ' required Parameters cannot have a default value'
            )
        super().__init__(name=name, required=required, help=help, hide=hide)
        self.action = action
        self.default = None if default is _NotSet and not required and self.nargs.max == 1 else default
        self.metavar = metavar
        if show_default is not None:
            self.show_default = show_default

    def _init_value_factory(self, state: ParseState):
        return _NotSet

    def __set_name__(self, command: CommandType, name: str):
        super().__set_name__(command, name)
        type_attr = self.type
        choices = isinstance(type_attr, (ChoiceMapInput, Choices)) and type_attr.type is None
        if not (choices or type_attr is None):
            return
        annotated_type = get_descriptor_value_type(command, name)
        if annotated_type is None:
            return
        elif choices:
            type_attr.type = annotated_type
        else:  # self.type must be None
            # Choices present earlier would have already been converted
            self.type = normalize_input_type(annotated_type, None)

    @property
    def has_choices(self) -> bool:
        type_attr = self.type
        return isinstance(type_attr, _ChoicesBase) and type_attr.choices

    # endregion

    def __repr__(self) -> str:
        attr_names = ('action', 'const', 'default', 'type', 'choices', 'required', 'hide', 'help')
        extra_attrs = self._repr_attrs
        if extra_attrs:
            attr_names = chain(attr_names, extra_attrs)

        attrs = ((a, getattr(self, a, None)) for a in attr_names)
        kwargs = ', '.join(f'{a}={v!r}' for a, v in attrs if v not in (None, _NotSet) and not (a == 'hide' and not v))
        return f'{self.__class__.__name__}({self.name!r}, {kwargs})'

    # region Argument Handling

    def __get__(self, command: Optional[Command], owner: CommandType):
        if command is None:
            return self

        with self._ctx(command):
            value = self.result()

        name = self._name
        if name is not None:
            command.__dict__[name] = value  # Skip __get__ on subsequent accesses
        return value

    def _nargs_max_reached(self) -> bool:
        try:
            return len(ctx.get_parsed_value(self)) >= self.nargs.max
        except TypeError:
            return False

    def take_action(  # pylint: disable=W0613
        self, value: Optional[str], short_combo: bool = False, opt_str: str = None
    ):
        action = self.action
        if action == 'append' and self._nargs_max_reached():
            val_count = len(ctx.get_parsed_value(self))
            raise ParamUsageError(
                self, f'cannot accept any additional args with nargs={self.nargs}: val_count={val_count!r}'
            )
        elif action == 'store':
            val = ctx.get_parsed_value(self)
            if val is not _NotSet:
                raise ParamUsageError(self, f'received value={value!r} but a stored value={val!r} already exists')

        ctx.record_action(self)
        action_method = getattr(self, action)
        return action_method(self.prepare_and_validate(value, short_combo))

    def would_accept(self, value: str, short_combo: bool = False) -> bool:
        action = self.action
        if action in {'store', 'store_all'} and ctx.get_parsed_value(self) is not _NotSet:
            return False
        elif action == 'append' and self._nargs_max_reached():
            return False
        try:
            normalized = self.prepare_value(value, short_combo, True)
        except BadArgument:
            return False
        return self.is_valid_arg(normalized)

    def prepare_and_validate(self, value: str, short_combo: bool = False) -> T_co:
        if value is not None:
            value = self.prepare_value(value, short_combo)
        self.validate(value)
        return value

    def prepare_value(  # pylint: disable=W0613
        self, value: str, short_combo: bool = False, pre_action: bool = False
    ) -> T_co:
        type_func = self.type
        if type_func is None or (pre_action and isinstance(type_func, InputType) and type_func.is_valid_type(value)):
            return value
        try:
            return type_func(value)
        except InvalidChoiceError as e:
            raise InvalidChoice(self, e.invalid, e.choices) from e
        except InputValidationError as e:
            raise BadArgument(self, str(e)) from e
        except (TypeError, ValueError) as e:
            raise BadArgument(self, f'bad value={value!r} for type={type_func!r}: {e}') from e
        except Exception as e:
            raise BadArgument(self, f'unable to cast value={value!r} to type={type_func!r}') from e

    def validate(self, value: Optional[T_co]):
        if isinstance(value, str) and value.startswith('-'):
            if len(value) > 1 and not _is_numeric(value):
                raise BadArgument(self, f'invalid value={value!r}')
        elif value is None:
            if not self.accepts_none:
                raise MissingArgument(self)
        elif not self.accepts_values:
            raise BadArgument(self, f'does not accept values, but value={value!r} was provided')

    def is_valid_arg(self, value: Any) -> bool:
        try:
            self.validate(value)
        except (InvalidChoice, BadArgument, MissingArgument):
            return False
        else:
            return True

    def _fix_default(self, value) -> Optional[T_co]:
        type_func = self.type
        if type_func is not None and isinstance(type_func, InputType):
            return type_func.fix_default(value)
        return value

    def _fix_default_collection(self, values) -> Optional[T_co]:
        type_func = self.type
        if type_func is None or not isinstance(type_func, InputType) or not isinstance(values, (list, tuple, set)):
            return values
        return values.__class__(map(type_func.fix_default, values))

    def result_value(self) -> Optional[T_co]:
        value = ctx.get_parsed_value(self)
        if value is _NotSet:
            if self.required:
                raise MissingArgument(self)
            else:
                return self._fix_default(self.default)

        if self.action == 'store':
            return value

        # action == 'append' or 'store_all'
        if not value:
            default = self.default
            if default is not _NotSet:
                if isinstance(default, Collection) and not isinstance(default, str):
                    value = self._fix_default_collection(default)
                else:
                    value.append(self._fix_default(default))

        nargs = self.nargs
        val_count = len(value)
        if val_count == 0 and 0 not in nargs:
            if self.required:
                raise MissingArgument(self)
        elif val_count not in nargs:
            raise BadArgument(self, f'expected nargs={nargs!r} values but found {val_count}')

        return value

    result = result_value

    def can_pop_counts(self) -> List[int]:  # noqa
        return []

    def pop_last(self, count: int = 1) -> List[str]:
        raise UnsupportedAction

    # endregion

    # region Usage / Help Text

    @property
    def show_in_help(self) -> bool:
        if self.hide:
            return False
        elif self.group is not None:
            return self.group.show_in_help
        return True

    # endregion


class BasicActionMixin:
    action: str
    nargs: Nargs

    def _init_value_factory(self, state: ParseState):
        if self.action == 'append':
            return []
        return super()._init_value_factory(state)  # noqa

    @parameter_action
    def store(self: Parameter, value: T_co):
        ctx.set_parsed_value(self, value)

    @parameter_action
    def append(self: Parameter, value: T_co):
        ctx.get_parsed_value(self).append(value)

    def _pre_pop_values(self: Parameter):
        if self.action != 'append' or not self.nargs.variable or self.type not in (None, str):
            return []

        return ctx.get_parsed_value(self)

    def can_pop_counts(self) -> List[int]:
        values = self._pre_pop_values()
        if not values:
            return []

        n_values = len(values)
        return [i for i in range(1, n_values) if self.nargs.satisfied(n_values - i)]

    def _reset(self: Union[Parameter, BasicActionMixin]) -> List[str]:
        if self.action != 'append' or self.type not in (None, str):
            raise UnsupportedAction

        values = ctx.get_parsed_value(self)
        if not values:
            return values

        ctx.set_parsed_value(self, self._init_value_factory(ctx.state))
        ctx._provided[self] = 0
        return values

    def pop_last(self: Union[Parameter, BasicActionMixin], count: int = 1) -> List[str]:
        values = self._pre_pop_values()
        if not values or count >= len(values) or not self.nargs.satisfied(len(values) - count):
            raise UnsupportedAction

        ctx.set_parsed_value(self, values[:-count])
        ctx.record_action(self, -count)
        return values[-count:]


class BasePositional(Parameter[T_co], ABC):
    """
    Base class for :class:`.Positional`, :class:`.SubCommand`, :class:`.Action`, and any other parameters that are
    provided positionally, without prefixes.  It is not meant to be used directly.

    All positional parameters are required by default.

    Custom positional parameter classes should extend this class to be treated the same as other positionals by the
    parser.

    :param action: The action to take on individual parsed values.  Actions must be defined as methods in classes
      that extend Parameter, and must be registered via :class:`parameter_action`.
    :param kwargs: Additional keyword arguments to pass to :class:`Parameter`.
    """

    _positional: bool = True
    _default_ok: bool = False

    def __init_subclass__(cls, default_ok: bool = None, **kwargs):  # pylint: disable=W0222
        """
        :param default_ok: Whether default values are supported for this Parameter type
        :param kwargs: Additional keyword arguments to pass to :meth:`.Parameter.__init_subclass__`.
        """
        super().__init_subclass__(**kwargs)
        if default_ok is not None:
            cls._default_ok = default_ok

    def __init__(self, action: str, *, required: Bool = True, default: Any = _NotSet, **kwargs):
        default_bad = not self._default_ok or 0 not in self.nargs
        if not required and default_bad:
            cls_name = self.__class__.__name__
            raise ParameterDefinitionError(
                f'All {cls_name} parameters must be required - invalid required={required!r}'
            )
        elif default_bad and default is not _NotSet:
            cls_name = self.__class__.__name__
            raise ParameterDefinitionError(f"The 'default' arg is not supported for {cls_name} parameters")
        super().__init__(action, default=default, required=required, **kwargs)


class BaseOption(Parameter[T_co], ABC):
    """
    Base class for :class:`.Option`, :class:`.Flag`, :class:`.Counter`, and any other keyword-like parameters that have
    ``--long`` and ``-short`` prefixes before values.

    Only the handling for processing long/short options and formatting usage of these parameters is provided in this
    class - it is not meant to be used directly.

    Custom option classes should extend this class to be treated the same as other options by the parser.

    :param option_strs: The long and/or short option prefixes for this option.  If no long prefixes are specified,
      then one will automatically be added based on the name assigned to this parameter.
    :param action: The action to take on individual parsed values.  Actions must be defined as methods in classes
      that extend Parameter, and must be registered via :class:`parameter_action`.
    :param name_mode: Override the configured :ref:`configuration:Parsing Options:option_name_mode` for this
      Option/Flag/Counter/etc.
    :param kwargs: Additional keyword arguments to pass to :class:`Parameter`.
    """

    _opt_str_cls = OptionStrings
    option_strs: OptionStrings

    def __init__(self, *option_strs: str, action: str, name_mode: Union[OptionNameMode, str] = None, **kwargs):
        _validate_opt_strs(option_strs)
        super().__init__(action, **kwargs)
        self.option_strs = self._opt_str_cls(option_strs, name_mode)

    def __set_name__(self, command: CommandType, name: str):
        super().__set_name__(command, name)
        self.option_strs.update(self, command, name)


def get_active_param_group() -> Optional[ParamGroup]:
    try:
        return _group_stack.get()[-1]
    except (AttributeError, IndexError):
        return None


def _validate_opt_strs(opt_strs: Collection[str]):
    bad = ', '.join(opt for opt in opt_strs if not 0 < opt.count('-', 0, 3) < 3 or opt.endswith('-') or '=' in opt)
    if bad:
        msg = f"Bad option(s) - they must start with '--' or '-', may not end with '-', and may not contain '=': {bad}"
        raise ParameterDefinitionError(msg)


def _is_numeric(text: str) -> Bool:
    try:
        num_match = _is_numeric._num_match
    except AttributeError:
        _is_numeric._num_match = num_match = re.compile(r'^-\d+$|^-\d*\.\d+?$').match
    return num_match(text)
