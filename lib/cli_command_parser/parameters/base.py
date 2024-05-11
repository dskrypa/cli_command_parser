"""
Base classes and helpers for Parameters and Groups

:author: Doug Skrypa
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from contextvars import ContextVar
from functools import cached_property
from itertools import chain
from typing import TYPE_CHECKING, Any, Callable, Collection, Generic, Iterator, NoReturn, Type, TypeVar, Union, overload

from ..annotations import get_descriptor_value_type
from ..config import DEFAULT_CONFIG, AllowLeadingDash, CommandConfig, OptionNameMode
from ..context import Context, ctx, get_current_context
from ..exceptions import BadArgument, InvalidChoice, MissingArgument, ParameterDefinitionError
from ..inputs import InputType, normalize_input_type
from ..inputs.choices import _ChoicesBase
from ..inputs.exceptions import InputValidationError, InvalidChoiceError
from ..nargs import REMAINDER, Nargs
from ..typing import CommandMethod, DefaultFunc, T_co
from ..utils import _NotSet
from .option_strings import OptionStrings

if TYPE_CHECKING:
    from ..formatting.params import ParamHelpFormatter
    from ..typing import Bool, CommandAny, CommandCls, CommandObj, LeadingDash, OptStr, OptStrs, Param, Strings
    from .actions import ParamAction
    from .groups import ParamGroup

__all__ = ['Parameter', 'BasePositional', 'BaseOption']

_group_stack = ContextVar('cli_command_parser.parameters.base.group_stack')
_is_numeric = re.compile(r'^-\d+$|^-\d*\.\d+?$').match
TD = TypeVar('TD')


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
    # Class Attributes
    missing_hint: str = None        #: Hint to provide if this param/group is missing
    # Instance Attributes
    _attr_name: str = None          #: Always the name of the attr that points to this object
    _name: str = None               #: An explicitly provided name, or the name of the attr that points to this object
    group: ParamGroup = None        #: The group this object is a member of, if any
    command: CommandCls = None      #: The :class:`.Command` this object is a member of
    required: Bool                  #: Whether this param/group is required
    help: str                       #: The description for this param/group that will appear in ``--help`` text
    hide: Bool                      #: Whether this param/group should be hidden in ``--help`` text
    # fmt: on

    def __init__(self, name: str = None, required: Bool = False, help: str = None, hide: Bool = False):  # noqa
        self.__doc__ = help  # Prevent this class's docstring from showing up for params in generated documentation
        self.required = required
        self.help = help
        self.hide = hide
        # TODO: Make the --help flag a counter and allow some `hide=True` params to be shown with `-hh` or similar?
        self.name = name
        if param_groups := _group_stack.get(None):  # If truthy, there's at least 1 active ParamGroup
            param_groups[-1].register(self)  # This sets self.group = group

    # region Name

    @property
    def name(self) -> str:
        if self._name is not None:
            return self._name
        return self._default_name()

    @name.setter
    def name(self, value: Union[str, None]):
        if value is not None:
            self._name = value

    def _default_name(self) -> str:
        return f'{self.__class__.__name__}#{id(self)}'

    def __set_name__(self, command: CommandCls, name: str):
        self.command = command
        if self._name is None:
            self._name = name
        self._attr_name = name

    # endregion

    def __hash__(self) -> int:
        return hash(self.__class__) ^ hash(self._attr_name) ^ hash(self._name) ^ hash(self.command)

    def _ctx(self, command: CommandAny = None) -> Union[Context, None]:
        if context := get_current_context(True):
            return context
        if command is None:
            command = self.command
        try:
            return command._Command__ctx
        except AttributeError:
            return None

    def _config(self, command: CommandAny = None) -> CommandConfig:
        if context := self._ctx(command):
            return context.config
        if command is None:
            command = self.command
        return command.__class__.config(command, DEFAULT_CONFIG)

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
    :param required: Whether this parameter is required or not.  If it is required, then an exception will be
      raised if the user did not provide a value for this parameter.  Defaults to ``False``.
    :param metavar: The name to use as a placeholder for values in usage / help messages.
    :param help: A brief description of this parameter that will appear in ``--help`` text.
    :param default: The default value for this parameter if it is not specified.  Defaults to ``None`` if this
      parameter is not required; not used if it is required.
    :param default_cb: A default callback function (or other callable) may be provided instead of a static default
      value (they cannot both be provided).  If ``cb_with_cmd`` is False (the default), then it must be callable with
      no arguments, otherwise it must accept a single positional argument (the :class:`.Command` that contains this
      Parameter).  Similar to when the ``default`` value would be used, it will only be called when no argument was
      provided.  It is also possible to :ref:`register a method in a Command to be the default callback
      <advanced:Dynamic Parameter Defaults>`.
    :param cb_with_cmd: Whether the provided ``default_cb`` should be called with the :class:`.Command` that contains
      this Parameter.  Ignored if ``default_cb`` is not provided.
    :param show_default: Override the :attr:`.CommandConfig.show_defaults` setting for this parameter to always or
      never include the default value in usage / help messages.  Default: follow the ``show_defaults`` setting.
    :param hide: If ``True``, this parameter will not be included in usage / help messages.  Defaults to ``False``.
    """

    # region Attributes & Initialization

    # fmt: off
    # Class attributes
    _action_map: dict[str, Type[ParamAction]] = {}
    _repr_attrs: Union[Strings, None] = None                            #: Attributes to include in ``repr()`` output
    # Instance attributes with class defaults
    metavar: str = None
    nargs: Nargs                                                        # Expected to be set in subclasses
    type: Union[Callable[[str], T_co], None] = None                     # Expected to be set in subclasses
    allow_leading_dash: AllowLeadingDash = AllowLeadingDash.NUMERIC     # Set in some subclasses
    default = _NotSet
    default_cb: DefaultCallback | None = None
    show_default: Bool = None
    strict_default: Bool = False
    # fmt: on

    def __init_subclass__(cls, repr_attrs: Strings = None, actions: Collection[Type[ParamAction]] = None, **kwargs):
        """
        :param repr_attrs: Additional attributes to include in the repr.
        :param actions: Collection of ParamAction classes that this type of Parameter supports
        """
        super().__init_subclass__(**kwargs)
        if actions:
            # Extend the parent class's actions without modifying the parent's supported actions
            cls._action_map = action_map = cls._action_map.copy()
            action_map.update((action.name, action) for action in actions)
        if repr_attrs:
            cls._repr_attrs = repr_attrs

    def __init__(  # pylint: disable=R0913
        self,
        action: str,
        *,
        help: str = None,  # noqa
        hide: Bool = False,
        metavar: str = None,
        name: str = None,
        required: Bool = False,
        default: Any = _NotSet,
        default_cb: DefaultFunc = None,
        cb_with_cmd: Bool = False,
        show_default: Bool = None,
        strict_default: Bool = False,
    ):
        if not (param_action := self._action_map.get(action)):
            self._handle_bad_action(action)
        if required and default is not _NotSet:
            # TODO: For required mutually dependent groups, or a required group with all params having a default,
            #  is another check needed, or does this check make sense, or should this check be removed?
            raise ParameterDefinitionError(
                f'Invalid combination of required=True with {default=} for {self.__class__.__name__} -'
                ' required Parameters cannot have a default value'
            )
        super().__init__(name=name, required=required, help=help, hide=hide)
        self.action = param_action(self)
        self.metavar = metavar
        if default is not _NotSet:
            if default_cb is not None:
                raise ParameterDefinitionError(
                    f'{self.__class__.__name__}s can only have a {default=} xor {default_cb=}, not both'
                )
            self.default = default
        elif default_cb is not None:
            self.default_cb = DefaultCallback(default_cb, cb_with_cmd)
        self.strict_default = strict_default
        if show_default is not None:
            self.show_default = show_default

    def _handle_bad_action(self, action: str) -> NoReturn:
        """
        Called when an action not supported by this type of Parameter was provided.  May be overwritten in subclasses
        to provide hints about more appropriate options.
        """
        raise ParameterDefinitionError(
            f'Invalid {action=} for {self.__class__.__name__} - valid actions: {sorted(self._action_map)}'
        )

    def __set_name__(self, command: CommandCls, name: str):
        super().__set_name__(command, name)
        # If self.type is None, a type may still be inferred from an annotation, which happens in this method.
        if untyped_choices := self.type is not None:
            if not isinstance(self.type, _ChoicesBase) or self.type.type is not None:
                return  # An explicit type was provided to either stand alone or be used for Choices values
            # self.type is therefore a Choices object with no explicit type provided, so from here on, the var
            # name `untyped_choices` is accurate.  The type for its values may still be inferred from an annotation.
        elif self.nargs.max is REMAINDER or not self._config(command).allow_annotation_type:
            return

        if (annotated_type := get_descriptor_value_type(command, name)) is None:
            return
        elif untyped_choices:
            self.type.type = annotated_type
        else:  # self.type must be None
            # Choices present earlier would have already been converted
            self.type = normalize_input_type(annotated_type, None)

    @property
    def has_choices(self) -> bool:
        if self.type:
            return isinstance(self.type, _ChoicesBase) and self.type.choices
        return False

    def register_default_cb(self, method: CommandMethod) -> CommandMethod:
        """
        Intended to be used as a decorator to register a method in a Command to be used as the default callback for
        this Parameter.  The method will only be called during parsing if no value was explicitly provided for this
        Parameter.  The decorated method is returned unchanged, so it can still be called directly if necessary.

        :param method: A method that does not accept any arguments (except ``self``), and returns the value that should
          be used for this Parameter.
        :return: The method, unchanged.
        """
        if self.default is not _NotSet:
            problem = f'default={self.default!r}'
        elif self.default_cb:
            problem = f'default_cb={self.default_cb!r}'
        else:
            problem = None

        if problem:
            raise ParameterDefinitionError(
                f'Cannot register a default callback method for {self} because it already has {problem}'
            )
        self.default_cb = DefaultCallback(method, True)
        return method

    # endregion

    def __repr__(self) -> str:
        names = ('action', 'const', 'default', 'default_cb', 'type', 'choices', 'required', 'hide', 'help')
        if self._repr_attrs:
            names = chain(names, self._repr_attrs)

        skip = (None, _NotSet)
        attrs = (
            (a, str(v) if a == 'action' else v)
            for a in names
            if (v := getattr(self, a, None)) not in skip and not (a == 'hide' and not v)
        )
        kwargs = ', '.join(f'{a}={v!r}' for a, v in attrs)
        return f'{self.__class__.__name__}({self.name!r}, {kwargs})'

    # region Parsing / Argument Handling

    def get_const(self, opt_str: OptStr = None):
        return _NotSet

    def get_env_const(self, value: str, env_var: str) -> tuple[T_co, bool]:
        return _NotSet, False

    def prepare_value(self, value: str, short_combo: Bool = False, pre_action: Bool = False) -> T_co:
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
            raise BadArgument(self, f'bad {value=} for type={type_func!r}: {e}') from e
        except Exception as e:
            raise BadArgument(self, f'unable to cast {value=} to type={type_func!r}') from e

    def validate(self, value: Union[T_co, None], joined: Bool = False):
        if not isinstance(value, str) or not value or not value[0] == '-':
            return
        elif self.allow_leading_dash == AllowLeadingDash.NUMERIC:
            if not joined and len(value) > 1 and not _is_numeric(value):
                raise BadArgument(self, f'invalid {value=}')
        elif self.allow_leading_dash == AllowLeadingDash.NEVER:
            raise BadArgument(self, f'invalid {value=}')

    def is_valid_arg(self, value: Any) -> bool:
        try:
            self.validate(value)
        except (InvalidChoice, BadArgument, MissingArgument):
            return False
        else:
            return True

    # endregion

    # region Parse Results / Argument Value Handling

    @overload
    def __get__(self: Param, command: None, owner: CommandCls) -> Param: ...

    @overload
    def __get__(self, command: CommandObj, owner: CommandCls) -> Union[T_co, None]: ...

    def __get__(self, command, owner):
        if command is None:
            return self

        with self._ctx(command):
            value = self.result(command)

        if self._attr_name:
            command.__dict__[self._attr_name] = value  # Skip __get__ on subsequent accesses
        return value

    def result(self, command: CommandObj | None = None, missing_default: TD = _NotSet) -> Union[T_co, TD, None]:
        """The final result / parsed value for this Parameter that is returned upon access as a descriptor."""
        if (value := ctx.get_parsed_value(self)) is not _NotSet:
            return self.action.finalize_value(value)
        elif self.required:
            if missing_default is _NotSet:
                raise MissingArgument(self)
            return missing_default
        else:
            try:
                return self.action.get_default(command, missing_default)
            except InputValidationError as e:
                # At this point, a default value was provided when this param was defined, but it wasn't acceptable
                # TODO: Do any of the other cases handled by the `prepare_value` method need to be checked here?
                #  Need to test choices - a non-acceptable choice may make sense as the default in some cases
                raise BadArgument(self, f'bad default value - {e}') from e

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

    _default_ok: bool = False

    def __init_subclass__(cls, default_ok: bool = None, **kwargs):  # pylint: disable=W0222
        """
        :param default_ok: Whether default values are supported for this Parameter type
        :param kwargs: Additional keyword arguments to pass to :meth:`.Parameter.__init_subclass__`.
        """
        super().__init_subclass__(**kwargs)
        if default_ok is not None:
            cls._default_ok = default_ok

    def __init__(
        self, action: str, *, required: Bool = True, default: Any = _NotSet, default_cb: DefaultFunc = None, **kwargs
    ):
        if not (self._default_ok and 0 in self.nargs):  # Indicates that having a default is bad
            if not required:
                cls_name = self.__class__.__name__
                raise ParameterDefinitionError(f'All {cls_name} parameters must be required - invalid {required=}')
            elif kw := ('default' if default is not _NotSet else 'default_cb' if default_cb is not None else None):
                cls_name = self.__class__.__name__
                raise ParameterDefinitionError(f'The {kw!r} arg is not supported for {cls_name} parameters')
        super().__init__(action, default=default, required=required, default_cb=default_cb, **kwargs)


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
    :param env_var: A string or sequence (tuple, list, etc) of strings representing environment variables that should
      be searched for a value when no value was provided via CLI.  If a value was provided via CLI, then these variables
      will not be checked.  If multiple env variable names/keys were provided, then they will be checked in the order
      that they were provided.  When enabled, values from env variables take precedence over the default value.  When
      enabled and the Parameter is required, then either a CLI value or an env var value must be provided.
    :param strict_env: When ``True`` (the default), if an :paramref:`.BaseOption.env_var` is used as the source of a
      value for this Parameter and that value is invalid, then parsing will fail.  When ``False``, invalid values from
      environment variables will be ignored (and a warning message will be logged).
    :param use_env_value: For optional Parameters that support storing a constant (such as Flag), this option controls
      behavior when an :paramref:`.BaseOption.env_var` is used as the source of a value for this Parameter.
      If ``True``, the parsed value will be stored as this Parameter's value (it must be a valid value).  If ``False``
      (the default), then the parsed value will be used to determine whether the store/append const action should be
      taken as if it was specified as a CLI flag (e.g., ``--foo`` with no value).
    :param kwargs: Additional keyword arguments to pass to :class:`Parameter`.
    """

    _opt_str_cls: Type[OptionStrings] = OptionStrings
    option_strs: OptionStrings
    env_var: OptStrs = None
    show_env_var: Bool = None
    strict_env: Bool
    use_env_value: Bool
    const = _NotSet

    def __init__(
        self,
        *option_strs: str,
        action: str,
        name_mode: Union[OptionNameMode, str, None] = _NotSet,
        env_var: OptStrs = None,
        strict_env: bool = True,
        use_env_value: Bool = None,
        show_env_var: Bool = None,
        **kwargs,
    ):
        super().__init__(action, **kwargs)
        self.option_strs = self._opt_str_cls(option_strs, name_mode)
        self.strict_env = strict_env
        if env_var:
            self.env_var = env_var
        if use_env_value is not None:
            self.use_env_value = use_env_value
        if show_env_var is not None:
            self.show_env_var = show_env_var

    def _handle_bad_action(self, action: str) -> NoReturn:
        if action in ('store', 'append') and (fixed := f'{action}_const') in self._action_map:
            raise ParameterDefinitionError(f'Invalid {action=} for {self.__class__.__name__} - did you mean {fixed!r}?')
        super()._handle_bad_action(action)

    def __set_name__(self, command: CommandCls, name: str):
        super().__set_name__(command, name)
        if not self.option_strs.name_mode:
            self.option_strs.name_mode = self._config(command).option_name_mode
        self.option_strs.update(name)

    def env_vars(self) -> Iterator[str]:
        if self.env_var:
            if isinstance(self.env_var, str):
                yield self.env_var
            else:
                yield from self.env_var

    def get_const(self, opt_str: OptStr = None):
        return self.const


class AllowLeadingDashProperty:
    """
    Custom value normalizer/validator for the ``allow_leading_dash`` property of ``Positional`` and ``Option`` classes.
    """

    __slots__ = ('name', 'default')

    def __init__(self, default: AllowLeadingDash = AllowLeadingDash.NUMERIC):
        self.default = default

    def __set_name__(self, owner, name: str):
        self.name = name

    def __get__(self, instance: Union[Parameter, None], owner) -> Union[AllowLeadingDash, AllowLeadingDashProperty]:
        if instance is None:
            return self
        return instance.__dict__.get(self.name, self.default)

    def __set__(self, instance: Parameter, value: LeadingDash):
        if value is not None:
            value = AllowLeadingDash(value)

        nargs = instance.nargs
        if nargs.max is REMAINDER:
            if instance.type is not None:
                raise ParameterDefinitionError(f'Type casting and choices are not supported with {nargs=}')
            elif value not in (None, AllowLeadingDash.ALWAYS):
                raise ParameterDefinitionError(
                    f'With {nargs=}, only allow_leading_dash=AllowLeadingDash.ALWAYS is supported - found: {value!r}'
                )
            value = AllowLeadingDash.ALWAYS

        if value is not None:
            instance.__dict__[self.name] = value


class DefaultCallback:
    __slots__ = ('func', 'use_cmd')

    def __init__(self, func: CommandMethod | DefaultFunc, use_cmd: bool = False):
        self.func = func
        self.use_cmd = use_cmd

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}({self.func!r}, use_cmd={self.use_cmd})>'

    def __call__(self, command: CommandObj | None) -> T_co:
        # If the func isn't a method / doesn't accept the command, then `command` must not be None, but the default
        # callback is intentionally not called by ParamAction.get_default (and its subclasses) when command is None.
        return self.func(command) if self.use_cmd else self.func()
