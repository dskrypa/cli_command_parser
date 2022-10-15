#!/usr/bin/env python

from typing import TYPE_CHECKING

from cli_command_parser import Command, Option, inputs

if TYPE_CHECKING:
    from pathlib import Path


class AnnotatedCommand(Command):
    paths_a: 'Path' = Option()
    paths_b: 'Path' = Option(type=inputs.Path(type='file', exists=True))
