"""
Command Parser

:author: Doug Skrypa
"""

from .commands import AsyncCommand, Command, main
from .config import (
    AllowLeadingDash,
    AmbiguousComboMode,
    CommandConfig,
    OptionNameMode,
    ShowDefaults,
    SubcommandAliasHelpMode,
)
from .context import Context, ctx, get_context, get_current_context, get_parsed, get_raw_arg
from .error_handling import ErrorHandler, error_handler, extended_error_handler, no_exit_handler
from .exceptions import (
    AmbiguousParseTree,
    BadArgument,
    CommandDefinitionError,
    CommandParserException,
    InvalidChoice,
    MissingArgument,
    NoActiveContext,
    NoSuchOption,
    ParamConflict,
    ParameterDefinitionError,
    ParamsMissing,
    ParamUsageError,
    ParserExit,
    TooManyArguments,
    UsageError,
)
from .formatting.commands import get_formatter
from .nargs import REMAINDER
from .parameters import (
    Action,
    ActionFlag,
    BaseOption,
    BasePositional,
    Counter,
    Flag,
    Option,
    Parameter,
    ParamGroup,
    PassThru,
    Positional,
    SubCommand,
    TriFlag,
    action_flag,
    after_main,
    before_main,
)
from .typing import Param, ParamOrGroup
