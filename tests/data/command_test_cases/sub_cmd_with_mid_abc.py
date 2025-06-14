"""
Test case for RST documentation generation.
"""

from abc import ABC

from cli_command_parser import Command, Flag, Option, SubCommand


class Base(Command, description='test'):
    sub_cmd = SubCommand()
    foo = Option()


class Mid(Base, ABC):
    bar = Flag()


class Sub(Mid, help='do foo'):
    baz = Flag()
