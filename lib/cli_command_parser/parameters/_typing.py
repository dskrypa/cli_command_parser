from __future__ import annotations

from typing import TYPE_CHECKING, Callable, TypeAlias, Union

from ..typing import D

if TYPE_CHECKING:
    from cli_command_parser.commands import Command
    from cli_command_parser.config import AllowLeadingDash


CommandMethod: TypeAlias = Callable[['Command'], D]
DefaultFunc: TypeAlias = Callable[[], D] | CommandMethod[D]

LeadingDash: TypeAlias = Union['AllowLeadingDash', str, bool]
