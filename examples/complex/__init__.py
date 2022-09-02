"""
Simplified example of a complex set of Commands defined across multiple modules.

The expected / intended use case would be for a program that would define an entry point like the following::

    complex_example.py = examples.complex:main


Any number of additional modules could be used, as long as they are imported in the package's ``__init__.py`` with the
base Command so that the base Command is made aware of the presence of the subcommands.

:author: Doug Skrypa
"""

from cli_command_parser import main  # noqa

from .base import Example
from .additional_commands import HelloWorld, Logs
