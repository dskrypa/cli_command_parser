"""
:author: Doug Skrypa
"""

import logging
from abc import ABC, abstractmethod
from functools import cached_property
from itertools import chain
from typing import TYPE_CHECKING, Any, Type, Optional, Callable, Collection
from types import MethodType

from .exceptions import ParameterDefinitionError, BadArgument, MissingArgument, InvalidChoice, CommandDefinitionError
from .exceptions import ParamUsageError
from .groups import ParameterGroup
from .utils import _NotSet, Nargs, NargsValue, Bool, parameter_action

if TYPE_CHECKING:
    from .commands import Command, CommandType

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
]
log = logging.getLogger(__name__)


class Parameter(ABC):
    _actions: frozenset[str] = frozenset()
    accepts_values: bool = True
    accepts_none: bool = False
    type: Callable = None
    nargs: Nargs = Nargs(1)
    group: ParameterGroup = None
    command: Type['Command'] = None
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
        cls_name = self.__class__.__name__
        if action not in self._actions:
            raise ParameterDefinitionError(f'Invalid {action=} for {cls_name} - valid actions: {sorted(self._actions)}')
        elif not choices and choices is not None:
            raise ParameterDefinitionError(f'Invalid {choices=} - when specified, choices cannot be empty')
        self.action = action
        self.required = required
        self.default = None if default is _NotSet and not required else default
        self.name = name
        self.metavar = metavar
        self.choices = choices
        self._value = _NotSet
        self.provided = 0
        self.help = help
        if (group := ParameterGroup._active) is not None:
            group.register(self)  # This sets self.group = group

    def __set_name__(self, command: Type['Command'], name):
        self.command = command
        if self.name is None:
            self.name = name

    def __repr__(self) -> str:
        attrs = ('action', 'const', 'default', 'type', 'choices', 'required', 'hide', 'help')
        kwargs = ', '.join(
            f'{a}={v!r}'
            for a in attrs
            if (v := getattr(self, a, None)) not in (None, _NotSet) and not (a == 'hide' and not v)
        )
        return f'{self.__class__.__name__}({self.name!r}, {kwargs})'

    def __get__(self, instance, owner):
        if instance is None:
            return self
        instance.__dict__[self.name] = value = self.result()
        return value

    def take_action(self, value: Optional[str]):
        # log.debug(f'{self!r}.take_action({value!r})')
        if (action := self.action) == 'store' and self._value is not _NotSet:
            raise ParamUsageError(self, f'received {value=} but a stored value={self._value!r} already exists')
        elif action == 'append':
            nargs = self.nargs
            try:
                if (val_count := len(self._value)) >= nargs.max:
                    raise ParamUsageError(self, f'cannot accept any additional args with {nargs=}: {val_count=}')
            except TypeError:
                pass

        self.provided += 1
        action_method = getattr(self, self.action)
        if action in {'store_const', 'append_const'}:
            if value is not None:
                raise ParamUsageError(self, f'received {value=} but no values are accepted for {action=}')
            return action_method()
        else:
            normalized = self.prepare_value(value) if value is not None else value
            return action_method(normalized)

    def would_accept(self, value: str) -> bool:
        if (action := self.action) in {'store', 'store_all'} and self._value is not _NotSet:
            return False
        elif action == 'append':
            nargs = self.nargs
            try:
                if len(self._value) == nargs.max:
                    return False
            except TypeError:
                pass
        try:
            normalized = self.prepare_value(value)
        except BadArgument:
            return False
        return self.is_valid_arg(normalized)

    def prepare_value(self, value: str) -> Any:
        if (type_func := self.type) is None:
            return value
        try:
            return type_func(value)
        except (TypeError, ValueError) as e:
            raise BadArgument(self, f'bad {value=} for type={type_func!r}') from e
        except Exception as e:
            raise BadArgument(self, f'unable to cast {value=} to type={type_func!r}') from e

    def is_valid_arg(self, value: Any) -> bool:
        if choices := self.choices:
            return value in choices
        elif isinstance(value, str) and value.startswith('-'):
            return False
        elif value is None:
            return self.accepts_none
        else:
            return self.accepts_values

    def result(self) -> Any:
        value = self._value
        if self.action == 'store':
            if value is _NotSet:
                if self.required:
                    raise MissingArgument(self)
                else:
                    return self.default
            elif (choices := self.choices) and value not in choices:
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

    def usage_str(self, include_meta: Bool = False, full: Bool = False, delim: str = ', ') -> str:
        return self.name

    @property
    def usage_metavar(self) -> str:
        if choices := self.choices:
            return '{{{}}}'.format(','.join(map(str, choices)))
        else:
            return self.metavar or self.name.upper()

    @abstractmethod
    def reset(self):
        raise NotImplementedError


class PassThru(Parameter):
    nargs = Nargs('*')

    def __init__(self, action: str = 'store_all', **kwargs):
        super().__init__(action=action, **kwargs)
        self._value = _NotSet

    def take_action(self, values: Collection[str]):
        if self._value is not _NotSet:
            raise ParamUsageError(self, f'received {values=} but a stored value={self._value!r} already exists')

        self.provided += 1
        normalized = list(map(self.prepare_value, values))
        action_method = getattr(self, self.action)
        return action_method(normalized)

    @parameter_action
    def store_all(self, values: Collection[str]):
        self._value = values

    def reset(self):
        self.provided = 0
        self._value = _NotSet


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
        self._value = [] if action == 'append' else _NotSet

    def reset(self):
        self.provided = 0
        self._value = [] if self.action == 'append' else _NotSet

    @parameter_action
    def store(self, value: Any):
        self._value = value

    @parameter_action
    def append(self, value: Any):
        self._value.append(value)


class LooseString(BasePositional):
    def __init__(self, action: str = 'append', choices: Collection[str] = None, **kwargs):
        super().__init__(action=action, **kwargs)
        self.register_choices(choices)
        self._value = []

    def reset(self):
        self.provided = 0
        self._value = []

    def register_choices(self, choices: Collection[str]):
        if choices is None:
            self.nargs = Nargs('+')
        elif choices and not all(isinstance(c, str) for c in choices):
            raise ParameterDefinitionError(f'Invalid {choices=} - all {self.__class__.__name__} choices must be strs')
        elif not choices:
            raise ParameterDefinitionError(f'Invalid {choices=} - when specified, choices cannot be empty')
        else:
            lens = set(map(len, map(str.split, choices)))
            self.nargs = Nargs(range(min(lens), max(lens) + 1))

        self.choices = choices

    @parameter_action
    def append(self, value: str):
        values = value.split()
        if not self.is_valid_arg(' '.join(values)):
            raise InvalidChoice(self, value, self.choices)

        self._value.extend(values)
        n_values = len(values)
        self.provided += n_values - 1
        return n_values

    def is_valid_arg(self, value: str) -> bool:
        if values := self._value:
            combined = ' '.join(values) + ' ' + value
        else:
            combined = value
        if choices := self.choices:
            return combined in choices or any(c.startswith(combined) for c in choices)
        elif value.startswith('-'):
            return False
        return True

    def result(self) -> str:
        values = self._value
        nargs = self.nargs
        if (val_count := len(values)) == 0 and 0 not in nargs:
            raise MissingArgument(self)
        elif val_count not in nargs:
            raise BadArgument(self, f'expected {nargs=} values but found {val_count}')

        combined = ' '.join(values)
        if (choices := self.choices) and combined not in choices:
            raise InvalidChoice(self, combined, choices)

        return combined


class SubCommand(LooseString):
    cmd_command_map: dict[str, 'CommandType']

    def __init__(self, *args, **kwargs):
        if (choices := kwargs.setdefault('choices', None)) is not None:
            raise ParameterDefinitionError(
                f'Invalid {choices=} - {self.__class__.__name__} choices must be added via register'
            )
        super().__init__(*args, **kwargs)
        self.choices = set()
        self.cmd_command_map = {}

    def register(self, command: 'CommandType') -> 'CommandType':
        """
        Register a :class:`Command` as a sub-command.  This method may be used as a decorator if the sub-command does
        not extend its parent Command.  When extending a parent Command, this method is called automatically during
        Command subclass initialization.
        """
        try:
            cmd = command._Command__cmd
        except AttributeError:
            raise CommandDefinitionError(f'Invalid {command=} - expected a Command subclass')
        else:
            if cmd is None:
                raise CommandDefinitionError(f"Missing class kwarg 'cmd' for {command}")

        try:
            sub_cmd = self.cmd_command_map[cmd]
        except KeyError:
            if getattr(command, '_Command__parent', None) is None:
                command._Command__parent = self.command
            self.cmd_command_map[cmd] = command
            self.choices.add(cmd)
            lens = set(map(len, map(str.split, self.choices)))
            self.nargs = Nargs(range(min(lens), max(lens) + 1))
            return command
        else:
            parent = getattr(command, '_Command__parent', None)
            raise CommandDefinitionError(f'Invalid {cmd=} for {command} with {parent=} - already assigned to {sub_cmd}')

    def result(self) -> 'CommandType':
        cmd = super().result()
        return self.cmd_command_map[cmd]


class Action(LooseString):
    # TODO: Either register should accept an optional name arg, or this should not extend LooseString
    name_method_map: dict[str, MethodType]

    def __init__(self, *args, **kwargs):
        if (choices := kwargs.setdefault('choices', None)) is not None:
            raise ParameterDefinitionError(
                f'Invalid {choices=} - {self.__class__.__name__} choices must be added via register'
            )
        super().__init__(*args, **kwargs)
        self.choices = set()
        self.name_method_map = {}

    def register(self, method: MethodType) -> Callable:
        name = method.__name__
        try:
            action_method = self.name_method_map[name]
        except KeyError:
            self.name_method_map[name] = method
            self.choices.add(name)
            lens = set(map(len, map(str.split, self.choices)))
            self.nargs = Nargs(range(min(lens), max(lens) + 1))
            return method
        else:
            raise CommandDefinitionError(f'Invalid {name=} for {method} - already assigned to {action_method}')

    def result(self) -> MethodType:
        name = super().result()
        return self.name_method_map[name]


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

    def __set_name__(self, owner, name):
        if self.name is None:
            self.name = name
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

    def usage_str(self, include_meta: Bool = False, full: Bool = False, delim: str = ', ') -> str:
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

    def format_help(self, width: int = 30, add_default: Bool = True) -> str:
        arg_str = '  ' + self.usage_str(include_meta=True, full=True)
        help_str = self.help or ''
        if add_default and (default := self.default) is not _NotSet:
            pad = ' ' if help_str else ''
            help_str += f'{pad}(default: {default})'

        if help_str:
            pad_chars = width - 2 - len(arg_str)
            pad = ('\n' + ' ' * width) if pad_chars < 0 else (' ' * pad_chars)
            return f'{arg_str}{pad}{help_str}'
        else:
            return arg_str


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
        self._value = [] if action == 'append' else _NotSet

    def reset(self):
        self.provided = 0
        self._value = [] if self.action == 'append' else _NotSet

    @parameter_action
    def store(self, value: Any):
        self._value = value

    @parameter_action
    def append(self, value: Any):
        self._value.append(value)


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
        self._value = default if action == 'store_const' else []

    def reset(self):
        self.provided = 0
        self._value = self.default if self.action == 'store_const' else []

    @parameter_action
    def store_const(self):
        self._value = self.const

    @parameter_action
    def append_const(self):
        self._value.append(self.const)

    def would_accept(self, value: Optional[str]) -> bool:
        return value is None

    def result(self) -> Any:
        return self._value


class Counter(BaseOption, accepts_values=True, accepts_none=True):
    type = int
    nargs = Nargs('?')

    def __init__(self, *args, action: str = 'append', default: int = 0, const: int = 1, **kwargs):
        vals = {'const': const, 'default': default}
        if bad_types := ', '.join(f'{k}={v!r}' for k, v in vals.items() if not isinstance(v, self.type)):
            raise ParameterDefinitionError(f'Invalid type for parameters (expected int): {bad_types}')
        super().__init__(*args, action=action, default=default, **kwargs)
        self.const = const
        self._value = default

    def reset(self):
        self.provided = 0
        self._value = self.default

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
    def append(self, value: Optional[int]):
        if value is None:
            value = self.const
        self._value += value

    def is_valid_arg(self, value: Any) -> bool:
        if value is None or isinstance(value, self.type):
            return True
        try:
            value = self.type(value)
        except (ValueError, TypeError):
            return False
        else:
            return True

    def result(self) -> int:
        return self._value


# endregion
