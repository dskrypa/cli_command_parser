#!/usr/bin/env python

import re
from inspect import Signature
from pathlib import Path
from typing import Callable, Collection, Dict, Set
from unittest import TestCase, main

from cli_command_parser.config import CommandConfig
from cli_command_parser.core import CommandMeta

DOCS_SRC = Path(__file__).resolve().parents[2].joinpath('docs', '_src')


def get_doc_params(rst_name: str, section_start: str, section_end: str = None) -> Dict[str, str]:
    data = DOCS_SRC.joinpath(rst_name).read_text('utf-8')
    start = data.index(section_start)
    if section_end:
        end = data.index(section_end)
        content = data[start:end]
    else:
        content = data[start:]

    key_val_match = re.compile(r'^:([^:]+):(?!`)\s*(.*)$').match
    params = {}
    key = None
    val = []
    for line in map(str.strip, content.splitlines()):
        if not line:
            if key:
                params[key] = ' '.join(val)
            key = None
            continue
        if m := key_val_match(line):
            if key:
                params[key] = ' '.join(val)
            key = m.group(1)
            val = [m.group(2)]
        else:
            val.append(line)

    if key:
        params[key] = ' '.join(val)
    return params


def get_func_params(func: Callable, skip: Collection[str] = None) -> Set[str]:
    sig = Signature.from_callable(func)
    params = set(sig.parameters)
    if skip:
        return params.difference(skip)
    return params


class UserDocsTest(TestCase):
    def test_command_kwargs_up_to_date(self):
        doc_params = set(get_doc_params('configuration.rst', 'Command Metadata', 'Configuration Options'))

        # TODO: Missing url, doc_url, maybe more
        meta_kwargs = {'prog', 'usage', 'description', 'epilog', 'doc_name'}
        cmd_params = get_func_params(CommandMeta.__new__, ('mcs', 'name', 'bases', 'namespace', 'kwargs'))

        self.assertSetEqual(doc_params, cmd_params | meta_kwargs)

    def test_config_options_up_to_date(self):
        doc_params = get_doc_params('configuration.rst', 'Configuration Options')
        self.assertSetEqual(set(doc_params), CommandConfig.FIELDS)


if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    try:
        main(verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
