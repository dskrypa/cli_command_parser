#!/usr/bin/env python

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Iterator
from unittest import TestCase, main, skipIf

from mypy.build import build
from mypy.fscache import FileSystemCache
from mypy.main import process_options

TEST_MODULES_DIR = Path(__file__).resolve().parent.joinpath('modules')


class TestInputsTyping(TestCase):
    def assert_revealed_types_are_correct(self, name: str):
        for result in RevealedTypeChecker(name):
            with self.subTest(line=result.line, attr=result.name):
                if reason := result.failure_reason():
                    self.fail(reason)

    @skipIf(sys.version_info < (3, 13), 'Most of these pass on 3.12, but not ')
    def test_inputs(self):
        self.assert_revealed_types_are_correct('inputs.py')

    def test_all_input_types_covered(self):
        # fmt: off
        all_input_types = {
            # Directly tested types
            'ChoiceMap', 'Choices', 'File', 'Json', 'Path', 'Pickle', 'Bytes', 'NumRange', 'Range',
            'Glob', 'Regex', 'Date', 'DateTime', 'Day', 'Month', 'Time', 'TimeDelta',
            # Indirectly tested types
            'ExampleEnum',  # => EnumChoices
        }
        # fmt: on
        type_search = re.compile(r'\btype=([a-zA-Z][^\s(]+)[()]').search
        tested = set()
        for line in TEST_MODULES_DIR.joinpath('inputs.py').read_text('utf-8').splitlines():
            if m := type_search(line):
                tested.add(m.group(1))

        covered = all_input_types.intersection(tested)
        if missing := all_input_types - tested:
            total = len(all_input_types)
            self.fail(
                f'Input type coverage: {len(covered)}/{total} ({len(covered) / total:.2%})'
                f' - missing: {", ".join(sorted(missing))}'
            )


class RevealedTypeChecker:
    __slots__ = ('mod_path', 'rel_path')

    revealed_type_pat = re.compile(r'^(.+?):(\d+): note: Revealed type is "(.+)"$')
    code_pat = re.compile(r'^\s*reveal_type\(\s*(\S+)\s*\)\s{2}# (.+)$')

    def __init__(self, name: str):
        self.mod_path = TEST_MODULES_DIR.joinpath(name)
        try:
            self.rel_path = self.mod_path.relative_to(Path.cwd()).as_posix()
        except ValueError:
            self.rel_path = self.mod_path.as_posix()

    def iter_type_check_results(self) -> Iterator[TypeCheckResult]:
        revealed_types = self._get_revealed_types()
        expected_types = self._get_expected_types()
        all_line_nums = sorted(set(revealed_types) | set(expected_types))
        for line_num in all_line_nums:
            try:
                name, expected = expected_types[line_num]
            except (KeyError, TypeError):
                name = expected = None

            yield TypeCheckResult(self.rel_path, line_num, name, expected, revealed_types.get(line_num))

    __iter__ = iter_type_check_results

    def _get_mypy_messages(self) -> list[str]:
        messages = []

        def flush_errors(filename: str | None, new_messages: list[str], _serious: bool):
            if new_messages and filename == self.rel_path:
                messages.extend(new_messages)

        stdout, stderr = StringIO(), StringIO()
        fscache = FileSystemCache()
        sources, options = process_options([self.mod_path.as_posix()], stdout=stdout, stderr=stderr, fscache=fscache)
        # Replaces: res, messages, blockers = run_build(sources, options, fscache, time.time(), stdout, stderr)
        build(sources, options, None, flush_errors, fscache, stdout, stderr)
        return messages

    def _get_revealed_types(self) -> dict[int, str]:
        line_revealed_type_map = {}
        for line in self._get_mypy_messages():
            if m := self.revealed_type_pat.match(line):
                rel_path, line_num, revealed_type = m.groups()
                line_revealed_type_map[int(line_num)] = revealed_type

        return line_revealed_type_map

    def _get_expected_types(self) -> dict[int, tuple[str, str]]:
        line_expected_type_map = {}
        lines = self.mod_path.read_text('utf-8').splitlines()
        for n, line in enumerate(lines, 1):
            if m := self.code_pat.match(line):
                line_expected_type_map[n] = m.group(1), m.group(2)

        return line_expected_type_map


@dataclass(slots=True)
class TypeCheckResult:
    source: str
    line: int
    name: str | None
    expected: str | None
    revealed: str | None

    def _item(self) -> str:
        return f'{self.name!r} @ {self.source}:{self.line}'

    def failure_reason(self) -> str | None:
        """If the type check passed, then None is returned, otherwise, a string describing why it failed is returned."""
        if self.expected is None:
            return f'Unexpected revealed type found at {self.source}:{self.line}'
        elif self.revealed is None:
            return f'No type was found for {self._item()}'
        elif self.expected != self.revealed:
            return f'Type mismatch for {self._item()}: expected={self.expected!r}, revealed={self.revealed!r}'

        return None


if __name__ == '__main__':
    try:
        main(verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
