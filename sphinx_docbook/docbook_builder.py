# -*- coding: utf-8 -*-
################################################################################
"""
A module for docutils that converts from a doctree to DocBook output.

Originally Written by Eron Hennessey
Updated for Python3 by Joe Stanley
"""
################################################################################

import os
import sys
from docutils.core import publish_from_doctree
from sphinx.builders.text import TextBuilder
from sphinx_docbook.docbook_writer import DocBookWriter

class DocBookBuilder(TextBuilder):
    """Build DocBook documents from a Sphinx doctree"""
    # pylint: disable=attribute-defined-outside-init

    name = 'docbook'

    def process_with_template(self, contents):
        """Process the results with a moustache-style template.

        The template variables can be specified as {{data.root_element}} and
        {{data.contents}}. You can use this to create a custom DocBook header
        for your final output."""
        try:
            import jinja2
        except ImportError:
            sys.stderr.write(
                "DocBookBuilder -- Jinja2 is not installed: can't use template!"
                "\n"
            )
            sys.exit(1)

        full_template_path = os.path.join(
            sphinx_app.env.srcdir,
            sphinx_app.config.docbook_template_file
        )

        if not os.path.exists(full_template_path):
            sys.stderr.write(
                "DocBookBuilder -- "
                f"template file doesn't exist: {full_template_path}\n"
            )
            sys.exit(1)

        data = { 'root_element': self.root_element,
                 'contents': contents }

        jinja2env = jinja2.Environment(
                loader=jinja2.FileSystemLoader(sphinx_app.env.srcdir),
                trim_blocks=True)

        try:
            template = jinja2env.get_template(self.template_filename)
            template.render(data=data)
        #pylint: disable=bare-except
        except:
            sys.stderr.write(
                "DocBookBuilder -- "
                f"template file doesn't exist: {full_template_path}\n"
            )
            sys.exit(1)
        #pylint: enable=bare-except

        return template.render(data=data)


    def get_target_uri(self, docname, typ=None):
        return f'./{docname}.xml'

    def prepare_writing(self, docnames):
        self.root_element = sphinx_app.config.docbook_default_root_element
        self.template_filename = sphinx_app.config.docbook_template_file

    def write_doc(self, docname, doctree):

        # If there's an output filename, use its basename as the root
        # element's ID.
        #(path, filename) = os.path.split(self.output_filename)
        #(doc_id, ext) = os.path.splitext(filename)

        docutils_writer = DocBookWriter(
            root_element=self.root_element,
            document_id=docname,
            output_xml_header=(self.template_filename == None),
            use_xml_id_in_titles=sphinx_app.config.docbook_use_xml_id_in_titles,
        )

        # get the docbook output.
        docbook_contents = publish_from_doctree(
            doctree,
            writer=docutils_writer
        )

        # process the output with a template if a template name was supplied.
        if self.template_filename is not None:
            docbook_contents = self.process_with_template(docbook_contents)

        out_path = os.path.join(self.outdir, f'{docname}.xml')
        with open(out_path, 'w+', encoding="utf-8") as output_file:
            output_file.write(docbook_contents.decode('utf-8'))


def setup(app):
    # pylint: disable=global-variable-undefined, invalid-name
    global sphinx_app
    sphinx_app = app
    # pylint: enable=global-variable-undefined, invalid-name
    app.add_config_value('docbook_default_root_element', 'section', 'env')
    app.add_config_value('docbook_template_file', None, 'env')
    app.add_config_value('docbook_use_xml_id_in_titles', False, 'env')
    app.add_builder(DocBookBuilder)
