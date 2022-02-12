"""
:author: Doug Skrypa
"""

import logging
from abc import ABC, abstractmethod
from functools import cached_property, partial, update_wrapper, reduce
from itertools import chain
from operator import xor
from threading import local
from typing import TYPE_CHECKING, Any, Type, Optional, Callable, Collection, Union, TypeVar, Iterable, Iterator
from types import MethodType

from .exceptions import ParameterDefinitionError, BadArgument, MissingArgument, InvalidChoice, CommandDefinitionError
from .exceptions import ParamUsageError, UsageError
from .nargs import Nargs, NargsValue
from .utils import _NotSet, Args, Bool, validate_positional, camel_to_snake_case

if TYPE_CHECKING:
    from .commands import BaseCommand, CommandType

__all__ = [
    'Parameter',
    'PassThru',
    'BasePositional',
    'Positional',
    'LooseString',
    'SubCommand',
    'Action',
    'BaseOption',
    'Option',
    'Flag',
    'Counter',
    'ActionFlag',
    'action_flag',
    'Param',
    'ParameterGroup',
    'ParamOrGroup',
]
log = logging.getLogger(__name__)

Param = TypeVar('Param', bound='Parameter')
ParamOrGroup = Union[Param, 'ParameterGroup']


class parameter_action:
    def __init__(self, method: MethodType):
        self.method = method
        update_wrapper(self, method)

    def __set_name__(self, parameter_cls: Type['Parameter'], name: str):
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
    __name: str = None
    _name: str = None
    group: 'ParameterGroup' = None
    command: 'CommandType' = None
    choices: Optional[Collection[Any]] = None
    required: Bool = False
    help: str = None

    def __init__(
        self,
        name: str = None,
        required: Bool = False,
        help: str = None,  # noqa
        choices: Collection[Any] = None,
    ):
        if not choices and choices is not None:
            raise ParameterDefinitionError(f'Invalid {choices=} - when specified, choices cannot be empty')
        self.required = required
        self.name = name
        self.help = help
        self.choices = choices
        if (group := ParameterGroup.active_group()) is not None:
            group.register(self)  # noqa  # This sets self.group = group

    @property
    def name(self) -> str:
        if (name := self._name) is not None:
            return name
        return f'{self.__class__.__name__}#{id(self)}'

    @name.setter
    def name(self, value: Optional[str]):
        if value is not None:
            self._name = value

    def __set_name__(self, command: 'CommandType', name: str):
        self.command = command
        if self._name is None:
            self.name = name
        self.__name = name

    def __hash__(self) -> int:
        return reduce(xor, map(hash, (self.__class__, self.__name, self.name, self.command)))

    @abstractmethod
    def format_usage(self, include_meta: Bool = False, full: Bool = False, delim: str = ', ') -> str:
        raise NotImplementedError

    @abstractmethod
    def format_help(self, width: int = 30, add_default: Bool = True) -> str:
        raise NotImplementedError


class ParameterGroup(ParamBase):
    """
    A group of parameters.

    Group nesting is not implemented due to the complexity and potential confusion that it would add for cases where
    differing mutual exclusivity/dependency rules would need to be resolved.  In theory, though, it should be possible.
    """

    _local = local()
    description: Optional[str]
    parameters: list['Parameter']
    groups: list['ParameterGroup']
    choices: list[ParamOrGroup]
    mutually_exclusive: Bool = False
    mutually_dependent: Bool = False

    def __init__(
        self,
        name: str = None,
        *,
        description: str = None,
        mutually_exclusive: Bool = False,
        mutually_dependent: Bool = False,
        required: Bool = False,
    ):
        super().__init__(name=name, required=required)
        self.description = description
        self.parameters = []
        self.groups = []
        self.choices = []
        if mutually_dependent and mutually_exclusive:
            name = self.name or 'Options'
            raise ParameterDefinitionError(f'group={name!r} cannot be both mutually_exclusive and mutually_dependent')
        self.mutually_exclusive = mutually_exclusive
        self.mutually_dependent = mutually_dependent

    def add(self, param: ParamOrGroup):
        """Add the given parameter without storing a back-reference.  Primary use case is for help text only groups."""
        if isinstance(param, ParameterGroup):
            self.groups.append(param)
        else:
            self.parameters.append(param)
        if self.mutually_exclusive:
            self.choices.append(param)

    def maybe_add_all(self, params: Iterable[ParamOrGroup]):
        for param in params:
            if not param.group:
                self.add(param)

    def register(self, param: ParamOrGroup):
        if isinstance(param, ParameterGroup):
            self.groups.append(param)
        else:
            self.parameters.append(param)
        if self.mutually_exclusive:
            self.choices.append(param)
        param.group = self

    def register_all(self, params: Iterable[ParamOrGroup]):
        for param in params:
            if isinstance(param, ParameterGroup):
                self.groups.append(param)
            else:
                self.parameters.append(param)
            if self.mutually_exclusive:
                self.choices.append(param)
            param.group = self

    def __repr__(self) -> str:
        exclusive, dependent = self.mutually_exclusive, self.mutually_dependent
        members = len(self.parameters)
        return f'<{self.__class__.__name__}[{self.name!r}, {members=}, m.{exclusive=!s}, m.{dependent=!s}]>'

    @classmethod
    def active_group(cls) -> Optional['ParameterGroup']:
        try:
            return cls._local.stack[-1]
        except (AttributeError, IndexError):
            return None

    def __hash__(self) -> int:
        return super().__hash__()

    def __eq__(self, other: 'ParameterGroup') -> bool:
        if isinstance(other, ParameterGroup) and self.group == other.group:
            attrs = ('mutually_exclusive', 'mutually_dependent', 'name', 'description', 'parameters', 'groups')
            return all(getattr(self, a) == getattr(other, a) for a in attrs)
        return False

    def __lt__(self, other: 'ParameterGroup') -> bool:
        if not isinstance(other, ParameterGroup):
            return NotImplemented

        group = self.group
        if group == other.group:
            return self.name < other.name
        elif group is None:  # Top-level - push to right (process conflicts last)
            return False
        elif group in other.groups:  # Nested in other - push to left (process conflicts first)
            return True
        else:
            return self.name < other.name

    def __enter__(self) -> 'ParameterGroup':
        try:
            stack = self._local.stack
        except AttributeError:
            self._local.stack = stack = []
        stack.append(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._local.stack.pop()
        return None

    def __contains__(self, param: ParamOrGroup) -> bool:
        return param in self.parameters or param in self.groups

    def __iter__(self) -> Iterator[Param]:
        yield from self.parameters

    def _categorize_params(self, args: 'Args') -> tuple[list[Param], list[Param]]:
        provided = []
        missing = []
        for obj in chain(self.parameters, self.groups):
            if args.num_provided(obj):
                provided.append(obj)
            else:
                missing.append(obj)

        return provided, missing

    def check_conflicts(self, args: 'Args'):
        # log.debug(f'{self}: Checking group conflicts in {args=}')
        provided, missing = self._categorize_params(args)
        args.record_action(self, len(provided))
        if not (self.mutually_dependent or self.mutually_exclusive):
            return

        # log.debug(f'{provided=}, {missing=}')
        # log.debug(f'provided={len(provided)}, missing={len(missing)}')
        if self.mutually_dependent and provided and missing:
            p_str = ', '.join(p.format_usage(full=True, delim='/') for p in provided)
            m_str = ', '.join(p.format_usage(full=True, delim='/') for p in missing)
            be = 'is' if len(provided) == 1 else 'are'
            raise UsageError(f'When {p_str} {be} provided, then the following must also be provided: {m_str}')
        elif self.mutually_exclusive and not 0 <= len(provided) < 2:
            p_str = ', '.join(p.format_usage(full=True, delim='/') for p in provided)
            raise UsageError(f'The following arguments are mutually exclusive - only one is allowed: {p_str}')

    def format_description(self, group_type: 'Bool' = True) -> str:
        description = self.description or f'{self.name} options'
        if group_type and (self.mutually_exclusive or self.mutually_dependent):
            description += ' (mutually {})'.format('exclusive' if self.mutually_exclusive else 'dependent')
        return description

    def format_usage(self, include_meta: Bool = False, full: Bool = False, delim: str = ', ') -> str:
        p_groups = (self.parameters, self.groups)
        choices = ','.join(p.format_usage(include_meta, full, delim) for p_group in p_groups for p in p_group)
        return f'{{{choices}}}'

    def format_help(self, width: int = 30, add_default: 'Bool' = True, group_type: 'Bool' = True):
        parts = [self.format_description(group_type) + ':']
        for param in self.parameters:
            parts.append(param.format_help(width=width, add_default=add_default))
        parts.append('')
        return '\n'.join(parts)


class Parameter(ParamBase):
    _actions: frozenset[str] = frozenset()
    accepts_values: bool = True
    accepts_none: bool = False
    type: Callable = None
    nargs: Nargs = Nargs(1)
    hide: Bool = False

    def __init_subclass__(cls, accepts_values: bool = None, accepts_none: bool = None):
        actions = set(cls._actions)  # Inherit actions from parent
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

    def __init__(
        self,
        action: str,
        name: str = None,
        default: Any = _NotSet,
        required: Bool = False,
        metavar: str = None,
        choices: Collection[Any] = None,
        help: str = None,  # noqa
    ):
        if action not in self._actions:
            raise ParameterDefinitionError(
                f'Invalid {action=} for {self.__class__.__name__} - valid actions: {sorted(self._actions)}'
            )
        super().__init__(name=name, required=required, help=help, choices=choices)
        self.action = action
        self.default = None if default is _NotSet and not required else default
        self.metavar = metavar

    @staticmethod
    def _init_value_factory():
        return _NotSet

    def __repr__(self) -> str:
        attrs = ('action', 'const', 'default', 'type', 'choices', 'required', 'hide', 'help')
        kwargs = ', '.join(
            f'{a}={v!r}'
            for a in attrs
            if (v := getattr(self, a, None)) not in (None, _NotSet) and not (a == 'hide' and not v)
        )
        return f'{self.__class__.__name__}({self.name!r}, {kwargs})'

    def __get__(self, command: 'BaseCommand', owner: 'CommandType'):
        if command is None:
            return self
        value = self.result(command._BaseCommand__args)  # noqa
        if (name := self._name) is not None:
            command.__dict__[name] = value  # Skip __get__ on subsequent accesses
        return value

    def take_action(self, args: Args, value: Optional[str]):
        # log.debug(f'{self!r}.take_action({value!r})')
        if (action := self.action) == 'store' and args[self] is not _NotSet:
            raise ParamUsageError(self, f'received {value=} but a stored value={args[self]!r} already exists')
        elif action == 'append':
            nargs = self.nargs
            try:
                if (val_count := len(args[self])) >= nargs.max:
                    raise ParamUsageError(self, f'cannot accept any additional args with {nargs=}: {val_count=}')
            except TypeError:
                pass

        args.record_action(self)
        action_method = getattr(self, self.action)
        if action in {'store_const', 'append_const'}:
            if value is not None:
                raise ParamUsageError(self, f'received {value=} but no values are accepted for {action=}')
            return action_method(args)
        else:
            normalized = self.prepare_value(value) if value is not None else value
            return action_method(args, normalized)

    def would_accept(self, args: Args, value: str) -> bool:
        if (action := self.action) in {'store', 'store_all'} and args[self] is not _NotSet:
            return False
        elif action == 'append':
            nargs = self.nargs
            try:
                if len(args[self]) == nargs.max:
                    return False
            except TypeError:
                pass
        try:
            normalized = self.prepare_value(value)
        except BadArgument:
            return False
        return self.is_valid_arg(args, normalized)

    def prepare_value(self, value: str) -> Any:
        if (type_func := self.type) is None:
            return value
        try:
            return type_func(value)
        except (TypeError, ValueError) as e:
            raise BadArgument(self, f'bad {value=} for type={type_func!r}') from e
        except Exception as e:
            raise BadArgument(self, f'unable to cast {value=} to type={type_func!r}') from e

    def is_valid_arg(self, args: Args, value: Any) -> bool:
        if choices := self.choices:
            return value in choices
        elif isinstance(value, str) and value.startswith('-'):
            return False
        elif value is None:
            return self.accepts_none
        else:
            return self.accepts_values

    def result(self, args: Args) -> Any:
        value = args[self]
        if value is _NotSet:
            if self.required:
                raise MissingArgument(self)
            else:
                return self.default
        elif self.action == 'store':
            if (choices := self.choices) and value not in choices:
                raise InvalidChoice(self, value, choices)
            else:
                return value
        else:  # action == 'append' or 'store_all'
            nargs = self.nargs
            if (val_count := len(value)) == 0 and 0 not in nargs:
                raise MissingArgument(self)
            elif val_count not in nargs:
                raise BadArgument(self, f'expected {nargs=} values but found {val_count}')
            elif (choices := self.choices) and (bad_values := tuple(v for v in value if v not in choices)):
                raise InvalidChoice(self, bad_values, choices)
            else:
                return value

    def format_usage(self, include_meta: Bool = False, full: Bool = False, delim: str = ', ') -> str:
        return self.usage_metavar

    def format_help(self, width: int = 30, add_default: Bool = True) -> str:
        arg_str = '  ' + self.format_usage(include_meta=True, full=True)
        help_str = self.help or ''
        if add_default and (default := self.default) is not _NotSet:
            pad = ' ' if help_str else ''
            help_str += f'{pad}(default: {default})'

        if help_str:
            if (pad_chars := width - len(arg_str)) < 0:
                pad = '\n' + ' ' * width
            else:
                pad = ' ' * pad_chars
            return f'{arg_str}{pad}{help_str}'
        else:
            return arg_str

    @property
    def usage_metavar(self) -> str:
        if choices := self.choices:
            return '{{{}}}'.format(','.join(map(str, choices)))
        else:
            return self.metavar or self.name.upper()


class PassThru(Parameter):
    nargs = Nargs('*')

    def __init__(self, action: str = 'store_all', **kwargs):
        super().__init__(action=action, **kwargs)

    def take_action(self, args: Args, values: Collection[str]):
        value = args[self]
        if value is not _NotSet:
            raise ParamUsageError(self, f'received {values=} but a stored {value=} already exists')

        args.record_action(self)
        normalized = list(map(self.prepare_value, values))
        action_method = getattr(self, self.action)
        return action_method(args, normalized)

    @parameter_action
    def store_all(self, args: Args, values: Collection[str]):
        args[self] = values


# region Positional Parameters


class BasePositional(Parameter, ABC):
    def __init__(self, action: str, **kwargs):
        if not (required := kwargs.setdefault('required', True)):
            cls_name = self.__class__.__name__
            raise ParameterDefinitionError(f'All {cls_name} parameters must be required - invalid {required=}')
        elif kwargs.setdefault('default', _NotSet) is not _NotSet:
            cls_name = self.__class__.__name__
            raise ParameterDefinitionError(f"The 'default' arg is not supported for {cls_name} parameters")
        super().__init__(action, **kwargs)

    def format_usage(self, include_meta: Bool = False, full: Bool = False, delim: str = ', ') -> str:
        metavar = self.usage_metavar
        return metavar if not full or self.nargs == 1 else f'{metavar} [{metavar} ...]'


class Positional(BasePositional):
    def __init__(self, nargs: NargsValue = None, action: str = _NotSet, **kwargs):
        if nargs is not None:
            self.nargs = Nargs(nargs)
            if self.nargs == 0:
                cls_name = self.__class__.__name__
                raise ParameterDefinitionError(f'Invalid nargs={self.nargs} - {cls_name} must allow at least 1 value')
        if action is _NotSet:
            action = 'store' if self.nargs == 1 else 'append'
        super().__init__(action=action, **kwargs)
        if action == 'append':
            self._init_value_factory = list

    @parameter_action
    def store(self, args: Args, value: Any):
        args[self] = value

    @parameter_action
    def append(self, args: Args, value: Any):
        args[self].append(value)


class LooseString(BasePositional):
    choices: set[str] = None

    def __init__(self, action: str = 'append', choices: Collection[str] = None, **kwargs):
        super().__init__(action=action, **kwargs)
        self.register_choices(choices)
        self._init_value_factory = list

    def register_choices(self, choices: Collection[str]):
        if choices is None:
            self.nargs = Nargs('+')
        elif choices and not all(isinstance(c, str) for c in choices):
            raise ParameterDefinitionError(f'Invalid {choices=} - all {self.__class__.__name__} choices must be strs')
        elif not choices:
            raise ParameterDefinitionError(f'Invalid {choices=} - when specified, choices cannot be empty')
        else:
            self.choices = set(choices)
            self._update_nargs()

    def add_choice(self, choice: str):
        try:
            self.choices.add(choice)
        except AttributeError:  # Initialized with no choices
            self.choices = {choice}
        self._update_nargs()

    def _update_nargs(self):
        self.nargs = Nargs(set(map(len, map(str.split, self.choices))))

    @parameter_action
    def append(self, args: Args, value: str):
        values = value.split()
        if not self.is_valid_arg(args, ' '.join(values)):
            raise InvalidChoice(self, value, self.choices)

        args[self].extend(values)
        n_values = len(values)
        args.record_action(self, n_values - 1)
        return n_values

    def is_valid_arg(self, args: Args, value: str) -> bool:
        if values := args[self]:
            combined = ' '.join(values) + ' ' + value
        else:
            combined = value
        if choices := self.choices:
            return combined in choices or any(c.startswith(combined) for c in choices)
        elif value.startswith('-'):
            return False
        return True

    def result(self, args: Args) -> str:
        values = args[self]
        nargs = self.nargs
        if (val_count := len(values)) == 0 and 0 not in nargs:
            raise MissingArgument(self)
        elif val_count not in nargs:
            raise BadArgument(self, f'expected {nargs=} values but found {val_count}')

        combined = ' '.join(values)
        if (choices := self.choices) and combined not in choices:
            raise InvalidChoice(self, combined, choices)

        return combined

    def format_usage(self, include_meta: Bool = False, full: Bool = False, delim: str = ', ') -> str:
        return self.usage_metavar


class SubCommand(LooseString):
    choice_command_map: dict[str, 'CommandType']
    choice_help_map: dict[str, Optional[str]]

    def __init__(self, *args, **kwargs):
        if (choices := kwargs.setdefault('choices', None)) is not None:
            raise ParameterDefinitionError(
                f'Invalid {choices=} - {self.__class__.__name__} choices must be added via register'
            )
        super().__init__(*args, **kwargs)
        self.choices = set()
        self.choice_command_map = {}
        self.choice_help_map = {}

    def register_sub_command(
        self,
        choice: Optional[str],
        help: Optional[str],  # noqa
        command: 'CommandType',
    ) -> 'CommandType':
        validate_positional(f'{self.__class__.__name__} for {command}', choice, 'choice', exc=CommandDefinitionError)
        parent = command.parser().command_parent
        if choice is None:
            choice = camel_to_snake_case(command.__name__)
        try:
            sub_cmd = self.choice_command_map[choice]
        except KeyError:
            # if parent is None:
            #     command.parser().command_parent = self.command
            self.choice_command_map[choice] = command
            self.choice_help_map[choice] = help
            self.add_choice(choice)
            return command
        else:
            raise CommandDefinitionError(
                f'Invalid {choice=} for {command} with {parent=} - already assigned to {sub_cmd}'
            )

    def register(self, choice: str = None, help: str = None) -> Callable:  # noqa
        """
        Decorator version of :meth:`.register_sub_command`.  Registers the wrapped :class:`BaseCommand` as a sub command
        with the specified value to be used as the parameter choice that will be associated with that command.

        This is only necessary for sub commands that do not extend their parent Command class.  When extending a parent
        Command, it is automatically registered during BaseCommand subclass initialization.

        :param choice: The ``choice`` value for the positional parameter that determines which sub command was chosen.
          Defaults to the name of the decorated class, converted from CamelCase to snake_case.
        :param help: Help text to be displayed as a SubCommand option
        """
        return partial(self.register_sub_command, choice, help)

    def result(self, args: Args) -> 'CommandType':
        choice = super().result(args)
        return self.choice_command_map[choice]


class Action(LooseString):
    choice_method_map: dict[str, MethodType]
    choice_help_map: dict[str, Optional[str]]

    def __init__(self, *args, **kwargs):
        if (choices := kwargs.setdefault('choices', None)) is not None:
            raise ParameterDefinitionError(
                f'Invalid {choices=} - {self.__class__.__name__} choices must be added via register'
            )
        super().__init__(*args, **kwargs)
        self.choices = set()
        self.choice_method_map = {}
        self.choice_help_map = {}

    def register(
        self, method_or_choice: Union[str, MethodType] = None, /, choice: str = None, help: str = None  # noqa
    ) -> Callable:
        if method_or_choice is None:
            return partial(self._register, choice, help)
        elif isinstance(method_or_choice, str):
            if choice is not None:
                raise CommandDefinitionError(f'Cannot combine a positional {method_or_choice=} choice with {choice=}')
            return partial(self._register, method_or_choice, help)
        else:
            return self._register(choice, help, method_or_choice)

    __call__ = register

    def _register(self, choice: str, help: str, method: MethodType) -> Callable:  # noqa
        if choice:
            validate_positional(self.__class__.__name__, choice)
        else:
            choice = method.__name__

        try:
            action_method = self.choice_method_map[choice]
        except KeyError:
            self.choice_method_map[choice] = method
            self.choice_help_map[choice] = help
            self.add_choice(choice)
            return method
        else:
            raise CommandDefinitionError(f'Invalid {choice=} for {method} - already assigned to {action_method}')

    def result(self, args: Args) -> MethodType:
        choice = super().result(args)
        return self.choice_method_map[choice]


# endregion


# region Optional Parameters


class BaseOption(Parameter, ABC):
    # fmt: off
    _long_opts: set[str]        # --long options
    _short_opts: set[str]       # -short options
    short_combinable: set[str]  # short options without the leading dash (for combined flags)
    # fmt: on

    def __init__(self, *option_strs: str, action: str, **kwargs):
        if bad_opts := ', '.join(opt for opt in option_strs if not 0 < opt.count('-', 0, 3) < 3):
            raise ParameterDefinitionError(f"Bad option(s) - must start with '--' or '-': {bad_opts}")
        elif bad_opts := ', '.join(opt for opt in option_strs if opt.endswith('-')):
            raise ParameterDefinitionError(f"Bad option(s) - may not end with '-': {bad_opts}")
        elif bad_opts := ', '.join(opt for opt in option_strs if '=' in opt):
            raise ParameterDefinitionError(f"Bad option(s) - may not contain '=': {bad_opts}")
        super().__init__(action, **kwargs)
        self._long_opts = {opt for opt in option_strs if opt.startswith('--')}
        self._short_opts = short_opts = {opt for opt in option_strs if 1 == opt.count('-', 0, 2)}
        self.short_combinable = {opt[1:] for opt in short_opts if len(opt) == 2}
        if bad_opts := ', '.join(opt for opt in short_opts if '-' in opt[1:]):
            raise ParameterDefinitionError(f"Bad short option(s) - may not contain '-': {bad_opts}")

    def __set_name__(self, command: 'CommandType', name: str):
        super().__set_name__(command, name)
        if not self._long_opts:
            self._long_opts.add(f'--{name}')
            try:
                del self.__dict__['long_opts']
            except KeyError:
                pass

    @cached_property
    def long_opts(self) -> list[str]:
        return sorted(self._long_opts, key=lambda opt: (-len(opt), opt))

    @cached_property
    def short_opts(self) -> list[str]:
        return sorted(self._short_opts, key=lambda opt: (-len(opt), opt))

    def format_usage(self, include_meta: Bool = False, full: Bool = False, delim: str = ', ') -> str:
        if include_meta:
            metavar = self.usage_metavar
            fmt = '{}' if self.nargs == 0 else f'{{}} [{metavar}]' if 0 in self.nargs else f'{{}} {metavar}'
            if full:
                return delim.join(fmt.format(opt) for opt in chain(self.long_opts, self.short_opts))
            else:
                return fmt.format(self.long_opts[0])
        else:
            if full:
                return delim.join(chain(self.long_opts, self.short_opts))
            else:
                return self.long_opts[0]


class Option(BaseOption):
    def __init__(
        self,
        *args,
        nargs: NargsValue = None,
        action: str = _NotSet,
        default: Any = _NotSet,
        required: Bool = False,
        **kwargs,
    ):
        if not required and default is _NotSet:
            default = None
        if nargs is not None:
            self.nargs = Nargs(nargs)
        if 0 in self.nargs:
            raise ParameterDefinitionError(f'Invalid nargs={self.nargs} - use Flag or Counter for Options with 0 args')
        if action is _NotSet:
            action = 'store' if self.nargs == 1 else 'append'
        elif action == 'store' and self.nargs != 1:
            raise ParameterDefinitionError(f'Invalid nargs={self.nargs} for {action=}')
        super().__init__(*args, action=action, default=default, required=required, **kwargs)
        if action == 'append':
            self._init_value_factory = list

    @parameter_action
    def store(self, args: Args, value: Any):
        args[self] = value

    @parameter_action
    def append(self, args: Args, value: Any):
        args[self].append(value)


class Flag(BaseOption, accepts_values=False, accepts_none=True):
    nargs = Nargs(0)

    def __init__(self, *args, action: str = 'store_const', default: Any = False, const: Any = _NotSet, **kwargs):
        if const is _NotSet:
            try:
                const = {True: False, False: True}[default]
            except KeyError as e:
                cls = self.__class__.__name__
                raise ParameterDefinitionError(f"Missing parameter='const' for {cls} with {default=}") from e
        super().__init__(*args, action=action, default=default, **kwargs)
        self.const = const

    def _init_value_factory(self):
        if self.action == 'store_const':
            return self.default
        else:
            return []

    @parameter_action
    def store_const(self, args: Args):
        args[self] = self.const

    @parameter_action
    def append_const(self, args: Args):
        args[self].append(self.const)

    def would_accept(self, args: Args, value: Optional[str]) -> bool:
        return value is None

    def result(self, args: Args) -> Any:
        return args[self]


class ActionFlag(Flag):
    def __init__(self, *args, priority: Union[int, float] = 1, func: Callable = None, **kwargs):
        expected = {'action': 'store_const', 'default': False, 'const': _NotSet}
        found = {k: kwargs.setdefault(k, v) for k, v in expected.items()}
        if bad := {k: v for k, v in found.items() if expected[k] != v}:
            raise ParameterDefinitionError(f'Unsupported kwargs for {self.__class__.__name__}: {bad}')
        super().__init__(*args, **kwargs)
        self.func = func
        self.priority = priority
        self.enabled = True

    @property
    def func(self):
        return self._func

    @func.setter
    def func(self, func: Optional[Callable]):
        self._func = func
        if func is not None:
            update_wrapper(self, func)

    def __call__(self, func: Callable):
        if self.func is not None:
            raise CommandDefinitionError(f'Cannot re-assign the func to call for {self}')
        self.func = func
        return self

    def __get__(self, command: 'BaseCommand', owner: 'CommandType'):
        # Allow the method to be called, regardless of whether it was specified
        if command is None:
            return self
        return partial(self.func, command)

    def result(self, args: Args) -> Optional[Callable]:
        if super().result(args):
            if func := self.func:
                return func
            raise ParameterDefinitionError(f'No function was registered for {self}')
        return None


action_flag = ActionFlag


class Counter(BaseOption, accepts_values=True, accepts_none=True):
    type = int
    nargs = Nargs('?')

    def __init__(self, *args, action: str = 'append', default: int = 0, const: int = 1, **kwargs):
        vals = {'const': const, 'default': default}
        if bad_types := ', '.join(f'{k}={v!r}' for k, v in vals.items() if not isinstance(v, self.type)):
            raise ParameterDefinitionError(f'Invalid type for parameters (expected int): {bad_types}')
        super().__init__(*args, action=action, default=default, **kwargs)
        self.const = const

    def _init_value_factory(self):
        return self.default

    def prepare_value(self, value: Optional[str]) -> int:
        if value is None:
            return self.const
        try:
            return self.type(value)
        except (ValueError, TypeError) as e:
            if (combinable := self.short_combinable) and all(c in combinable for c in value):
                return len(value) + 1  # +1 for the -short that preceded this value
            raise BadArgument(self, f'bad counter {value=}') from e

    @parameter_action
    def append(self, args: Args, value: Optional[int]):
        if value is None:
            value = self.const
        args[self] += value

    def is_valid_arg(self, args: Args, value: Any) -> bool:
        if value is None or isinstance(value, self.type):
            return True
        try:
            value = self.type(value)
        except (ValueError, TypeError):
            return False
        else:
            return True

    def result(self, args: Args) -> int:
        return args[self]


# endregion
