# Sphinx Configuration

import logging
import sys
from datetime import datetime
from pathlib import Path

docs_dir = Path(__file__).resolve().parents[1]
sys.path.append(docs_dir.joinpath('_ext').as_posix())

from cli_command_parser.__version__ import __author__, __version__, __description__, __title__

project = __description__
release = __version__
author = __author__
copyright = '{}, {}'.format(datetime.now().strftime('%Y'), author)

extensions = [
    'sphinx.ext.intersphinx',
    'sphinx.ext.autodoc',  # https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html
    'sphinx.ext.viewcode',
    # 'sphinx.ext.autosummary',  # https://www.sphinx-doc.org/en/master/usage/extensions/autosummary.html
    'sphinx_paramlinks',  # https://github.com/sqlalchemyorg/sphinx-paramlinks
    'show_on_github',
]

# Extension options
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
}
viewcode_follow_imported_members = False
show_on_github_options = {
    'user': 'dskrypa',
    'repo': __title__,
    'rm_prefix': 'api/',
    'lib_relative_path': 'lib',
    'use_root': {'index', 'api'},
    'skip': {'advanced', 'basic', 'parameters'},
}

autodoc_default_options = {
    'exclude-members': '_abc_impl',
    'member-order': 'bysource',
    'special-members': '__init_subclass__,__call__,__new__,__init__,_before_main_,_after_main_',
}
autodoc_typehints_format = 'short'

templates_path = [docs_dir.joinpath('_templates').as_posix()]
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

html_theme = 'sphinx_rtd_theme'
html_theme_options = {'sticky_navigation': True}

# html_static_path = [docs_dir.joinpath('_static').as_posix()]

logging.basicConfig(level=logging.INFO, format='%(message)s')
