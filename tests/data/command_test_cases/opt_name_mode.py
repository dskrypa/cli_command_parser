from cli_command_parser import Command, SubCommand, Flag, TriFlag


class Base(Command, option_name_mode='-'):
    sub_cmd = SubCommand()


class Foo(Base):
    a_b = Flag()
    a_c = TriFlag()
