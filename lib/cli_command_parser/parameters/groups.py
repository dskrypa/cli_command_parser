"""
Parameter Groups

:author: Doug Skrypa
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Iterable, Iterator, Tuple, List

from ..context import ctx
from ..exceptions import ParameterDefinitionError, CommandDefinitionError, ParamConflict, ParamsMissing
from .base import ParamBase, BasePositional, BaseOption, _group_stack
from .pass_thru import PassThru

if TYPE_CHECKING:
    from ..typing import Bool, ParamList, ParamOrGroup

__all__ = ['ParamGroup']


class ParamGroup(ParamBase):
    """
    A group of parameters.  Intended to be used as a context manager, where group members are defined inside the
    ``with`` block.  Allows arbitrary levels of nesting, including mutually dependent groups inside mutually exclusive
    groups, and vice versa.

    :param name: The name of this group, to appear in help messages.
    :param description: A brief description for this group, to appear in help messages.
    :param mutually_exclusive: ``True`` if parameters in this group are mutually exclusive, ``False`` otherwise.
      I.e., if one parameter in this group is provided, then no other parameter in this group will be allowed.
      Cannot be combined with ``mutually_dependent``.
    :param mutually_dependent: ``True`` if parameters in this group are mutually dependent, ``False`` otherwise.
      I.e., if one parameter in this group is provided, then all other parameters in this group must also be
      provided.  Cannot be combined with ``mutually_exclusive``.
    :param required: Whether at least one parameter in this group is required or not.  If it is required, then an
      exception will be raised if the user did not provide a value for any parameters in this group.  Defaults to
      ``False``.
    :param hide: If ``True``, this group of parameters will not be included in usage / help messages.  Defaults to
      ``False``.
    """

    description: Optional[str]
    members: List[ParamOrGroup]
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

    # region Boilerplate Methods

    def __repr__(self) -> str:
        exclusive, dependent = str(self.mutually_exclusive)[0], str(self.mutually_dependent)[0]
        members = len(self.members)
        return (
            f'<{self.__class__.__name__}[{self.name!r},'
            f' members={members!r}, m.exclusive={exclusive}, m.dependent={dependent}]>'
        )

    def __hash__(self) -> int:
        return super().__hash__()

    def __eq__(self, other: ParamGroup) -> bool:
        if isinstance(other, ParamGroup) and self.group == other.group:
            attrs = ('mutually_exclusive', 'mutually_dependent', 'name', 'description', 'members')
            return all(getattr(self, a) == getattr(other, a) for a in attrs)
        return False

    def __lt__(self, other: ParamGroup) -> bool:
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

    def __contains__(self, param: ParamOrGroup) -> bool:
        """
        Returns True if the given :class:`Parameter` or :class:`ParamGroup` is a member of this group, False otherwise.
        """
        return param in self.members

    def __iter__(self) -> Iterator[ParamOrGroup]:
        yield from self.members

    # endregion

    # region Active Group Methods

    def __enter__(self) -> ParamGroup:
        """
        A ParamGroup can be used as a context manager, where all Parameters (and ParamGroups) defined inside the
        ``with`` block will be registered as members of that group.
        """
        _group_stack.get().append(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        _group_stack.get().pop()

    # endregion

    # region Membership Methods

    def add(self, param: ParamOrGroup):
        """Add the given parameter without storing a back-reference.  Primary use case is for help text only groups."""
        self.members.append(param)

    def extend(self, params: Iterable[ParamOrGroup]):
        """Add the given parameters without storing a back-reference.  Primary use case is for help text only groups."""
        self.members.extend(params)

    def register(self, param: ParamOrGroup):
        if self.mutually_exclusive:
            if (isinstance(param, BasePositional) and 0 not in param.nargs) or isinstance(param, PassThru):
                cls_name = param.__class__.__name__
                raise CommandDefinitionError(
                    f'Cannot add param={param!r} to {self} - {cls_name} parameters cannot be mutually exclusive'
                )
            elif isinstance(param, BaseOption) and param.required:
                raise CommandDefinitionError(
                    f'Cannot add param={param!r} to {self} - required parameters cannot be mutually exclusive'
                    ' (but the group can be required)'
                )

        self.members.append(param)
        param.group = self

    def register_all(self, params: Iterable[ParamOrGroup]):
        for param in params:
            self.register(param)

    # endregion

    # region Argument Handling

    def _categorize_params(self) -> Tuple[ParamList, ParamList]:
        """Called after parsing to group this group's members by whether they were provided or not."""
        provided = []
        missing = []
        for obj in self.members:
            if ctx.num_provided(obj):
                provided.append(obj)
            else:
                missing.append(obj)

        return provided, missing

    def _check_conflicts(self, provided: ParamList, missing: ParamList):
        """
        Validates that the provided / missing parameters are acceptable based on the mutual exclusivity / dependency
        configured for this group.

        :raises: :class:`.ParamsMissing` if this is a :paramref:`.ParamGroup.mutually_dependent` group and some but not
          all members were provided.
        :raises: :class:`.ParamConflict` if this is a :paramref:`.ParamGroup.mutually_exclusive` group and multiple
          members were provided.
        """
        if not (self.mutually_dependent or self.mutually_exclusive):
            return

        # log.debug(f'{self}: Checking group conflicts in {provided=}, {missing=}')
        # log.debug(f'{self}: Checking group conflicts in provided={len(provided)}, missing={len(missing)}')
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

    # endregion

    # region Usage / Help Text

    @property
    def contains_positional(self) -> bool:
        # Used by the help text formatter when grouping parameters / groups
        return any(isinstance(p, BasePositional) for p in self)

    @property
    def show_in_help(self) -> bool:
        if self.hide or not self.members:
            return False
        elif self.group is not None:
            return self.group.show_in_help
        return True

    # endregion
