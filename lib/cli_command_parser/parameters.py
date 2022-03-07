"""
Parameters and Groups

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

from .context import ctx
from .exceptions import ParameterDefinitionError, BadArgument, MissingArgument, InvalidChoice, CommandDefinitionError
from .exceptions import ParamUsageError, ParamConflict, ParamsMissing, NoActiveContext
from .formatting import HelpEntryFormatter
from .nargs import Nargs, NargsValue
from .utils import (
    _NotSet,
    Bool,
    validate_positional,
    camel_to_snake_case,
    get_descriptor_value_type,
    is_numeric,
)

if TYPE_CHECKING:
    from .core import CommandType
    from .commands import Command

__all__ = [
    'Parameter',
    'PassThru',
    'BasePositional',
    'Positional',
    'SubCommand',
    'Action',
    'BaseOption',
    'Option',
    'Flag',
    'Counter',
    'ActionFlag',
    'action_flag',
    'before_main',
    'after_main',
    'Param',
    'ParamGroup',
    'ParamOrGroup',
]
log = logging.getLogger(__name__)

Param = TypeVar('Param', bound='Parameter')
ParamOrGroup = Union[Param, 'ParamGroup']


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
    group: 'ParamGroup' = None
    command: 'CommandType' = None
    required: Bool = False
    help: str = None
    hide: Bool = False

    def __init__(self, name: str = None, required: Bool = False, help: str = None, hide: Bool = False):  # noqa
        self.required = required
        self.name = name
        self.help = help
        self.hide = hide
        if (group := ParamGroup.active_group()) is not None:
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
        self.command = command  # TODO: Is it really necessary to store a reference to the command?
        if self._name is None:
            self.name = name
        self.__name = name

    def __hash__(self) -> int:
        return reduce(xor, map(hash, (self.__class__, self.__name, self.name, self.command)))

    @property
    @abstractmethod
    def show_in_help(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def format_usage(self, include_meta: Bool = False, full: Bool = False, delim: str = ', ') -> str:
        raise NotImplementedError

    @abstractmethod
    def format_help(self, width: int = 30, add_default: Bool = True) -> str:
        raise NotImplementedError


class ParamGroup(ParamBase):
    """A group of parameters."""

    _local = local()
    description: Optional[str]
    members: list[ParamOrGroup]
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
        hide: Bool = False,
    ):
        super().__init__(name=name, required=required, hide=hide)
        self.description = description
        self.members = []
        if mutually_dependent and mutually_exclusive:
            name = self.name or 'Options'
            raise ParameterDefinitionError(f'group={name!r} cannot be both mutually_exclusive and mutually_dependent')
        self.mutually_exclusive = mutually_exclusive
        self.mutually_dependent = mutually_dependent

    def add(self, param: ParamOrGroup):
        """Add the given parameter without storing a back-reference.  Primary use case is for help text only groups."""
        self.members.append(param)

    def register(self, param: ParamOrGroup):
        if self.mutually_exclusive:
            if (isinstance(param, BasePositional) and 0 not in param.nargs) or isinstance(param, PassThru):
                cls_name = param.__class__.__name__
                raise CommandDefinitionError(
                    f'Cannot add {param=} to {self} - {cls_name} parameters cannot be mutually exclusive'
                )
            elif isinstance(param, BaseOption) and param.required:
                raise CommandDefinitionError(
                    f'Cannot add {param=} to {self} - required parameters cannot be mutually exclusive (but the group'
                    f' can be required)'
                )

        self.members.append(param)
        param.group = self

    def register_all(self, params: Iterable[ParamOrGroup]):
        for param in params:
            self.register(param)

    def __repr__(self) -> str:
        exclusive, dependent = str(self.mutually_exclusive)[0], str(self.mutually_dependent)[0]
        members = len(self.members)
        return f'<{self.__class__.__name__}[{self.name!r}, {members=}, m.{exclusive=!s}, m.{dependent=!s}]>'

    @classmethod
    def active_group(cls) -> Optional['ParamGroup']:
        try:
            return cls._local.stack[-1]
        except (AttributeError, IndexError):
            return None

    def __hash__(self) -> int:
        return super().__hash__()

    def __eq__(self, other: 'ParamGroup') -> bool:
        if isinstance(other, ParamGroup) and self.group == other.group:
            attrs = ('mutually_exclusive', 'mutually_dependent', 'name', 'description', 'members')
            return all(getattr(self, a) == getattr(other, a) for a in attrs)
        return False

    def __lt__(self, other: 'ParamGroup') -> bool:
        if not isinstance(other, ParamGroup):
            return NotImplemented
        elif self in other.members:
            return True

        group = self.group
        other_group = other.group
        if group != other_group:
            if group is None:
                return False
            elif other_group is None:
                return True
            else:
                return group < other_group

        return self.name < other.name

    def __enter__(self) -> 'ParamGroup':
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
        return param in self.members

    def __iter__(self) -> Iterator[ParamOrGroup]:
        yield from self.members

    def _categorize_params(self) -> tuple[list[Param], list[Param]]:
        provided = []
        missing = []
        for obj in self.members:
            if ctx.num_provided(obj):
                provided.append(obj)
            else:
                missing.append(obj)

        return provided, missing

    def _check_conflicts(self, provided: list[Param], missing: list[Param]):
        # log.debug(f'{self}: Checking group conflicts in {args=}')
        if not (self.mutually_dependent or self.mutually_exclusive):
            return

        # log.debug(f'{provided=}, {missing=}')
        # log.debug(f'provided={len(provided)}, missing={len(missing)}')
        if self.mutually_dependent and provided and missing:
            p_str = ', '.join(p.format_usage(full=True, delim='/') for p in provided)
            be = 'was' if len(provided) == 1 else 'were'
            raise ParamsMissing(missing, f'because {p_str} {be} provided')
        elif self.mutually_exclusive and not 0 <= len(provided) < 2:
            raise ParamConflict(provided, 'they are mutually exclusive - only one is allowed')

    def validate(self):
        provided, missing = self._categorize_params()
        ctx.record_action(self, len(provided))
        self._check_conflicts(provided, missing)

        required = self.required or (self.mutually_dependent and any(p.required for p in self.members))
        if required and not ctx.num_provided(self):
            raise ParamsMissing(missing)

    @property
    def contains_positional(self) -> bool:
        return any(isinstance(p, BasePositional) for p in self)

    @property
    def show_in_help(self) -> bool:
        if self.hide or not self.members:
            return False
        elif (group := self.group) is not None:
            return group.show_in_help
        return True

    def format_description(self, group_type: 'Bool' = True) -> str:
        description = self.description or f'{self.name} options'
        if group_type and (self.mutually_exclusive or self.mutually_dependent):
            description += ' (mutually {})'.format('exclusive' if self.mutually_exclusive else 'dependent')
        return description

    def format_usage(self, include_meta: Bool = False, full: Bool = False, delim: str = ', ') -> str:
        choices = ','.join(mem.format_usage(include_meta, full, delim) for mem in self.members)
        return f'{{{choices}}}'

    def format_help(
        self, width: int = 30, add_default: 'Bool' = True, group_type: 'Bool' = True, clean: Bool = True
    ) -> str:
        """
        Prepare the help text for this group.

        :param width: The width of the option/action/command column.
        :param add_default: Whether default values should be included in the help text for parameters.
        :param group_type: Whether the group type should be included in the description if this is a mutually
          exclusive / dependent group
        :param clean: If this group only contains other groups or Action or SubCommand parameters, then omit the
          description.
        :return: The formatted help text.
        """
        parts = [self.format_description(group_type) + ':']

        nested, params = 0, 0
        for member in self.members:
            if not member.show_in_help:
                continue

            if isinstance(member, (ChoiceMap, ParamGroup)):
                nested += 1
                parts.append('')  # Add space for readability
            else:
                params += 1
            parts.append(member.format_help(width=width, add_default=add_default))

        if clean and nested and not params:
            parts = parts[2:]  # remove description and the first spacer

        parts.append('')
        return '\n'.join(parts)


class Parameter(ParamBase, ABC):
    _actions: frozenset[str] = frozenset()
    _positional: bool = False
    accepts_none: bool = False
    accepts_values: bool = True
    choices: Optional[Collection[Any]] = None
    metavar: str = None
    nargs: Nargs = Nargs(1)
    type: Callable = None

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
        hide: Bool = False,
    ):
        if action not in self._actions:
            raise ParameterDefinitionError(
                f'Invalid {action=} for {self.__class__.__name__} - valid actions: {sorted(self._actions)}'
            )
        if not choices and choices is not None:
            raise ParameterDefinitionError(f'Invalid {choices=} - when specified, choices cannot be empty')
        super().__init__(name=name, required=required, help=help, hide=hide)
        self.action = action
        self.choices = choices
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

    def __set_name__(self, command: 'CommandType', name: str):
        super().__set_name__(command, name)
        if self.type is None and (annotated_type := get_descriptor_value_type(command, name)) is not None:
            self.type = annotated_type

    def __get__(self, command: 'Command', owner: 'CommandType'):
        if command is None:
            return self

        try:
            value = self.result()
        except NoActiveContext:
            with command._Command__ctx:
                value = self.result()

        if (name := self._name) is not None:
            command.__dict__[name] = value  # Skip __get__ on subsequent accesses
        return value

    def _nargs_max_reached(self):
        try:
            return len(ctx.get_parsing_value(self)) >= self.nargs.max
        except TypeError:
            return False

    def take_action(self, value: Optional[str], short_combo: bool = False):
        # log.debug(f'{self!r}.take_action({value!r})')
        if (action := self.action) == 'store' and (val := ctx.get_parsing_value(self)) is not _NotSet:
            raise ParamUsageError(self, f'received {value=} but a stored value={val!r} already exists')
        elif action == 'append' and self._nargs_max_reached():
            val_count = len(ctx.get_parsing_value(self))
            raise ParamUsageError(self, f'cannot accept any additional args with nargs={self.nargs}: {val_count=}')

        ctx.record_action(self)
        action_method = getattr(self, self.action)
        if action in {'store_const', 'append_const'}:
            if value is not None:
                raise ParamUsageError(self, f'received {value=} but no values are accepted for {action=}')
            return action_method()
        else:
            normalized = self.prepare_value(value, short_combo) if value is not None else value
            self.validate(normalized)
            return action_method(normalized)

    def would_accept(self, value: str, short_combo: bool = False) -> bool:
        if (action := self.action) in {'store', 'store_all'} and ctx.get_parsing_value(self) is not _NotSet:
            return False
        elif action == 'append' and self._nargs_max_reached():
            return False
        try:
            normalized = self.prepare_value(value, short_combo)
        except BadArgument:
            return False
        return self.is_valid_arg(normalized)

    def prepare_value(self, value: str, short_combo: bool = False) -> Any:
        if (type_func := self.type) is None:
            return value
        try:
            return type_func(value)
        except (TypeError, ValueError) as e:
            raise BadArgument(self, f'bad {value=} for type={type_func!r}') from e
        except Exception as e:
            raise BadArgument(self, f'unable to cast {value=} to type={type_func!r}') from e

    def validate(self, value: Any):
        if (choices := self.choices) and value not in choices:
            raise InvalidChoice(self, value, choices)
        elif isinstance(value, str) and value.startswith('-'):
            if not is_numeric(value):
                raise BadArgument(self, f'invalid {value=}')
        elif value is None:
            if not self.accepts_none:
                raise MissingArgument(self)
        elif not self.accepts_values:
            raise BadArgument(self, f'does not accept values, but {value=} was provided')

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

    result = result_value

    @property
    def show_in_help(self) -> bool:
        if self.hide:
            return False
        elif (group := self.group) is not None:
            return group.show_in_help
        return True

    def format_usage(self, include_meta: Bool = False, full: Bool = False, delim: str = ', ') -> str:
        return self.usage_metavar

    def format_help(self, width: int = 30, add_default: Bool = True) -> str:
        usage = self.format_usage(include_meta=True, full=True)
        description = self.help or ''
        if add_default and (default := self.default) is not _NotSet:
            pad = ' ' if description else ''
            description += f'{pad}(default: {default})'
        return HelpEntryFormatter(usage, description, width)()

    @property
    def usage_metavar(self) -> str:
        if choices := self.choices:
            return '{{{}}}'.format(','.join(map(str, choices)))
        else:
            return self.metavar or self.name.upper()


# region Positional Parameters


class BasePositional(Parameter, ABC):
    _positional: bool = True

    def __init__(self, action: str, **kwargs):
        if not (required := kwargs.setdefault('required', True)):
            cls_name = self.__class__.__name__
            raise ParameterDefinitionError(f'All {cls_name} parameters must be required - invalid {required=}')
        elif kwargs.setdefault('default', _NotSet) is not _NotSet:
            cls_name = self.__class__.__name__
            raise ParameterDefinitionError(f"The 'default' arg is not supported for {cls_name} parameters")
        super().__init__(action, **kwargs)

    def format_basic_usage(self) -> str:
        return self.format_usage()

    def format_usage(self, include_meta: Bool = False, full: Bool = False, delim: str = ', ') -> str:
        metavar = self.usage_metavar
        return metavar if not full or self.nargs == 1 else f'{metavar} [{metavar} ...]'


class Positional(BasePositional):
    def __init__(
        self,
        nargs: NargsValue = None,
        action: str = _NotSet,
        type: Callable = None,  # noqa
        default: Any = _NotSet,
        **kwargs,
    ):
        if nargs is not None:
            self.nargs = Nargs(nargs)
            if self.nargs == 0:
                cls_name = self.__class__.__name__
                raise ParameterDefinitionError(f'Invalid nargs={self.nargs} - {cls_name} must allow at least 1 value')
        if action is _NotSet:
            action = 'store' if self.nargs == 1 or self.nargs == Nargs('?') else 'append'
        elif action == 'store' and self.nargs.max != 1:
            raise ParameterDefinitionError(f'Invalid {action=} for nargs={self.nargs}')
        if default is not _NotSet and (action != 'store' or 0 not in self.nargs):
            raise ParameterDefinitionError(f'Invalid {default=} - only allowed for Positional parameters when nargs=?')
        super().__init__(action=action, **kwargs)
        self.type = type
        if action == 'append':
            self._init_value_factory = list
        if 0 in self.nargs:
            self.required = False
            if action == 'store':
                self.default = None if default is _NotSet else default

    @parameter_action
    def store(self, value: Any):
        ctx.set_parsing_value(self, value)

    @parameter_action
    def append(self, value: Any):
        ctx.get_parsing_value(self).append(value)


# endregion

# region Choice Mapping Parameters


class Choice:
    __slots__ = ('choice', 'target', 'help')

    def __init__(self, choice: Optional[str], target: Any = _NotSet, help: str = None):  # noqa
        self.choice = choice
        self.target = choice if target is _NotSet else target
        self.help = help

    def __repr__(self) -> str:
        help_str = f', help={self.help!r}' if self.help else ''
        target_str = f', target={self.target}' if self.choice != self.target else ''
        return f'{self.__class__.__name__}({self.choice!r}{target_str}{help_str})'

    def format_help(self, width: int = 30, lpad: int = 4) -> str:
        choice = '(default)' if self.choice is None else self.choice
        return HelpEntryFormatter(choice, self.help, width, lpad)()


class ChoiceMap(BasePositional):
    _choice_validation_exc = ParameterDefinitionError
    _default_title: str = 'Choices'
    nargs = Nargs('+')
    choices: dict[str, Choice]
    title: Optional[str]
    description: Optional[str]

    def __init_subclass__(cls, title: str = None, choice_validation_exc: Type[Exception] = None, **kwargs):
        super().__init_subclass__(**kwargs)
        if title is not None:
            cls._default_title = title
        if choice_validation_exc is not None:
            cls._choice_validation_exc = choice_validation_exc

    def __init__(self, action: str = 'append', title: str = None, description: str = None, **kwargs):
        if (choices := kwargs.setdefault('choices', None)) is not None:
            raise ParameterDefinitionError(
                f'Invalid {choices=} - {self.__class__.__name__} choices must be added via register'
            )
        super().__init__(action=action, **kwargs)
        self._init_value_factory = list
        self.title = title
        self.description = description
        self.choices = {}

    def _update_nargs(self):
        try:
            lengths = set(map(len, map(str.split, self.choices)))
        except TypeError:
            lengths = set(map(len, map(str.split, filter(None, self.choices))))
            lengths.add(0)

        self.nargs = Nargs(lengths)

    def register_choice(self, choice: str, target: Any = _NotSet, help: str = None):  # noqa
        validate_positional(self.__class__.__name__, choice, exc=self._choice_validation_exc)
        self._register_choice(choice, target, help)

    def _register_choice(self, choice: Optional[str], target: Any = _NotSet, help: str = None):  # noqa
        try:
            existing = self.choices[choice]
        except KeyError:
            self.choices[choice] = Choice(choice, target, help)
            self._update_nargs()
        else:
            prefix = 'Invalid default' if choice is None else f'Invalid {choice=} for'
            raise CommandDefinitionError(f'{prefix} {target=} - already assigned to {existing}')

    @parameter_action
    def append(self, value: str):
        values = value.split()
        if not self.is_valid_arg(' '.join(values)):
            raise InvalidChoice(self, value, self.choices)

        ctx.get_parsing_value(self).extend(values)
        n_values = len(values)
        ctx.record_action(self, n_values - 1)  # - 1 because it was already called before dispatching to this method
        return n_values

    def validate(self, value: str):
        values = ctx.get_parsing_value(self).copy()
        values.append(value)
        if choices := self.choices:
            choice = ' '.join(values)
            if choice in choices:
                return
            elif len(values) > self.nargs.max:
                raise BadArgument(self, 'too many values')
            prefix = choice + ' '
            if not any(c.startswith(prefix) for c in choices if c):
                raise InvalidChoice(self, prefix[:-1], choices)
        elif value.startswith('-'):
            raise BadArgument(self, f'invalid {value=}')
        # TODO: Should this raise an error?

    def result_value(self) -> Optional[str]:
        if not (choices := self.choices):
            raise CommandDefinitionError(f'No choices were registered for {self}')
        elif not (values := ctx.get_parsing_value(self)):
            if None in choices:
                return None
            raise MissingArgument(self)
        elif (val_count := len(values)) not in self.nargs:
            raise BadArgument(self, f'expected nargs={self.nargs} values but found {val_count}')
        elif (choice := ' '.join(values)) not in choices:
            raise InvalidChoice(self, choice, choices)
        return choice

    def result(self):
        choice = self.result_value()
        return self.choices[choice].target

    @property
    def show_in_help(self) -> bool:
        return bool(self.choices)

    @property
    def usage_metavar(self) -> str:
        if choices := self.choices:
            return '{{{}}}'.format(','.join(map(str, filter(None, choices))))
        else:
            return self.metavar or self.name.upper()

    def format_usage(self, include_meta: Bool = None, full: Bool = None, delim: str = None) -> str:
        return self.usage_metavar

    def format_help(self, width: int = 30, add_default: 'Bool' = None):
        title = self.title or self._default_title
        help_entry = HelpEntryFormatter(self.format_usage(), self.description, width, lpad=2)()
        parts = [f'{title}:', help_entry]
        for choice in self.choices.values():
            parts.append(choice.format_help(width, lpad=4))

        parts.append('')
        return '\n'.join(parts)


class SubCommand(ChoiceMap, title='Subcommands', choice_validation_exc=CommandDefinitionError):
    def register_command(
        self, choice: Optional[str], command: 'CommandType', help: Optional[str]  # noqa
    ) -> 'CommandType':
        if choice is None:
            choice = camel_to_snake_case(command.__name__)
        else:
            validate_positional(self.__class__.__name__, choice, exc=self._choice_validation_exc)

        try:
            self.register_choice(choice, command, help)
        except CommandDefinitionError:
            from .core import get_parent

            parent = get_parent(command)
            raise CommandDefinitionError(
                f'Invalid {choice=} for {command} with {parent=} - already assigned to {self.choices[choice].target}'
            ) from None

        return command

    def register(
        self, command_or_choice: Union[str, 'CommandType'] = None, /, choice: str = None, help: str = None  # noqa
    ) -> Callable[['CommandType'], 'CommandType']:
        """
        Class decorator version of :meth:`.register_command`.  Registers the wrapped :class:`~.commands.Command` as the
        subcommand class to be used for further parsing when the given choice is specified for this parameter.

        This is only necessary for subcommands that do not extend their parent Command class.  When extending a parent
        Command, it is automatically registered as a subcommand during Command subclass initialization.

        :param command_or_choice: When not called explicitly, this will be Command class that will be wrapped.  When
          called to provide arguments, the ``choice`` value for the positional parameter that determines which
          subcommand was chosen may be provided here.  Defaults to the name of the decorated class, converted from
          CamelCase to snake_case.
        :param choice: Keyword-only way to provide the ``choice`` value.  May not be combined with a positional
          ``choice`` string value.
        :param help: (Keyword-only) The help text / description to be displayed for this choice
        """
        if command_or_choice is None:
            return partial(self.register_command, choice, help=help)
        elif isinstance(command_or_choice, str):
            if choice is not None:
                raise CommandDefinitionError(f'Cannot combine a positional {command_or_choice=} choice with {choice=}')
            return partial(self.register_command, command_or_choice, help=help)
        else:
            return self.register_command(choice, command_or_choice, help=help)  # noqa


class Action(ChoiceMap, title='Actions'):
    def register_action(
        self, choice: Optional[str], method: MethodType, help: str = None, default: Bool = False  # noqa
    ) -> MethodType:
        if help is None:
            try:
                help = method.__doc__  # noqa
            except AttributeError:
                pass

        if default:
            if help is None:
                help = 'Default action if no other action is specified'  # noqa
            if choice:  # register both the explicit and the default choices
                self.register_choice(choice, method, help)
            self._register_choice(None, method, help)
        else:
            self.register_choice(choice or method.__name__, method, help)

        return method

    def register(
        self,
        method_or_choice: Union[str, MethodType] = None,
        /,
        choice: str = None,
        help: str = None,  # noqa
        default: Bool = False,
    ) -> Union[MethodType, Callable[[MethodType], MethodType]]:
        """
        Decorator that registers the wrapped method to be called when the given choice is specified for this parameter.
        Methods may also be registered by decorating them with the instantiated Action parameter directly - doing so
        calls this method.

        This decorator may be used with or without arguments.  When no arguments are needed, it does not need to be
        explicitly called.

        :param method_or_choice: When not called explicitly, this will be the method that will be wrapped.  When called
          to provide arguments, the ``choice`` value may be provided as a positional argument here.  Defaults to the
          name of the decorated method.
        :param choice: Keyword-only way to provide the ``choice`` value.  May not be combined with a positional
          ``choice`` string value.
        :param help: (Keyword-only) The help text / description to be displayed for this choice
        :param default: (Keyword-only) If true, this method will be registered as the default action to take when no
          other choice is specified.  When marking a method as the default, if you want it to also be available as an
          explicit choice, then a ``choice`` value must be specified.
        :return: The original method, unchanged.  When called explicitly, a :class:`~functools.partial` method
          will be returned first, which will automatically be called by the interpreter with the method to be decorated,
          and that call will return the original method.
        """
        # TODO: Accept params=Collection[ParamOrGroup] and treat more like a subcommand?
        if isinstance(method_or_choice, str):
            if choice is not None:
                raise CommandDefinitionError(f'Cannot combine a positional {method_or_choice=} choice with {choice=}')
            method_or_choice, choice = None, method_or_choice

        if method_or_choice is None:
            return partial(self.register_action, choice, help=help, default=default)
        else:
            return self.register_action(choice, method_or_choice, help=help, default=default)

    __call__ = register


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

    def format_basic_usage(self) -> str:
        usage = self.format_usage(True)
        return usage if self.required else f'[{usage}]'

    def format_usage(self, include_meta: Bool = False, full: Bool = False, delim: str = ', ') -> str:
        if include_meta:
            metavar = self.usage_metavar.replace('{', '{{').replace('}', '}}')
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
        type: Callable = None,  # noqa
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
        self.type = type
        if action == 'append':
            self._init_value_factory = list

    @parameter_action
    def store(self, value: Any):
        ctx.set_parsing_value(self, value)

    @parameter_action
    def append(self, value: Any):
        ctx.get_parsing_value(self).append(value)


class Flag(BaseOption, accepts_values=False, accepts_none=True):
    __default_const_map = {True: False, False: True, _NotSet: True}
    nargs = Nargs(0)

    def __init__(self, *args, action: str = 'store_const', default: Any = _NotSet, const: Any = _NotSet, **kwargs):
        if const is _NotSet:
            try:
                const = self.__default_const_map[default]
            except KeyError as e:
                cls = self.__class__.__name__
                raise ParameterDefinitionError(f"Missing parameter='const' for {cls} with {default=}") from e
        if default is _NotSet:
            default = self.__default_const_map.get(const)  # will be True, False, or None
        super().__init__(*args, action=action, default=default, **kwargs)
        self.const = const

    def _init_value_factory(self):
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


class ActionFlag(Flag):
    def __init__(
        self, *args, order: Union[int, float] = 1, func: Callable = None, before_main: Bool = True, **kwargs  # noqa
    ):
        # TODO: Test in groups, esp mutually excl/dependent
        expected = {'action': 'store_const', 'default': False, 'const': _NotSet}
        found = {k: kwargs.setdefault(k, v) for k, v in expected.items()}
        if bad := {k: v for k, v in found.items() if expected[k] != v}:
            raise ParameterDefinitionError(f'Unsupported kwargs for {self.__class__.__name__}: {bad}')
        super().__init__(*args, **kwargs)
        self.func = func
        self.order = order
        self.before_main = before_main

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

    def __eq__(self, other: 'ActionFlag') -> bool:
        if not isinstance(other, ActionFlag):
            return NotImplemented
        return all(getattr(self, a) == getattr(other, a) for a in ('name', 'func', 'command', 'order', 'before_main'))

    def __lt__(self, other: 'ActionFlag') -> bool:
        if not isinstance(other, ActionFlag):
            return NotImplemented
        return (not self.before_main, self.order, self.name) < (not self.before_main, other.order, other.name)

    def __call__(self, func: Callable):
        if self.func is not None:
            raise CommandDefinitionError(f'Cannot re-assign the func to call for {self}')
        self.func = func
        return self

    def __get__(self, command: 'Command', owner: 'CommandType'):
        # Allow the method to be called, regardless of whether it was specified
        if command is None:
            return self
        return partial(self.func, command)

    def result(self) -> Optional[Callable]:
        if self.result_value():
            if func := self.func:
                return func
            raise ParameterDefinitionError(f'No function was registered for {self}')
        return None


action_flag = ActionFlag
before_main = partial(ActionFlag, before_main=True)  #: An ActionFlag that will be executed before main()
after_main = partial(ActionFlag, before_main=False)  #: An ActionFlag that will be executed after main()


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

    def prepare_value(self, value: Optional[str], short_combo: bool = False) -> int:
        if value is None:
            return self.const
        try:
            return self.type(value)
        except (ValueError, TypeError) as e:
            if short_combo and (combinable := self.short_combinable) and all(c in combinable for c in value):  # noqa
                return len(value) + 1  # +1 for the -short that preceded this value
            raise BadArgument(self, f'bad counter {value=}') from e

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
            raise BadArgument(self, f'invalid {value=}') from e
        else:
            return

    def result_value(self) -> int:
        return ctx.get_parsing_value(self)

    result = result_value


# endregion


class PassThru(Parameter):
    nargs = Nargs('*')

    def __init__(self, action: str = 'store_all', **kwargs):
        super().__init__(action=action, **kwargs)

    def take_action(self, values: Collection[str], short_combo: bool = False):
        value = ctx.get_parsing_value(self)
        if value is not _NotSet:
            raise ParamUsageError(self, f'received {values=} but a stored {value=} already exists')

        ctx.record_action(self)
        normalized = list(map(self.prepare_value, values))
        action_method = getattr(self, self.action)
        return action_method(normalized)

    @parameter_action
    def store_all(self, values: Collection[str]):
        ctx.set_parsing_value(self, values)

    def format_basic_usage(self) -> str:
        usage = self.format_usage()
        return f'-- {usage}' if self.required else f'[-- {usage}]'
