# Sphinx Configuration

import logging
import sys
from datetime import datetime
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]
docs_src_path = project_root.joinpath('docs_src')
sys.path.append(project_root.as_posix())
sys.path.append(docs_src_path.joinpath('ext').as_posix())

from cli_command_parser.__version__ import __author__, __version__, __description__

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
show_on_github_user = 'dskrypa'
show_on_github_repo = project_root.name

autodoc_default_options = {
    'exclude-members': '_abc_impl',
    'member-order': 'bysource',
    'special-members': '__init_subclass__',
}
autodoc_typehints_format = 'short'

templates_path = [docs_src_path.joinpath('templates').as_posix()]
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

html_theme = 'sphinx_rtd_theme'
html_theme_options = {'sticky_navigation': True}

html_static_path = [docs_src_path.joinpath('static').as_posix()]

logging.basicConfig(level=logging.INFO, format='%(message)s')
