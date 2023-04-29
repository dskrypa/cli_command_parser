# Sphinx Configuration

import logging
import sys
from datetime import datetime
from pathlib import Path

THIS_FILE = Path(__file__).resolve()
docs_src = THIS_FILE.parent
docs_dir = THIS_FILE.parents[1]
sys.path.append(docs_dir.joinpath('_ext').as_posix())

from cli_command_parser.__version__ import __author__, __version__, __description__, __title__

project = __description__
version = release = __version__
author = __author__
copyright = '{}, {}'.format(datetime.now().strftime('%Y'), author)  # noqa

extensions = [
    'field_list_refs',
    'show_on_github',
    'sphinx.ext.autodoc',  # https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html
    'sphinx.ext.autosectionlabel',
    # 'sphinx.ext.autosummary',  # https://www.sphinx-doc.org/en/master/usage/extensions/autosummary.html
    'sphinx.ext.extlinks',
    'sphinx.ext.intersphinx',
    'sphinx.ext.viewcode',
    'sphinx_paramlinks',  # https://github.com/sqlalchemyorg/sphinx-paramlinks
]

# Extension options
autosectionlabel_prefix_document = True
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'wcwidth': ('https://wcwidth.readthedocs.io/en/latest/', None),
    'sphinx': ('https://www.sphinx-doc.org/en/master/', None),
}
extlinks = {
    'du_directives': ('https://docutils.sourceforge.io/docs/ref/rst/directives.html#%s', '%s'),
    'du_rst': ('https://docutils.sourceforge.io/docs/ref/rst/restructuredtext.html#%s', '%s'),
    'gh_examples': ('https://github.com/dskrypa/cli_command_parser/blob/main/examples/%s', '%s'),
    'gh_proj_url': ('https://github.com/dskrypa/cli_command_parser/%s', '%s'),
}
viewcode_follow_imported_members = False

_no_skip = {'examples.rst', 'api.rst'}
show_on_github_options = {
    'user': 'dskrypa',
    'repo': __title__,
    'rm_prefix': 'api/',
    'lib_relative_path': 'lib',
    'use_root': {'index', 'api'},
    'skip': {p.name for p in docs_src.glob('*.rst') if p.name not in _no_skip},
}
field_list_refs_options = {
    'skip_dirs': (docs_src.joinpath('api'), docs_src.joinpath('examples')),
}

autodoc_default_options = {
    'exclude-members': '_abc_impl',
    'member-order': 'bysource',
    'special-members': '__init_subclass__,__call__',
    'private-members': '_pre_init_actions_,_init_command_,_before_main_,_after_main_',
    'ignore-module-all': True,
}
autodoc_typehints_format = 'short'

templates_path = [docs_dir.joinpath('_templates').as_posix()]
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

html_theme = 'sphinx_rtd_theme'
html_theme_options = {'sticky_navigation': True}

# html_static_path = [docs_dir.joinpath('_static').as_posix()]

logging.basicConfig(level=logging.INFO, format='%(message)s')
