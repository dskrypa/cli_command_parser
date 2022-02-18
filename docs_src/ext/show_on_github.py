"""
Sphinx extension to provide links to source on github.

:author: Doug Skrypa
"""

import logging
import warnings
from pathlib import Path

log = logging.getLogger(__name__)

URL_FMT = 'https://github.com/{user}/{repo}/blob/{branch}/lib/{path}'
INDEX_URL_FMT = 'https://github.com/{user}/{repo}'


def get_github_url(app, path):
    return URL_FMT.format(
        user=app.config.show_on_github_user,
        repo=app.config.show_on_github_repo,
        branch=app.config.show_on_github_branch,
        path=path,
    )


def html_page_context(app, pagename, templatename, context, doctree):
    context['show_on_github_url'] = None
    if templatename != 'page.html' or not doctree:
        return
    missing = [key for key in ('user', 'repo', 'branch') if not getattr(app.config, 'show_on_github_{}'.format(key))]
    if missing:
        missing = ', '.join('show_on_github_{}'.format(key) for key in missing)
        warnings.warn('show_on_github required conf.py settings missing: {}'.format(missing))
        return
    if pagename == 'index':
        context['show_on_github_url'] = INDEX_URL_FMT.format(
            user=app.config.show_on_github_user, repo=app.config.show_on_github_repo
        )
    else:
        rst_src_dir = Path(app.builder.srcdir)
        src_dir = rst_src_dir.parent.joinpath('lib')
        rst_path = Path(doctree.get('source'))
        rel_path = rst_path.relative_to(rst_src_dir).with_suffix('')
        rel_path = rel_path.as_posix().replace('.', '/')

        log.debug('Using src_dir={}'.format(src_dir))
        if not src_dir.joinpath(rel_path).exists():
            rel_path += '.py'
        if not src_dir.joinpath(rel_path).exists():
            log.warning('Skipping non-existant path: {}'.format(rel_path))
            # log.warning('Skipping non-existant path: {}'.format(src_dir.joinpath(rel_path)))
            return
        context['show_on_github_url'] = get_github_url(app, rel_path)

    log.debug('Github URL for {!r} => {}'.format(pagename, context['show_on_github_url']))


def setup(app):
    app.add_config_value('show_on_github_user', '', True)
    app.add_config_value('show_on_github_repo', '', True)
    app.add_config_value('show_on_github_branch', 'main', True)
    app.connect('html-page-context', html_page_context)
    return {'version': '1.0', 'parallel_read_safe': True}
