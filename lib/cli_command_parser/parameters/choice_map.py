"""
ChoiceMap Parameters

:author: Doug Skrypa
"""

from __future__ import annotations

from functools import partial
from string import whitespace, printable
from typing import TYPE_CHECKING, Any, Type, Optional, Callable, Union, Collection, Mapping, Dict
from types import MethodType

from ..context import ctx, ParseState
from ..exceptions import ParameterDefinitionError, BadArgument, MissingArgument, InvalidChoice, CommandDefinitionError
from ..formatting.utils import format_help_entry
from ..nargs import Nargs
from ..utils import _NotSet, camel_to_snake_case
from .base import BasePositional, parameter_action

if TYPE_CHECKING:
    from ..core import CommandType
    from ..typing import Bool

__all__ = ['SubCommand', 'Action']


class Choice:
    """
    Used internally to store a value that can be provided as a choice for a parameter, and the target value / callable
    associated with that choice.
    """

    __slots__ = ('choice', 'target', 'help')

    def __init__(self, choice: Optional[str], target: Any = _NotSet, help: str = None):  # noqa
        self.choice = choice
        self.target = choice if target is _NotSet else target
        self.help = help

    def __repr__(self) -> str:
        help_str = f', help={self.help!r}' if self.help else ''
        target_str = f', target={self.target}' if self.choice != self.target else ''
        return f'{self.__class__.__name__}({self.choice!r}{target_str}{help_str})'

    def format_usage(self) -> str:
        return '(default)' if self.choice is None else self.choice

    def format_help(self, lpad: int = 4, tw_offset: int = 0, prefix: str = '') -> str:
        usage = self.format_usage()
        return format_help_entry(usage, self.help, lpad, tw_offset=tw_offset, prefix=prefix)


class ChoiceMap(BasePositional):
    """
    Base class for :class:`SubCommand` and :class:`Action`.  It is not meant to be used directly.

    Allows choices to be defined and provided as a string that may contain spaces, without requiring users to escape or
    quote the string (i.e., as technically separate arguments).  This allows for a more natural way to provide
    multi-word commands, without needing to jump through hoops to handle them.

    :param action: The action to take on individual parsed values.  Actions must be defined as methods in classes
      that extend Parameter, and must be registered via :class:`.parameter_action`.  Defaults to (and only supports)
      ``append``.  The ``nargs`` value is automatically calculated / maintained, based on the number of distinct
      words in the defined choices.  While most parameters that use ``action='append'`` will return a list, the
      final value for ChoiceMap parameters will instead be a string of space-separated provided values.
    :param title: The title to use for help text sections containing the choices for this parameter.  Default value
      depends on what is provided by subclasses.
    :param description: The description to be used in help text for this parameter.
    :param kwargs: Additional keyword arguments to pass to :class:`.BasePositional`.
    """

    _choice_validation_exc = ParameterDefinitionError
    _default_title: str = 'Choices'
    nargs = Nargs('+')
    choices: Dict[str, Choice]
    title: Optional[str]
    description: Optional[str]

    def __init_subclass__(  # pylint: disable=W0222
        cls, title: str = None, choice_validation_exc: Type[Exception] = None, **kwargs
    ):
        """
        :param title: Default title to use for help text sections containing the choices for this parameter.
        :param choice_validation_exc: The type of exception to raise when validating defined choices.
        :param kwargs: Additional keyword arguments to pass to :meth:`.Parameter.__init_subclass__`.
        """
        super().__init_subclass__(**kwargs)
        if title is not None:
            cls._default_title = title
        if choice_validation_exc is not None:
            cls._choice_validation_exc = choice_validation_exc

    def __init__(self, *, action: str = 'append', title: str = None, description: str = None, **kwargs):
        super().__init__(action=action, **kwargs)
        self.title = title
        self.description = description
        self.choices = {}

    def _init_value_factory(self, state: ParseState):
        return []

    # region Choice Registration

    @property
    def has_choices(self) -> bool:
        return bool(self.choices)

    def _update_nargs(self):
        try:
            lengths = set(map(len, map(str.split, self.choices)))
        except TypeError:
            lengths = set(map(len, map(str.split, filter(None, self.choices))))
            lengths.add(0)

        self.nargs = Nargs(lengths)

    def register_choice(self, choice: str, target: Any = _NotSet, help: str = None):  # noqa
        _validate_positional(self.__class__.__name__, choice, exc=self._choice_validation_exc)
        self._register_choice(choice, target, help)

    def _register_choice(self, choice: Optional[str], target: Any = _NotSet, help: str = None):  # noqa
        try:
            existing = self.choices[choice]
        except KeyError:
            self.choices[choice] = Choice(choice, target, help)
            self._update_nargs()
        else:
            prefix = 'Invalid default' if choice is None else f'Invalid choice={choice!r} for'
            raise CommandDefinitionError(f'{prefix} target={target!r} - already assigned to {existing}')

    # endregion

    # region Argument Handling

    @parameter_action
    def append(self, value: str):
        values = value.split()
        if not self.is_valid_arg(' '.join(values)):
            raise InvalidChoice(self, value, self.choices)

        ctx.get_parsed_value(self).extend(values)
        n_values = len(values)
        ctx.record_action(self, n_values - 1)  # - 1 because it was already called before dispatching to this method
        return n_values

    def validate(self, value: str):
        values = ctx.get_parsed_value(self).copy()
        values.append(value)
        choices = self.choices
        if choices:
            choice = ' '.join(values)
            if choice in choices:
                return
            elif len(values) > self.nargs.max:
                raise BadArgument(self, 'too many values')
            prefix = choice + ' '
            if not any(c.startswith(prefix) for c in choices if c):
                raise InvalidChoice(self, prefix[:-1], choices)
        elif value.startswith('-'):
            raise BadArgument(self, f'invalid value={value!r}')

    def result_value(self) -> Optional[str]:
        choices = self.choices
        if not choices:
            raise CommandDefinitionError(f'No choices were registered for {self}')

        values = ctx.get_parsed_value(self)
        if not values:
            if None in choices:
                return None
            raise MissingArgument(self)
        val_count = len(values)
        if val_count not in self.nargs:
            raise BadArgument(self, f'expected nargs={self.nargs} values but found {val_count}')
        choice = ' '.join(values)
        if choice not in choices:
            raise InvalidChoice(self, choice, choices)
        return choice

    result = result_value

    def target(self):
        choice = self.result_value()
        return self.choices[choice].target

    # endregion

    # region Usage / Help Text

    @property
    def show_in_help(self) -> bool:
        return bool(self.choices)

    # endregion


class SubCommand(ChoiceMap, title='Subcommands', choice_validation_exc=CommandDefinitionError):
    """
    Used to indicate the position where a choice that results in delegating execution of the program to a sub-command
    should be provided.

    Sub :class:`.Command` classes are automatically registered as choices for a SubCommand parameter
    if they extend the Command that contains a SubCommand parameter instead of extending Command directly.  When
    automatically registered, the choice will be the lower-case name of the sub command class.  It is possible to
    :meth:`.register` sub commands explicitly to specify a different choice value.
    """

    def __init__(
        self,
        *,
        required: Bool = True,
        local_choices: Optional[Union[Mapping[str, str], Collection[str]]] = None,
        **kwargs,
    ):
        """
        :param required: Whether this parameter is required or not.  If it is required, then an exception will be
          raised if the user did not provide a value for this parameter.  Defaults to ``True``.  If not required and
          not provided, the :meth:`~.Command.main` method for the base :class:`.Command` that contains this
          SubCommand will be executed by default.
        :param local_choices: If some choices should be handled in the Command that this SubCommand is in, they should
          be specified here.  Supports either a mapping of ``{choice: help text}`` or a collection of choice values.
        :param kwargs: Additional keyword arguments to pass to :class:`ChoiceMap`.
        """
        super().__init__(**kwargs)
        self.required = required
        if not required:
            self._register_choice(None, None)  # Results in next_cmd=None in parse_args, so the base cmd will run
        if local_choices:
            self._register_local_choices(local_choices)

    def _register_local_choices(self, local_choices: Union[Mapping[str, str], Collection[str]]):
        try:
            choice_help_iter = local_choices.items()
        except AttributeError:
            choice_help_iter = ((choice, None) for choice in local_choices)

        for choice, help_text in choice_help_iter:
            self._register_choice(choice, None, help_text)

    def register_command(self, choice: Optional[str], command: CommandType, help: Optional[str]) -> CommandType:  # noqa
        if choice is None:
            choice = camel_to_snake_case(command.__name__)
        else:
            _validate_positional(self.__class__.__name__, choice, exc=self._choice_validation_exc)

        try:
            self.register_choice(choice, command, help)
        except CommandDefinitionError:
            from ..core import get_parent

            parent = get_parent(command)
            target = self.choices[choice].target
            msg = f'Invalid choice={choice!r} for {command} with parent={parent!r} - already assigned to {target}'
            raise CommandDefinitionError(msg) from None

        return command

    def register(
        self, command_or_choice: Union[str, CommandType] = None, *, choice: str = None, help: str = None  # noqa
    ) -> Callable[[CommandType], CommandType]:
        """
        Class decorator version of :meth:`.register_command`.  Registers the wrapped :class:`.Command` as the
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
                raise CommandDefinitionError(
                    f'Cannot combine a positional command_or_choice={command_or_choice!r} choice with choice={choice!r}'
                )
            return partial(self.register_command, command_or_choice, help=help)
        else:
            return self.register_command(choice, command_or_choice, help=help)  # noqa


class Action(ChoiceMap, title='Actions'):
    """
    Actions are similar to :class:`.SubCommand` parameters, but allow methods in :class:`.Command` classes to
    be registered as a callable to be executed based on a user's choice instead of separate sub Commands.

    Actions are better suited for use cases where all of the target functions accept the same arguments.  If target
    functions require different / additional parameters, then using a :class:`.SubCommand` with separate sub
    :class:`.Command` classes may make more sense.
    """

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
        *,
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
        :return: The original method, unchanged.  When called explicitly, a
          `partial <https://docs.python.org/3/library/functools.html#functools.partial>`__ method will be returned
          first, which will automatically be called by the interpreter with the method to be decorated, and that call
          will return the original method.
        """
        if isinstance(method_or_choice, str):
            if choice is not None:
                raise CommandDefinitionError(
                    f'Cannot combine a positional method_or_choice={method_or_choice!r} choice with choice={choice!r}'
                )
            method_or_choice, choice = None, method_or_choice

        if method_or_choice is None:
            return partial(self.register_action, choice, help=help, default=default)
        else:
            return self.register_action(choice, method_or_choice, help=help, default=default)

    __call__ = register


def _validate_positional(
    param_cls: str, value: str, prefix: str = 'choice', exc: Type[Exception] = ParameterDefinitionError
):
    if not value or value.startswith('-'):
        raise exc(f"Invalid {param_cls} {prefix}={value!r} - may not be empty or start with '-'")

    bad = {c for c in value if (c in whitespace and c != ' ') or c not in printable}
    if bad:
        raise exc(f'Invalid {param_cls} {prefix}={value!r} - invalid characters: {bad}')
