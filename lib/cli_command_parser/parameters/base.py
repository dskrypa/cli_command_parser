"""
Base classes and helpers for Parameters and Groups

:author: Doug Skrypa
"""

from __future__ import annotations

# import logging
from abc import ABC, abstractmethod
from functools import partial, update_wrapper, reduce
from itertools import chain
from operator import xor
from typing import TYPE_CHECKING, Any, Type, Optional, Callable, Collection, Union, List, Set, FrozenSet
from types import MethodType

try:
    from functools import cached_property  # pylint: disable=C0412
except ImportError:
    from ..compat import cached_property

from ..config import CommandConfig, OptionNameMode
from ..context import Context, ctx, get_current_context
from ..exceptions import ParameterDefinitionError, BadArgument, MissingArgument, InvalidChoice
from ..exceptions import ParamUsageError, NoActiveContext, UnsupportedAction
from ..inputs import InputType, normalize_input_type, Choices, ChoiceMap as ChoiceMapInput
from ..inputs.exceptions import InputValidationError, InvalidChoiceError
from ..nargs import Nargs
from ..utils import _NotSet, Bool, get_descriptor_value_type, is_numeric

if TYPE_CHECKING:
    from ..core import CommandType
    from ..commands import Command
    from ..formatting.params import ParamHelpFormatter

__all__ = ['Parameter', 'BasePositional', 'BaseOption']
# log = logging.getLogger(__name__)


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

    # fmt: off
    __name: str = None              #: Always the name of the attr that points to this object
    _name: str = None               #: An explicitly provided name, or the name of the attr that points to this object
    group: ParamGroup = None        #: The group this object is a member of, if any
    command: CommandType = None     #: The :class:`.Command` this object is a member of
    required: Bool = False          #: Whether this param/group is required
    help: str = None                #: The description for this param/group that will appear in ``--help`` text
    hide: Bool = False              #: Whether this param/group should be hidden in ``--help`` text
    missing_hint: str = None        #: Hint to provide if this param/group is missing
    # fmt: on

    def __init__(self, name: str = None, required: Bool = False, help: str = None, hide: Bool = False):  # noqa
        self.required = required
        self.name = name
        self.help = help
        self.hide = hide
        group = ParamGroup.active_group()
        if group is not None:
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
        return reduce(xor, map(hash, (self.__class__, self.__name, self.name, self.command)))

    def _ctx(self, command: Command = None) -> Context:
        try:
            return get_current_context()
        except NoActiveContext:
            pass
        command = command or self.command
        try:
            return command._Command__ctx
        except AttributeError:
            pass
        raise NoActiveContext('There is no active context')

    def _ctx_or_config(self, command: CommandType) -> Union[CommandConfig, Context]:
        try:
            return self._ctx(command)
        except NoActiveContext:
            return command.__class__.config(command)

    # region Usage / Help Text

    @cached_property
    def formatter(self) -> ParamHelpFormatter:
        from ..formatting.params import ParamHelpFormatter  # Here due to circular dependency

        try:
            with self._ctx() as context:
                formatter_factory = context.param_formatter or ParamHelpFormatter
        except NoActiveContext:
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


class Parameter(ParamBase, ABC):
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
    :param choices: A container that holds the specific values that users must pick from.  By default, any value is
      allowed.
    :param help: A brief description of this parameter that will appear in ``--help`` text.
    :param hide: If ``True``, this parameter will not be included in usage / help messages.  Defaults to ``False``.
    :param show_default: Override the :attr:`.CommandConfig.show_defaults` setting for this parameter to always or
      never include the default value in usage / help messages.  Default: follow the ``show_defaults`` setting.
    """

    # region Attributes & Initialization

    _actions: FrozenSet[str] = frozenset()
    _positional: bool = False
    _repr_attrs: Optional[Collection[str]] = None
    accepts_none: bool = False
    accepts_values: bool = True
    choices: Optional[Collection[Any]] = None
    metavar: str = None
    nargs: Nargs = Nargs(1)
    type: Optional[Callable[[str], Any]] = None
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
        choices: Collection[Any] = None,
        help: str = None,  # noqa
        hide: Bool = False,
        show_default: Bool = None,
    ):
        if action not in self._actions:
            raise ParameterDefinitionError(
                f'Invalid action={action!r} for {self.__class__.__name__} - valid actions: {sorted(self._actions)}'
            )
        if not choices and choices is not None:
            raise ParameterDefinitionError(f'Invalid choices={choices!r} - when specified, choices cannot be empty')
        if required and default is not _NotSet:
            raise ParameterDefinitionError(
                f'Invalid combination of required=True with default={default!r} for {self.__class__.__name__} -'
                ' required Parameters cannot have a default value'
            )
        super().__init__(name=name, required=required, help=help, hide=hide)
        self.action = action
        self.choices = choices
        self.default = None if default is _NotSet and not required and self.nargs.max == 1 else default
        self.metavar = metavar
        if show_default is not None:
            self.show_default = show_default

    @staticmethod
    def _init_value_factory():
        return _NotSet

    def __set_name__(self, command: CommandType, name: str):
        super().__set_name__(command, name)
        type_attr = self.type
        choices = isinstance(type_attr, (ChoiceMapInput, Choices)) and type_attr.type is None
        if choices or type_attr is None:
            annotated_type = get_descriptor_value_type(command, name)
            if annotated_type is not None:
                if choices:
                    type_attr.type = annotated_type
                else:  # self.type must be None
                    # Choices present earlier would have already been converted
                    self.type = normalize_input_type(annotated_type, None)

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
            return len(ctx.get_parsing_value(self)) >= self.nargs.max
        except TypeError:
            return False

    def take_action(self, value: Optional[str], short_combo: bool = False):
        # log.debug(f'{self!r}.take_action({value!r})')
        action = self.action
        if action == 'append' and self._nargs_max_reached():
            val_count = len(ctx.get_parsing_value(self))
            raise ParamUsageError(
                self, f'cannot accept any additional args with nargs={self.nargs}: val_count={val_count!r}'
            )
        elif action == 'store':
            val = ctx.get_parsing_value(self)
            if val is not _NotSet:
                raise ParamUsageError(self, f'received value={value!r} but a stored value={val!r} already exists')

        ctx.record_action(self)
        action_method = getattr(self, self.action)
        if action in {'store_const', 'append_const'}:
            if value is not None:
                raise ParamUsageError(
                    self, f'received value={value!r} but no values are accepted for action={action!r}'
                )
            return action_method()
        else:
            normalized = self.prepare_value(value, short_combo) if value is not None else value
            self.validate(normalized)
            return action_method(normalized)

    def would_accept(self, value: str, short_combo: bool = False) -> bool:
        action = self.action
        if action in {'store', 'store_all'} and ctx.get_parsing_value(self) is not _NotSet:
            return False
        elif action == 'append' and self._nargs_max_reached():
            return False
        try:
            normalized = self.prepare_value(value, short_combo, True)
        except BadArgument:
            return False
        return self.is_valid_arg(normalized)

    def prepare_value(  # pylint: disable=W0613
        self, value: str, short_combo: bool = False, pre_action: bool = False
    ) -> Any:
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

    def validate(self, value: Any):
        if isinstance(value, str) and value.startswith('-'):
            if len(value) > 1 and not is_numeric(value):
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

    def result_value(self) -> Any:
        value = ctx.get_parsing_value(self)
        if value is _NotSet:
            if self.required:
                raise MissingArgument(self)
            else:
                return self.default

        if self.action == 'store':
            return value

        # action == 'append' or 'store_all'
        if not value:
            default = self.default
            if default is not _NotSet:
                if isinstance(default, Collection) and not isinstance(default, str):
                    value = default
                else:
                    value.append(default)

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

    @parameter_action
    def store(self: Parameter, value: Any):
        ctx.set_parsing_value(self, value)

    @parameter_action
    def append(self: Parameter, value: Any):
        ctx.get_parsing_value(self).append(value)

    def _pre_pop_values(self: Parameter):
        if self.action != 'append' or not self.nargs.variable or self.type not in (None, str):
            return []

        return ctx.get_parsing_value(self)

    def can_pop_counts(self) -> List[int]:
        values = self._pre_pop_values()
        if not values:
            return []

        n_values = len(values)
        return [i for i in range(1, n_values) if self.nargs.satisfied(n_values - i)]

    def _reset(self: Union[Parameter, BasicActionMixin]) -> List[str]:
        if self.action != 'append' or self.type not in (None, str):
            raise UnsupportedAction

        values = ctx.get_parsing_value(self)
        if not values:
            return values

        ctx.set_parsing_value(self, self._init_value_factory())
        ctx._provided[self] = 0
        return values

    def pop_last(self: Union[Parameter, BasicActionMixin], count: int = 1) -> List[str]:
        values = self._pre_pop_values()
        if not values or count >= len(values) or not self.nargs.satisfied(len(values) - count):
            raise UnsupportedAction

        ctx.set_parsing_value(self, values[:-count])
        ctx.record_action(self, -count)
        return values[-count:]


class BasePositional(Parameter, ABC):
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

    def __init__(self, action: str, **kwargs):
        required = kwargs.setdefault('required', True)
        if not required:
            cls_name = self.__class__.__name__
            raise ParameterDefinitionError(
                f'All {cls_name} parameters must be required - invalid required={required!r}'
            )
        elif kwargs.setdefault('default', _NotSet) is not _NotSet:
            cls_name = self.__class__.__name__
            raise ParameterDefinitionError(f"The 'default' arg is not supported for {cls_name} parameters")
        super().__init__(action, **kwargs)


class BaseOption(Parameter, ABC):
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

    # fmt: off
    _long_opts: Set[str]                        # --long options
    _short_opts: Set[str]                       # -short options
    short_combinable: Set[str]                  # short options without the leading dash (for combined flags)
    name_mode: Optional[OptionNameMode] = None  # OptionNameMode override
    # fmt: on

    def __init__(self, *option_strs: str, action: str, name_mode: Union[OptionNameMode, str] = None, **kwargs):
        bad_opts = ', '.join(opt for opt in option_strs if not 0 < opt.count('-', 0, 3) < 3)
        if bad_opts:
            raise ParameterDefinitionError(f"Bad option(s) - must start with '--' or '-': {bad_opts}")
        bad_opts = ', '.join(opt for opt in option_strs if opt.endswith('-'))
        if bad_opts:
            raise ParameterDefinitionError(f"Bad option(s) - may not end with '-': {bad_opts}")
        bad_opts = ', '.join(opt for opt in option_strs if '=' in opt)
        if bad_opts:
            raise ParameterDefinitionError(f"Bad option(s) - may not contain '=': {bad_opts}")

        super().__init__(action, **kwargs)
        self._long_opts = {opt for opt in option_strs if opt.startswith('--')}
        self._short_opts = short_opts = {opt for opt in option_strs if 1 == opt.count('-', 0, 2)}
        self.short_combinable = {opt[1:] for opt in short_opts if len(opt) == 2}
        if name_mode is not None:
            self.name_mode = OptionNameMode(name_mode)
        bad_opts = ', '.join(opt for opt in short_opts if '-' in opt[1:])
        if bad_opts:
            raise ParameterDefinitionError(f"Bad short option(s) - may not contain '-': {bad_opts}")

    def __set_name__(self, command: CommandType, name: str):
        super().__set_name__(command, name)
        if not self._long_opts:
            mode = self.name_mode if self.name_mode is not None else self._ctx_or_config(command).option_name_mode
            if mode & OptionNameMode.DASH:
                self._long_opts.add('--{}'.format(name.replace('_', '-')))
            if mode & OptionNameMode.UNDERSCORE:
                self._long_opts.add(f'--{name}')
            try:
                del self.__dict__['long_opts']
            except KeyError:
                pass

    @cached_property
    def long_opts(self) -> List[str]:
        return sorted(self._long_opts, key=lambda opt: (-len(opt), opt))

    @cached_property
    def short_opts(self) -> List[str]:
        return sorted(self._short_opts, key=lambda opt: (-len(opt), opt))


# Down here due to circular dependency
from .groups import ParamGroup  # pylint: disable=C0413
