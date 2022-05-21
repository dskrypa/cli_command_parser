"""
Sphinx extension to provide links to source on github.

:author: Doug Skrypa
"""

import logging
import warnings
from pathlib import Path

log = logging.getLogger(__name__)

URL_FMT = 'https://github.com/{user}/{repo}/blob/{branch}/{lib_relative_path}{path}'
ROOT_URL_FMT = 'https://github.com/{user}/{repo}'
OPTION_DEFAULTS = {
    'user': '',
    'repo': '',
    'branch': 'main',
    'rm_prefix': None,
    'lib_relative_path': '/',
    'use_root': ('index',),
    'skip': (),
}


def get_github_url(app, path):
    options = app.config.show_on_github_options
    return URL_FMT.format(path=path, **options)


def html_page_context(app, page_name, template_name, context, doc_tree):
    context['show_on_github_url'] = None
    if template_name != 'page.html' or not doc_tree:
        return

    options = app.config.show_on_github_options
    if not options['ok']:
        return
    elif page_name in options['use_root']:
        context['show_on_github_url'] = ROOT_URL_FMT.format(**options)
    elif page_name in options['skip']:
        log.debug(f'Skipping page_name={page_name!r}')
        return
    else:
        rst_path = Path(doc_tree.get('source'))
        rel_path = rst_path.relative_to(options['rst_src_dir']).with_suffix('')
        rel_path = rel_path.as_posix().replace('.', '/')
        rm_prefix = options.get('rm_prefix')
        if rm_prefix and rel_path.startswith(rm_prefix):
            rel_path = rel_path.replace(rm_prefix, '', 1)

        src_lib_dir = options['src_lib_dir']
        code_path = src_lib_dir.joinpath(rel_path)
        if not code_path.exists():
            rel_path += '.py'
            code_path = src_lib_dir.joinpath(rel_path)
        if not code_path.exists():
            log.warning(f'Skipping GitHub link for non-existent rel_path={rel_path!r}')
            # log.warning(f'Skipping GitHub link for non-existent {rel_path=} @ {code_path=}')
            return

        context['show_on_github_url'] = get_github_url(app, rel_path)

    log.debug('Github URL for {!r} => {}'.format(page_name, context['show_on_github_url']))


def process_config(app):
    options = app.config.show_on_github_options
    for key, val in OPTION_DEFAULTS.items():
        options.setdefault(key, val)

    lib_relative_path = options['lib_relative_path']  # type: str
    if lib_relative_path.startswith('/') and lib_relative_path != '/':
        lib_relative_path = lib_relative_path[1:]
    if not lib_relative_path.endswith('/'):
        lib_relative_path += '/'
    if lib_relative_path != options['lib_relative_path']:
        options['lib_relative_path'] = lib_relative_path

    missing = ', '.join(key for key in ('user', 'repo', 'branch') if not options.get(key))
    if missing:
        warnings.warn(f'show_on_github required conf.py settings missing: {missing}')
        options['ok'] = False
    else:
        options['ok'] = True
        options['rst_src_dir'] = rst_src_dir = Path(app.builder.srcdir)
        src_lib_dir = rst_src_dir.parents[1]
        if lib_relative_path != '/':
            src_lib_dir = src_lib_dir.joinpath(lib_relative_path)
        options['src_lib_dir'] = src_lib_dir
        log.debug(f'Using src_dir={src_lib_dir}')


def setup(app):
    app.add_config_value('show_on_github_options', OPTION_DEFAULTS, True)
    app.connect('html-page-context', html_page_context)
    app.connect('builder-inited', process_config)  # Using builder-inited instead of config-inited to get builder.srcdir
    return {'version': '1.0', 'parallel_read_safe': True}
