from enum import Enum
from typing import reveal_type

from cli_command_parser import Command, Flag, Option, ParamGroup, Positional, TriFlag
from cli_command_parser.inputs import ChoiceMap, Choices, File, Glob, Json, Path, Pickle, Regex, RegexMode
from cli_command_parser.inputs.numeric import Bytes, NumRange, Range
from cli_command_parser.inputs.time import Date, DateTime, Day, DTFormatMode, Month, Time, TimeDelta


class ExampleEnum(Enum):
    FOO = 'foo'
    BAR = 'bar'
    BAZ = 'baz'


class InputsExample(Command):
    positional = Positional()
    positional_int = Positional(type=int)
    optional_positional = Positional(nargs='?')
    required = Option(required=True)
    required_int = Option(required=True, type=int)

    with ParamGroup('Files / Serialization'):
        path = Option(type=Path(exists=True, type='file'))
        in_file = Option(type=File(allow_dash=True, lazy=False))
        out_file = Option(type=File(allow_dash=True, mode='w'))
        json = Option(type=Json(allow_dash=True))
        eager_json = Option(type=Json(allow_dash=True, lazy=False))
        pickle_lazy = Option(type=Pickle())
        pickle_eager = Option(type=Pickle(lazy=False))

    with ParamGroup('Numeric'):
        enum = Option(type=ExampleEnum)
        integer = Option(type=int)
        integers = Option(nargs='+', type=int)
        ints_with_choices = Option(nargs='+', type=int, choices=(1, 2, 3))
        bytes = Option(type=Bytes())
        bytes_float = Option(type=Bytes(fractions=True))

    with ParamGroup('Ranges'):
        range_input = Option(type=Range(50))
        float_range = Option(type=Range(10, type=float))
        float_num_range = Option(type=NumRange(float, min=0, max=1))
        implied_float_num_range = Option(type=NumRange(min=0.0))
        range_choices = Option(choices=range(20))
        # The next one doesn't work, but it probably never should have been implemented to work
        # range_type = Option(type=range(1, 30, 2))

    with ParamGroup('Date / Time'):
        day_str = Option(type=Day())
        day_abbr = Option(type=Day(out_format='abbreviation'))
        day_int = Option(type=Day(out_format=DTFormatMode.NUMERIC))
        month_str = Option(type=Month())
        month_int = Option(type=Month(out_format='numeric'))
        time_delta = Option(type=TimeDelta('seconds'))
        date_time = Option(type=DateTime())
        date_time_req = Option(type=DateTime(), required=True)
        date_times = Option(nargs='+', type=DateTime())
        date = Option(type=Date())
        time = Option(type=Time())

    with ParamGroup('Flags'):
        flag = Flag()
        flag_str = Flag(default='A', const='B')
        tri_flag = TriFlag()

    with ParamGroup('Choices'):
        choices_str = Option(type=Choices(['a', 'b']))
        choices_int = Option(type=Choices([1, 2], type=int))
        choice_map_str_str = Option(type=ChoiceMap({'a': 'b'}))
        choice_map_str_int = Option(type=ChoiceMap({'a': 1}))
        choice_map_int_str = Option(type=ChoiceMap({1: 'a'}, type=int))
        choice_map_int_int = Option(type=ChoiceMap({1: 2}, type=int))

    with ParamGroup('Patterns'):
        glob = Option(type=Glob('*.yml'))
        regex = Option(type=Regex('foo.*bar'))
        regex_group = Option(type=Regex('foo.*bar', mode='group'))
        regex_groups = Option(type=Regex('foo.*bar', mode='groups'))
        regex_match = Option(type=Regex('foo.*bar', mode=RegexMode.MATCH))
        regex_dict = Option(type=Regex('foo.*bar', mode=RegexMode.DICT))
        # The next one doesn't work, but it probably never should have been implemented to work
        # regex_converted = Option(type=re.compile('foo.*bar'))

    with ParamGroup('Complex'):
        ints_default_list = Option(nargs='+', type=int, default=[1])
        ints_default_set = Option(nargs='+', type=int, default={1, 2})
        ints_default_set_strict = Option(nargs='+', type=int, default={1, 2}, strict_default=True)
        ints_default_single = Option(nargs='+', type=int, default=1)
        mixed_types_default_single = Option(nargs='+', default=1)
        # The next two don't work, but it would be a relatively strange use case to need
        # mixed_types_default_list = Option(nargs='+', default=[1])
        # mixed_types_default_tuple = Option(nargs='+', default=(1,))

    def main(self) -> None:
        reveal_type(self.positional)  # str
        reveal_type(self.positional_int)  # int
        reveal_type(self.required)  # str
        reveal_type(self.required_int)  # int

        reveal_type(self.path)  # pathlib.Path | None
        reveal_type(self.in_file)  # str | None
        reveal_type(self.out_file)  # cli_command_parser.inputs.utils.FileWrapper[str] | None
        reveal_type(self.json)  # cli_command_parser.inputs.utils.SerializedFileWrapper[str] | None
        reveal_type(self.eager_json)  # Any | None
        reveal_type(self.pickle_lazy)  # cli_command_parser.inputs.utils.SerializedFileWrapper[bytes] | None
        reveal_type(self.pickle_eager)  # Any | None

        reveal_type(self.enum)  # tests.test_typing.modules.inputs.ExampleEnum | None
        reveal_type(self.integer)  # int | None
        reveal_type(self.integers)  # list[int]
        reveal_type(self.ints_with_choices)  # list[int]
        reveal_type(self.bytes)  # int | None
        reveal_type(self.bytes_float)  # float | None

        reveal_type(self.range_input)  # int | None
        reveal_type(self.float_range)  # float | None
        reveal_type(self.float_num_range)  # float | None
        reveal_type(self.implied_float_num_range)  # float | None
        reveal_type(self.range_choices)  # int | None
        # reveal_type(self.range_type)  # int | None

        reveal_type(self.day_str)  # str | None
        reveal_type(self.day_abbr)  # str | None
        reveal_type(self.day_int)  # int | None
        reveal_type(self.month_str)  # str | None
        reveal_type(self.month_int)  # int | None
        reveal_type(self.time_delta)  # datetime.timedelta | None
        reveal_type(self.date_time)  # datetime.datetime | None
        reveal_type(self.date_time_req)  # datetime.datetime
        reveal_type(self.date_times)  # list[datetime.datetime]
        reveal_type(self.date)  # datetime.date | None
        reveal_type(self.time)  # datetime.time | None

        reveal_type(self.flag)  # bool
        reveal_type(self.flag_str)  # str
        reveal_type(self.tri_flag)  # bool | None

        reveal_type(self.choices_str)  # str | None
        reveal_type(self.choices_int)  # int | None
        reveal_type(self.choice_map_str_str)  # str | None
        reveal_type(self.choice_map_str_int)  # int | None
        reveal_type(self.choice_map_int_str)  # str | None
        reveal_type(self.choice_map_int_int)  # int | None

        reveal_type(self.glob)  # str | None
        reveal_type(self.regex)  # str | None
        reveal_type(self.regex_group)  # str | None
        reveal_type(self.regex_groups)  # tuple[str, ...] | None
        reveal_type(self.regex_match)  # re.Match[str] | None
        reveal_type(self.regex_dict)  # dict[str, str] | None
        # reveal_type(self.regex_converted)  # str | None

        reveal_type(self.ints_default_list)  # list[int]
        reveal_type(self.ints_default_set)  # list[int]
        reveal_type(self.ints_default_set_strict)  # list[int] | set[int]
        reveal_type(self.ints_default_single)  # list[int]
        reveal_type(self.mixed_types_default_single)  # list[str] | list[int]
        # reveal_type(self.mixed_types_default_list)  # list[str] | list[int]
        # reveal_type(self.mixed_types_default_tuple)  # list[str] | list[int]
