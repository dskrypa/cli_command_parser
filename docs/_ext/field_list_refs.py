"""
Sphinx extension to add :ref: link targets for field list names.

Intended use case is for manually written documentation, not autodoc/automodule docs, which are not handled well.

:author: Doug Skrypa
"""

from pathlib import Path
from typing import Any, Dict

from docutils.nodes import field_name as FieldName, document as Document, fully_normalize_name
from sphinx.application import Sphinx
from sphinx.domains.std import StandardDomain
from sphinx.util import logging
from sphinx.util.nodes import clean_astext

log = logging.getLogger(__name__)
OPTION_DEFAULTS = {'skip_dirs': ()}


def register_field_list_names_as_labels(app: Sphinx, document: Document) -> None:
    rst_src_path = Path(document['source'])
    options = app.config.field_list_refs_options
    for skip_dir in options['skip_dirs']:  # type: Path
        if is_relative_to(rst_src_path, skip_dir):
            log.debug(f'Skipping field list name processing for {rst_src_path.as_posix()}')
            return

    domain = app.env.get_domain('std')  # type: StandardDomain  # noqa
    doc_name = app.env.docname

    for node in document.findall(FieldName):  # noqa
        section = node.parent.parent.parent
        section_name = clean_astext(section[0])
        # field_name = node.astext()
        field_name = clean_astext(node)

        label_id = fully_normalize_name(f'{section_name}:{field_name}')
        label_name = fully_normalize_name(f'{doc_name}:{section_name}:{field_name}')
        node['ids'].append(label_id)

        try:
            orig_doc, orig_label, orig_section = domain.labels[label_name]
        except KeyError:
            pass
        else:
            orig_path = app.env.doc2path(orig_doc)
            log.warning(
                f'duplicate label {label_name}, other instance in {orig_path}',
                location=node,
                type='field_list_refs',
                subtype=doc_name,
            )

        domain.anonlabels[label_name] = (doc_name, label_id)
        domain.labels[label_name] = (doc_name, label_id, field_name)  # doc, html id to link to, default link text


def is_relative_to(a: Path, b: Path) -> bool:
    # Would use Path.is_relative_to, but it was added in 3.9, so this maintains 3.7 compatibility
    try:
        a.relative_to(b)
    except ValueError:
        return False
    return True


def process_config(app: Sphinx, config):
    options = config.field_list_refs_options
    for key, val in OPTION_DEFAULTS.items():
        options.setdefault(key, val)

    options['skip_dirs'] = [Path(skip_dir).resolve() for skip_dir in options['skip_dirs']]


def setup(app: Sphinx) -> Dict[str, Any]:
    app.add_config_value('field_list_refs_options', OPTION_DEFAULTS, True)
    app.connect('doctree-read', register_field_list_names_as_labels)
    app.connect('config-inited', process_config)
    return {'version': '1.0', 'parallel_read_safe': True, 'parallel_write_safe': True}
