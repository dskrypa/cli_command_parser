"""
ChoiceMap Parameters

:author: Doug Skrypa
"""

from __future__ import annotations

from functools import partial
from string import printable, whitespace
from types import MethodType
from typing import TYPE_CHECKING, Callable, Collection, Generic, Mapping, NoReturn, Optional, Type, TypeVar, Union

from ..context import ctx
from ..exceptions import BadArgument, CommandDefinitionError, InvalidChoice, ParameterDefinitionError
from ..formatting.utils import format_help_entry
from ..nargs import Nargs
from ..typing import Bool, CommandCls, CommandObj
from ..utils import _NotSet, camel_to_snake_case, short_repr
from .actions import Concatenate
from .base import BasePositional

if TYPE_CHECKING:
    from ..metadata import ProgramMetadata

__all__ = ['SubCommand', 'Action', 'Choice', 'ChoiceMap']

T = TypeVar('T')
TD = TypeVar('TD')
OptStr = Optional[str]
# TODO: Combine SubCommand and Action, replacing `local_choices` with stackable decorators on the target method,
#  optionally injecting the selected choice into positional args for the decorated method, which may be main?


class Choice(Generic[T]):
    """
    Used internally to store a value that can be provided as a choice for a parameter, and the target value / callable
    associated with that choice.
    """

    __slots__ = ('choice', 'target', 'help', 'local')

    def __init__(self, choice: OptStr, target: T = _NotSet, help: str = None, local: bool = False):  # noqa
        self.choice = choice
        self.target = choice if target is _NotSet else target
        self.help = help
        self.local = local

    def __repr__(self) -> str:
        help_str = f', help={short_repr(self.help)}' if self.help else ''
        target_str = f', target={self.target}' if self.choice != self.target else ''
        return f'{self.__class__.__name__}({self.choice!r}{target_str}{help_str})'

    def format_usage(self) -> str:
        return '(default)' if self.choice is None else self.choice

    def format_help(self, lpad: int = 4, prefix: str = '') -> str:
        # Note: no longer called by formatters
        return format_help_entry((self.format_usage(),), self.help, prefix, lpad=lpad)


class ChoiceMap(BasePositional[str], Generic[T], actions=(Concatenate,)):
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
    choices: dict[str, Choice[T]]
    title: OptStr
    description: OptStr

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

    def __init__(self, *, action: str = 'concatenate', title: str = None, description: str = None, **kwargs):
        super().__init__(action=action, **kwargs)
        self.title = title
        self.description = description
        self.choices = {}

    def register_default_cb(self, method):
        raise ParameterDefinitionError(f'{self.__class__.__name__}s do not support default callback methods')

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

    @classmethod
    def _validate_positional(cls, value: str, prefix: str = 'choice'):
        if not value or value.startswith('-'):
            raise cls._choice_validation_exc(
                f"Invalid {cls.__name__} {prefix}={value!r} - may not be empty or start with '-'"
            )

        if bad := {c for c in value if (c in whitespace and c != ' ') or c not in printable}:
            raise cls._choice_validation_exc(f'Invalid {cls.__name__} {prefix}={value!r} - invalid characters: {bad}')

    def register_choice(self, choice: str, target: T = _NotSet, help: str = None):  # noqa
        self._validate_positional(choice)
        self._register_choice(choice, target, help)

    def _register_choice(
        self,
        choice: OptStr,
        target: Optional[T] = _NotSet,
        help: str = None,  # noqa
        local: bool = False,
    ):
        try:
            existing = self.choices[choice]
        except KeyError:
            self.choices[choice] = Choice(choice, target, help, local)
            self._update_nargs()
        else:
            prefix = 'Invalid default' if choice is None else f'Invalid {choice=} for'
            raise CommandDefinitionError(f'{prefix} {target=} - already assigned to {existing}')

    def _no_choices_error(self) -> NoReturn:
        raise CommandDefinitionError(f'No choices were registered for {self}')

    # endregion

    # region Argument Handling

    def validate(self, value: str, joined: Bool = False):
        if not self.choices:
            self._no_choices_error()

        parsed = ctx.get_parsed_value(self)
        values = (value,) if parsed is _NotSet else (*parsed, value)
        if (choice := ' '.join(values)) in self.choices:
            return
        elif len(values) > self.nargs.max:
            raise BadArgument(self, 'too many values')
        prefix = choice + ' '
        if not any(c.startswith(prefix) for c in self.choices if c):
            raise InvalidChoice(self, prefix[:-1], self.choices)

    def result(self, command: CommandObj | None = None, missing_default: TD = _NotSet) -> Union[OptStr, TD]:
        if not self.choices:
            self._no_choices_error()
        return super().result(command, missing_default)

    def target(self) -> T:
        return self.choices[self.result(None)].target

    # endregion

    # region Usage / Help Text

    @property
    def show_in_help(self) -> bool:
        return bool(self.choices)

    # endregion


class SubCommand(ChoiceMap[CommandCls], title='Subcommands', choice_validation_exc=CommandDefinitionError):
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
        default_help: str = None,
        local_choices: Optional[Union[Mapping[str, str], Collection[str]]] = None,
        **kwargs,
    ):
        """
        :param required: Whether this parameter is required or not.  If it is required, then an exception will be
          raised if the user did not provide a value for this parameter.  Defaults to ``True``.  If not required and
          not provided, the :meth:`~.Command.main` method for the base :class:`.Command` that contains this
          SubCommand will be executed by default.
        :param default_help: Help text to display for the default choice.  Only used if ``required=False``.
        :param local_choices: If some choices should be handled in the Command that this SubCommand is in, they should
          be specified here.  Supports either a mapping of ``{choice: help text}`` or a collection of choice values.
        :param kwargs: Additional keyword arguments to pass to :class:`ChoiceMap`.
        """
        super().__init__(**kwargs)
        self.required = required
        if not required:
            # This results in next_cmd=None in parse_args, so the base cmd will run
            self._register_choice(None, None, default_help)
            self.default = None
        if local_choices:
            self._register_local_choices(local_choices)

    @property
    def has_local_choices(self) -> bool:
        return None in self.choices or any(c.target is None for c in self.choices.values())

    def _register_local_choices(self, local_choices: Union[Mapping[str, str], Collection[str]]):
        try:
            choice_help_iter = local_choices.items()
        except AttributeError:
            choice_help_iter = ((choice, None) for choice in local_choices)

        for choice, help_text in choice_help_iter:
            self._register_choice(choice, None, help_text, True)

    def register_command(self, choice: OptStr, command: CommandCls, help: OptStr) -> CommandCls:  # noqa
        if choice is None:
            choice = camel_to_snake_case(command.__name__)
        else:
            self._validate_positional(choice)

        if help is None:
            # This approach was used because importing get_metadata from core would result in a circular dependency
            meta: ProgramMetadata = command.__class__.meta(command)
            # print(f'Registering {choice=} -> {command=} w/ {meta.description=}, {meta.parent=}')
            if meta.description and (not meta.parent or meta.parent.description != meta.description):
                help = meta.description  # noqa

        try:
            self.register_choice(choice, command, help)
        except CommandDefinitionError:
            from ..core import get_parent

            parent = get_parent(command)
            msg = f'Invalid {choice=} for {command} with {parent=} - already assigned to {self.choices[choice].target}'
            raise CommandDefinitionError(msg) from None

        command._is_subcommand_ = True  # This is used indirectly by ``main()`` to filter out non-top-level Commands
        return command

    def register(
        self,
        command_or_choice: Union[str, CommandCls] = None,
        *,
        choice: str = None,
        help: str = None,  # noqa
    ) -> Callable[[CommandCls], CommandCls]:
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
                raise CommandDefinitionError(f'Cannot combine a positional {command_or_choice=} choice with {choice=}')
            return partial(self.register_command, command_or_choice, help=help)
        else:
            return self.register_command(choice, command_or_choice, help=help)  # noqa

    def _no_choices_error(self) -> NoReturn:
        raise CommandDefinitionError(f'{ctx.command_cls}.{self.name} = {self} has no sub Commands')


class Action(ChoiceMap[MethodType], title='Actions'):
    """
    Actions are similar to :class:`.SubCommand` parameters, but allow methods in :class:`.Command` classes to
    be registered as a callable to be executed based on a user's choice instead of separate sub Commands.

    Actions are better suited for use cases where all of the target functions accept the same arguments.  If target
    functions require different / additional parameters, then using a :class:`.SubCommand` with separate sub
    :class:`.Command` classes may make more sense.
    """

    def register_action(
        self,
        choice: OptStr,
        method: MethodType,
        help: str = None,  # noqa
        default: Bool = False,
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
            self.default = None
            self.required = False
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
                raise CommandDefinitionError(f'Cannot combine a positional {method_or_choice=} choice with {choice=}')
            method_or_choice, choice = None, method_or_choice

        if method_or_choice is None:
            return partial(self.register_action, choice, help=help, default=default)
        else:
            return self.register_action(choice, method_or_choice, help=help, default=default)

    __call__ = register
