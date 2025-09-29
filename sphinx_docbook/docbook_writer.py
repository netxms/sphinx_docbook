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

from docutils import nodes, writers

import lxml.etree as etree


def _print_error(text, node = None):
    """Prints an error string and optionally, the node being worked on."""
    sys.stderr.write(f'\n{__name__}: {text}\n')
    if node:
        sys.stderr.write(f"  {node}\n")

_NAMESPACE_ID = '{http://www.w3.org/XML/1998/namespace}id'

class DocBookWriter(writers.Writer):
    """
    A docutils writer for DocBook.

    Parameters
    ----------
    root_element:       str
                        The root element which Docbook builder should utilize.
    document_id:        str, optional
                        Identifying name of the document.
    output_xml_header:  bool, optional
                        Use the builtin XML header information (default).
    kwargs:             dict[str, str], optional
                        Dictionary of additional controls for adjusting XML
                        generation.
    """
    # pylint: disable=attribute-defined-outside-init

    def __init__(
        self,
        root_element: str,
        document_id: str = None,
        output_xml_header: bool = True,
        **kwargs,
    ):
        """Initialize the writer. Takes the root element of the resulting
        DocBook output as its sole argument."""
        writers.Writer.__init__(self)
        self.document_type = root_element
        self.document_id = document_id
        self.output_xml_header = output_xml_header
        self._kwargs = kwargs

    def translate(self):
        """Call the translator to translate the document."""
        self.visitor = DocBookTranslator(
            self.document,
            self.document_type,
            self.document_id,
            self.output_xml_header,
            **self._kwargs,
        )
        self.document.walkabout(self.visitor)
        self.output = self.visitor.astext()
        self.fields = self.visitor.fields


class DocBookTranslator(nodes.NodeVisitor):
    """A docutils translator for DocBook."""
    # pylint: disable=missing-function-docstring, unnecessary-pass
    # pylint: disable=unused-argument

    def __init__(
        self,
        document,
        document_type: str,
        document_id: str = None,
        output_xml_header: bool = True,
        **kwargs,
    ):
        """Initialize the translator. Takes the root element of the resulting
        DocBook output as its sole argument."""
        nodes.NodeVisitor.__init__(self, document)
        self.settings = document.settings
        self.content = []
        self.document_type = document_type
        self.document_id = document_id
        self.in_first_section = False
        self.output_xml_header = output_xml_header
        self._kwargs = kwargs

        self.in_pre_block = False
        self.in_figure = False
        self.in_glossary = False
        self.next_element_id = None

        self.description_type = None
        self._auto_summary_node = None

        # self.estack is a stack of etree nodes. The bottom of the stack should
        # always be the base element (the document). The top of the stack is
        # the element currently being processed.
        self.estack = []
        self.tb = etree.TreeBuilder()
        self.fields = {}
        self.current_field_name = None
        self.nsmap = {
            'xml': 'http://www.w3.org/XML/1998/namespace',
            'xlink': 'http://www.w3.org/1999/xlink',
            'xi': 'http://www.w3.org/2001/XInclude',
            'svg': 'http://www.w3.org/2000/svg',
            'xhtml': 'http://www.w3.org/1999/xhtml',
            'mathml': 'http://www.w3.org/1998/Math/MathML',
            None: 'http://docbook.org/ns/docbook'
        }

        self.SkipNode = nodes.SkipNode

    #
    # functions used by the translator.
    #

    def astext(self):
        doc = self.tb.close()
        et = etree.ElementTree(doc)
        if self.output_xml_header:
            rep = etree.tostring(et, encoding="utf-8", standalone=True,
                    pretty_print=True)
        else:
            rep = etree.tostring(et, encoding="utf-8", pretty_print=True)
        return rep


    def _sanitize_xml_text(self, text):
        """Sanitize text content for XML compatibility."""
        if text is None:
            return ''
        
        text_str = str(text)
        
        # Check if text contains invalid XML characters
        if '\x00' in text_str or any(ord(c) < 32 and c not in '\t\n\r' for c in text_str):
            # print(f"DEBUG: Found invalid XML characters in text: {repr(text_str)}")
            # Remove or replace invalid characters
            sanitized = ''.join(c if ord(c) >= 32 or c in '\t\n\r' else '' for c in text_str if c != '\x00')
            # print(f"DEBUG: Sanitized text: {repr(sanitized)}")
            return sanitized
        
        return text_str

    def _add_element_title(self, title_name, title_attribs = None):
        """Add a title to the current element."""
        if title_attribs is None:
            title_attribs = {}
        self._push_element('title', title_attribs)
        sanitized_title = self._sanitize_xml_text(title_name)
        self.tb.data(sanitized_title)
        return self._pop_element()


    def _push_element(self, name, attribs = None):
        if attribs is None:
            attribs = {}
        if self.next_element_id:
            attribs[
                '{http://www.w3.org/XML/1998/namespace}id'
            ] = self.next_element_id
            self.next_element_id = None
        elif (('{http://www.w3.org/XML/1998/namespace}id' in attribs) and
            (attribs['{http://www.w3.org/XML/1998/namespace}id'] is None)):
            del attribs['{http://www.w3.org/XML/1998/namespace}id']
        try:
            e = self.tb.start(name, attribs, self.nsmap)
        except Exception as err:
            raise err
        self.estack.append(e)
        return e


    def _pop_element(self):
        e = self.estack.pop()
        try:
            return self.tb.end(str(e.tag))
        except ValueError as err:
            message = (
                f"{str(err)}\nTag Information: "
                f"{e.tag} :: {type(e.tag)} :: {len(e.tag)}"
            )
            raise ValueError(message) from err


    #
    # The document itself
    #

    def visit_document(self, node):
        """Create the document itself."""
        pass


    def depart_document(self, node):
        pass

    #
    # document parts
    #

    def visit_Text(self, node):
        sanitized_text = self._sanitize_xml_text(node)
        self.tb.data(sanitized_text)


    def depart_Text(self, node):
        pass

    def visit_paragraph(self, node):
        if self.current_field_name is None:
            self._push_element('para')


    def depart_paragraph(self, node):
        if self.current_field_name is None:
            try:
                self._pop_element()
            except ValueError as err:
                print(node)
                raise err

    def visit_compact_paragraph(self, node):
        self.visit_paragraph(node)


    def depart_compact_paragraph(self, node):
        self.depart_paragraph(node)


    def visit_section(self, node):
        attribs = {}
        # Do something special if this is the very first section in the
        # document.
        if self.in_first_section == False:
            node['ids'][0] = self.document_id
            self._push_element(
                self.document_type,
                {
                    '{http://www.w3.org/XML/1998/namespace}id': self.document_id,
                    'version': '5.0'
                }
            )
            self.in_first_section = True
            return

        if self.next_element_id:
            node['ids'][0] = self.next_element_id
            attribs[
                '{http://www.w3.org/XML/1998/namespace}id'
            ] = self.next_element_id
            self.next_element_id = None
        else:
            if len(node['ids']) > 0:
                attribs[
                    '{http://www.w3.org/XML/1998/namespace}id'
                ] = node['ids'][0]

        self._push_element('section', attribs)
        # TODO - Collect other attributes.


    def depart_section(self, node):
        self._pop_element()


    def visit_block_quote(self, node):
        self._push_element('blockquote')


    def depart_block_quote(self, node):
        self._pop_element()



    def visit_abstract(self, node):
        self._push_element('abstract')


    def depart_abstract(self, node):
        self._pop_element()


    def visit_desc(self, node):
        attribs = {}
        self.description_type = node.get("desctype")
        next_node = node.next_node()

        if self.next_element_id:
            node['ids'][0] = self.next_element_id
            attribs[
                '{http://www.w3.org/XML/1998/namespace}id'
            ] = self.next_element_id
            self.next_element_id = None
        else:
            if len(node['ids']) > 0:
                attribs[
                    '{http://www.w3.org/XML/1998/namespace}id'
                ] = node['ids'][0]
            elif len(next_node['ids']) > 0:
                attribs[
                    '{http://www.w3.org/XML/1998/namespace}id'
                ] = next_node['ids'][0]

        self._push_element('section', attribs=attribs)


    def depart_desc(self, node):
        # Pop the Autodoc Description if Applicable
        if self._auto_summary_node is not None:
            self.depart_autosummary_table(self._auto_summary_node, opt=True)
            self._auto_summary_node = None
        self._pop_element()

    def visit_desc_signature(self, node):
        #self._push_element('desc_signature')
        pass

    def depart_desc_signature(self, node):
        #self._pop_element()
        pass


    def visit_desc_annotation(self, node):
        # ignore description annotation in the output.
        #self._push_element('desc_annotation')
        _print_error("ignoring description annotation:", node)
        raise nodes.SkipNode

    def depart_desc_annotation(self, node):
        #self._pop_element()
        pass


    def visit_desc_addname(self, node):
        # ignore description addname in the output.
        #self._push_element('desc_addname')
        _print_error("ignoring description addname:", node)
        raise nodes.SkipNode

    def depart_desc_addname(self, node):
        #self._pop_element()
        pass


    def visit_desc_name(self, node):
        if isinstance(self.description_type, str):
            next_node = str(node.next_node())
            node.pop()
            # Sanitize the text before creating the Text node
            sanitized_text = self._sanitize_xml_text(f"{next_node} ({self.description_type.title()})")
            node.append(
                nodes.Text(sanitized_text)
            )
        self.visit_title(node=node)

    def depart_desc_name(self, node):
        self.description_type = None # Reset
        self._pop_element()


    def visit_desc_parameterlist(self, node):
        attribs = {}
        if len(node['ids']) > 0:
            attribs[_NAMESPACE_ID] = node['ids'][0]
        elif len(node.parent['ids']) > 0:
            # If the parent node has an ID, we can use that and add
            # '.title' at the end to make a deterministic title ID.
            attribs[_NAMESPACE_ID] = f"{node.parent['ids'][0]}.parameters"
        self._push_element('section', attribs=attribs)
        # Add the Title to the Parameter List
        self.visit_title(node=node)
        self.visit_Text(node=nodes.Text("Constructor Parameters"))
        self._pop_element()
        self._push_element('variablelist')

    def depart_desc_parameterlist(self, node):
        self._pop_element()
        self._pop_element()


    def visit_desc_parameter(self, node):
        self._push_element('varlistentry')

    def depart_desc_parameter(self, node):
        self._pop_element()


    def visit_desc_content(self, node):
        #self._push_element('desc_content')
        pass

    def depart_desc_content(self, node):
        #self._pop_element()
        pass


    def visit_literal_emphasis(self, node):
        self._push_element('literal_emphasis')

    def depart_literal_emphasis(self, node):
        self._pop_element()


    def visit_rubric(self, node):
        _print_error("ignoring rubric:", node)
        raise nodes.SkipNode

    def depart_rubric(self, node):
        pass


    def visit_doctest_block(self, node):
        self._push_element('doctest_block')

    def depart_doctest_block(self, node):
        self._pop_element()


    def visit_tabular_col_spec(self, node):
        _print_error("ignoring tabular column spec:", node)
        raise nodes.SkipNode
        #self._push_element('tabular_col_spec')

    def depart_tabular_col_spec(self, node):
        pass


    def visit_autosummary_table(self, node):
        self.visit_section(node)
        rubric = node.previous_sibling().previous_sibling()
        text = rubric.next_node()
        self.visit_title(node=rubric)
        self.visit_Text(text)
        self.depart_Text(text)
        self.depart_title(node=rubric)

    def depart_autosummary_table(self, node, opt=False):
        if opt:
            # Only Pop the Element when Leaving the Overall Autodoc Description
            self._pop_element()
        else:
            self._auto_summary_node = node


    def visit_seealso(self, node):
        self._push_element('seealso')

    def depart_seealso(self, node):
        self._pop_element()


    def visit_option_list(self, node):
        self._push_element('option_list')

    def depart_option_list(self, node):
        self._pop_element()


    def visit_option_list_item(self, node):
        self._push_element('option_list_item')

    def depart_option_list_item(self, node):
        self._pop_element()


    def visit_option_group(self, node):
        self._push_element('option_group')

    def depart_option_group(self, node):
        self._pop_element()


    def visit_option_string(self, node):
        self._push_element('option_string')

    def depart_option_string(self, node):
        self._pop_element()


    def visit_option(self, node):
        self._push_element('option')

    def depart_option(self, node):
        self._pop_element()


    def visit_option_argument(self, node):
        self._push_element('option_argument')

    def depart_option_argument(self, node):
        self._pop_element()


    def visit_description(self, node):
        self._push_element('description')

    def depart_description(self, node):
        self._pop_element()


    def visit_address(self, node):
        self.visit_literal_block(node)


    def depart_address(self, node):
        self.depart_literal_block(node)


    def visit_line_block(self, node):
        """Visit a line block node.
        
        Line blocks preserve line breaks and are typically used for poetry,
        addresses, or other formatted text where line breaks are significant.
        In DocBook, we use literallayout to preserve formatting.
        """
        self._push_element('literallayout')


    def depart_line_block(self, node):
        """Depart a line block node."""
        self._pop_element()


    def visit_line(self, node):
        """Visit a line node within a line block.
        
        Each line in a line block is represented as a separate line node.
        We don't need to create additional elements, just let the content flow.
        """
        pass


    def depart_line(self, node):
        """Depart a line node within a line block.
        
        Add a line break after each line except the last one.
        """
        # Check if this is not the last line in the line block
        if node.parent and hasattr(node, 'parent'):
            parent_children = list(node.parent.children)
            if parent_children and node is not parent_children[-1]:
                # Add a line break after this line (except for the last line)
                self.tb.data('\n')


    def visit_download_reference(self, node):
        # ignore comments in the output.
        _print_error("ignoring download reference:", node)
        raise nodes.SkipNode


    def depart_download_reference(self, node):
        pass


    def visit_comment(self, node):
        # ignore comments in the output.
        _print_error("ignoring comment:", node)
        raise nodes.SkipNode

    def depart_comment(self, node):
        pass

    def visit_compound(self, node):
        pass


    def depart_compound(self, node):
        pass


    def visit_docinfo(self, node):
        _print_error("docinfo", node)
        pass


    def depart_docinfo(self, node):
        pass


    def visit_include(self, node):
        """Include as an xi:include"""


    def visit_index(self, node):
        pass
        #self._push_element('indexterm')


    def depart_index(self, node):
        pass
        #self._pop_element()


    def visit_literal_strong(self, node):
        self._push_element('command')


    def depart_literal_strong(self, node):
        self._pop_element()


    def visit_substitution_definition(self, node):
        # substitution references don't seem to be caught by the processor.
        # Otherwise, I'd have this code here:
        # sub_name = node['names'][0]
        # sub_text = node.children[0])
        # if sub_text[0:2] == '\\u':
        #     sub_text = '&#%s;' % sub_text[2:]
        # self.subs.append('<!ENTITY %s "%s">' % (sub_name, sub_text))
        raise nodes.SkipNode

    def depart_substitution_definition(self, node):
        pass

    def visit_substitution_reference(self, node):
        #self.tb.data('&%s;' % node))
        raise nodes.SkipNode

    def depart_substitution_reference(self, node):
        pass


    def visit_subtitle(self, node):
        self._push_element('subtitle')


    def depart_subtitle(self, node):
        self._pop_element()


    def visit_title(self, node):
        attribs = {}
        if "use_xml_id_in_titles" in self._kwargs:
            if self._kwargs["use_xml_id_in_titles"]:
                # first check to see if an
                # {http://www.w3.org/XML/1998/namespace}id was supplied.
                if len(node['ids']) > 0:
                    attribs[_NAMESPACE_ID] = node['ids'][0]
                elif len(node.parent['ids']) > 0:
                    # If the parent node has an ID, we can use that and add
                    # '.title' at the end to make a deterministic title ID.
                    attribs[_NAMESPACE_ID] = f"{node.parent['ids'][0]}.title"
        self._push_element('title', attribs)


    def depart_title(self, node):
        self._pop_element()


    def visit_title_reference(self, node):
        self._push_element('citetitle')


    def depart_title_reference(self, node):
        self._pop_element()


    def visit_titleabbrev(self, node):
        self._push_element('titleabbrev')


    def depart_titleabbrev(self, node):
        self._pop_element()


    def visit_topic(self, node):
        self.visit_section(node)


    def depart_topic(self, node):
        self.depart_section(node)


    #
    # link parts
    #

    def visit_reference(self, node):
        internal_ref = False

        # internal ref style #1: it declares itself internal
        if node.hasattr('internal'):
            internal_ref = node['internal']

        # internal ref style #2: it hides as an external ref, with strange
        # qualities.
        if (node.hasattr('anonymous') and (node['anonymous'] == 1) and
                node.hasattr('refuri') and (node['refuri'][0] == '_')):
            internal_ref = True
            node['refuri'] = node['refuri'][1:]

        if node.hasattr('refid'):
            self._push_element('link', {'linkend': node['refid']})
        elif node.hasattr('refuri'):
            if internal_ref:
                ref_name = os.path.splitext(node['refuri'])[0]
                self._push_element('link', {'linkend': ref_name})
            else:
                self._push_element(
                    'link',
                    {'{http://www.w3.org/1999/xlink}href': node['refuri']}
                )
        else:
            _print_error('unknown reference', node)


    def depart_reference(self, node):
        if node.hasattr('refid') or node.hasattr('refuri'):
            self._pop_element()


    def visit_target(self, node):
        if node.hasattr('refid'):
            if node['refid'] == 'index-0':
                return
            else:
                self.next_element_id = node['refid']


    def depart_target(self, node):
        #self._pop_element()
        pass


    #
    # list parts
    #

    def visit_bullet_list(self, node):
        self._push_element('itemizedlist')


    def depart_bullet_list(self, node):
        self._pop_element()


    def visit_enumerated_list(self, node):
        self._push_element('orderedlist')


    def depart_enumerated_list(self, node):
        self._pop_element()


    def visit_list_item(self, node):
        self._push_element('listitem')


    def depart_list_item(self, node):
        self._pop_element()


    def visit_definition_list(self, node):
        # Don't create additional container if we're already in a glossary
        if not self.in_glossary:
            self._push_element('variablelist')


    def depart_definition_list(self, node):
        if not self.in_glossary:
            self._pop_element()


    def visit_definition_list_item(self, node):
        attribs = {}
        
        # Handle IDs for glossary entries
        if len(node['ids']) > 0:
            attribs[_NAMESPACE_ID] = node['ids'][0]
        
        if self.in_glossary:
            self._push_element('glossentry', attribs)
        else:
            self._push_element('varlistentry', attribs)


    def depart_definition_list_item(self, node):
        self._pop_element()


    def visit_term(self, node):
        attribs = {}
        
        # Handle IDs for glossary terms
        if len(node['ids']) > 0:
            attribs[_NAMESPACE_ID] = node['ids'][0]
            
        if self.in_glossary:
            self._push_element('glossterm', attribs)
        else:
            self._push_element('term', attribs)


    def depart_term(self, node):
        self._pop_element()


    def visit_definition(self, node):
        if self.in_glossary:
            self._push_element('glossdef')
        else:
            self.visit_list_item(node)


    def depart_definition(self, node):
        if self.in_glossary:
            self._pop_element()
        else:
            self.depart_list_item(node)


    def visit_field_list(self, node):
        self._push_element('info')


    def depart_field_list(self, node):
        self._pop_element()  # info


    def visit_field(self, node):
        pass


    def depart_field(self, node):
        pass


    def visit_field_name(self, node):
        name = node.astext()
        if name == 'author':
            self._push_element('author')
            self._push_element('personname')
        elif name == 'date':
            self._push_element('pubdate')
        self.current_field_name = name
        raise self.SkipNode

    def depart_field_name(self, node):
        pass

    def visit_field_body(self, node):
        if self.current_field_name:
            value = node.astext()
            self.fields[self.current_field_name] = value
        else:
            node.clear()

    def depart_field_body(self, node):
        if self.current_field_name:
            if self.current_field_name == 'author':
                self._pop_element()  # personname
                self._pop_element()  # author
            elif self.current_field_name == 'date':
                self._pop_element()  # pubdate
            self.current_field_name = None

    #
    # image parts
    #

    def visit_image(self, node):
        # if not in an enclosing figure, then we need to start a mediaobject
        # here.
        if self.in_figure == False:
            self._push_element('mediaobject')

        self._push_element('imageobject')

        # Many options are supported for imagedata
        imagedata_attribs = {}

        if node.hasattr('uri'):
            imagedata_attribs['fileref'] = node['uri']
        else:
            # unknown attribute - convert to string representation
            imagedata_attribs['eek'] = str(node)

        if node.hasattr('height'):
            pass # not in docbook

        if node.hasattr('width'):
            pass # not in docbook

        if node.hasattr('scale'):
            imagedata_attribs['scale'] = str(node['scale'])

        if node.hasattr('align'):
            alignval = node['align']
            if alignval in ['top', 'middle', 'bottom']:
                # top, middle, bottom all refer to the docbook 'valign'
                # attribute.
                imagedata_attribs['valign'] = alignval
            else:
                # left, right, center stay as-is
                imagedata_attribs['align'] = alignval

        if node.hasattr('target'):
            _print_error('no target attribute supported for images!')

        self._push_element('imagedata', imagedata_attribs)
        self._pop_element()

        # alt text?
        if node.hasattr('alt'):
            self._push_element('textobject')
            self._push_element('phrase')
            sanitized_alt = self._sanitize_xml_text(node['alt'])
            self.tb.data(sanitized_alt)
            self._pop_element() # phrase
            self._pop_element() # textobject


    def depart_image(self, node):
        self._pop_element() # imageobject
        # if not in an enclosing figure, then we need to close the mediaobject
        # here.
        if self.in_figure == False:
            self._pop_element() # mediaobject


    def visit_figure(self, node):
        self._push_element('mediaobject')
        self.in_figure = True


    def depart_figure(self, node):
        self._pop_element()
        self.in_figure = False


    def visit_caption(self, node):
        self._push_element('caption')
        self.visit_paragraph(node)


    def depart_caption(self, node):
        self.depart_paragraph(node)
        self._pop_element()


    #
    # table parts
    #

    def visit_table(self, node):
        self._push_element('table')


    def depart_table(self, node):
        self._pop_element()


    def visit_tgroup(self, node):
        attribs = {}

        if node.hasattr('cols'):
            attribs['cols'] = str(node['cols'])

        self._push_element('tgroup', attribs)


    def depart_tgroup(self, node):
        self._pop_element()


    def visit_colspec(self, node):
        attribs = {}

        if node.hasattr('colwidth'):
            attribs['colwidth'] = str(node['colwidth'])

        self._push_element('colspec', attribs)


    def depart_colspec(self, node):
        self._pop_element()


    def visit_thead(self, node):
        self._push_element('thead')


    def depart_thead(self, node):
        self._pop_element()


    def visit_row(self, node):
        self._push_element('row')


    def depart_row(self, node):
        self._pop_element()


    def visit_entry(self, node):
        self._push_element('entry')


    def depart_entry(self, node):
        self._pop_element()


    def visit_tbody(self, node):
        self._push_element('tbody')


    def depart_tbody(self, node):
        self._pop_element()


    #
    # Character formatting
    #

    def visit_emphasis(self, node):
        self._push_element('emphasis')


    def depart_emphasis(self, node):
        self._pop_element()


    def visit_strong(self, node):
        self._push_element('emphasis', {'role': 'strong'})


    def depart_strong(self, node):
        self._pop_element()


    def visit_subscript(self, node):
        self._push_element('subscript')


    def depart_subscript(self, node):
        self._pop_element()


    def visit_superscript(self, node):
        self._push_element('superscript')


    def depart_superscript(self, node):
        self._pop_element()


    #
    # Code and such
    #

    def visit_literal_block(self, node):
        attribs = {}

        if node.hasattr('language'):
            if node.hasattr('classes') and len(node['classes']) > 0:
                attribs['language'] = node['classes'][1]
            else:
                attribs['language'] = node['language']

        self._push_element("programlisting", attribs)
        self.in_pre_block = True


    def depart_literal_block(self, node):
        self._pop_element()
        self.in_pre_block = False


    def visit_literal(self, node):
        self._push_element('code')


    def depart_literal(self, node):
        self._pop_element()


    def visit_inline(self, node):
        pass


    def depart_inline(self, node):
        pass

    #
    # Admonitions
    #

    def visit_admonition(self, node):
        # generic admonitions will just use the 'note' conventions, but will
        # set the title.
        self.visit_note(node)


    def depart_admonition(self, node):
        self.depart_note(node)


    def visit_attention(self, node):
        self.visit_important(node)
        self._add_element_title('Attention')


    def depart_attention(self, node):
        self.depart_important(node)


    def visit_caution(self, node):
        self._push_element('caution')


    def depart_caution(self, node):
        self._pop_element()


    def visit_danger(self, node):
        self.visit_warning(node)
        self._add_element_title('Danger')


    def depart_danger(self, node):
        self.depart_warning(node)


    def visit_error(self, node):
        self.visit_important(node)
        self._add_element_title('Error')


    def depart_error(self, node):
        self.depart_important(node)


    def visit_hint(self, node):
        self.visit_tip(node)
        self._add_element_title('Hint')


    def depart_hint(self, node):
        self.depart_tip(node)


    def visit_important(self, node):
        self._push_element('important')


    def depart_important(self, node):
        self._pop_element()


    def visit_note(self, node):
        self._push_element('note')


    def depart_note(self, node):
        self._pop_element()


    def visit_tip(self, node):
        self._push_element('tip')


    def depart_tip(self, node):
        self._pop_element()


    def visit_warning(self, node):
        self._push_element('warning')


    def depart_warning(self, node):
        self._pop_element()


    #
    # Version modification
    #

    def visit_versionmodified(self, node):
        """Handle Sphinx versionmodified nodes (versionadded, versionchanged, deprecated)."""
        # Use a note element for version information in DocBook
        # We could also use 'remark' for editorial information
        self._push_element('note')
        
        # Create a title based on the type and version
        version_type = node.get('type', 'versionmodified')
        version = node.get('version', '')
        
        # Map Sphinx version types to readable titles
        type_labels = {
            'versionadded': 'New in version',
            'versionchanged': 'Changed in version', 
            'deprecated': 'Deprecated since version',
            'versionremoved': 'Removed in version'
        }
        
        title_text = f"{type_labels.get(version_type, 'Version')} {version}"
        if title_text.strip():
            self._add_element_title(title_text)


    def depart_versionmodified(self, node):
        self._pop_element()

    #
    # Glossary support
    #

    def visit_glossary(self, node):
        """Handle Sphinx glossary directive."""
        attribs = {}
        
        # Handle IDs for glossary
        if self.next_element_id:
            attribs[_NAMESPACE_ID] = self.next_element_id
            self.next_element_id = None
        elif len(node['ids']) > 0:
            attribs[_NAMESPACE_ID] = node['ids'][0]
        
        # Set glossary context
        self.in_glossary = True
        
        # Create a glossary element in DocBook
        self._push_element('glossary', attribs)
        
        # Add title if not already present
        # Sphinx glossaries often don't have explicit titles
        # but DocBook glossaries can benefit from one
        if not any(isinstance(child, nodes.title) for child in node.children):
            self._add_element_title('Glossary')

    def depart_glossary(self, node):
        self.in_glossary = False
        self._pop_element()



    def visit_term_reference(self, node):
        """Handle references to glossary terms."""
        # Create a link to the glossary term
        if node.hasattr('refid'):
            self._push_element('glossterm', {'linkend': node['refid']})
        else:
            # Fallback to regular emphasis if no reference ID
            self._push_element('glossterm')

    def depart_term_reference(self, node):
        self._pop_element()

    def visit_pending_xref(self, node):
        """Handle Sphinx cross-references including glossary term references."""
        reftype = node.get('reftype', '')
        reftarget = node.get('reftarget', '')
        
        if reftype == 'term' and reftarget:
            # This is a glossary term reference
            self._push_element('glossterm', {'linkend': reftarget})
        elif node.get('refid'):
            # General cross-reference with ID
            self._push_element('link', {'linkend': node['refid']})
        elif reftarget:
            # Use the target as link reference
            self._push_element('link', {'linkend': reftarget})
        else:
            # Fallback to emphasis for unresolved references
            self._push_element('emphasis')

    def depart_pending_xref(self, node):
        self._pop_element()

    def visit_glossary_see(self, node):
        """Handle 'see' references in glossary entries."""
        self._push_element('glosssee')

    def depart_glossary_see(self, node):
        self._pop_element()

    def visit_glossary_seealso(self, node):
        """Handle 'see also' references in glossary entries."""
        self._push_element('glossseealso')

    def depart_glossary_seealso(self, node):
        self._pop_element()

    def visit_only(self, node):
        """Handle Sphinx 'only' directive nodes."""
        # The 'only' directive is used for conditional content
        # We'll process its content normally for DocBook output
        pass

    def depart_only(self, node):
        pass

    def visit_meta(self, node):
        """Handle meta nodes (usually for HTML metadata)."""
        # Meta nodes are typically for HTML output, skip in DocBook
        _print_error("ignoring meta node:", node)
        raise nodes.SkipNode

    def depart_meta(self, node):
        pass

    def visit_highlightlang(self, node):
        """Handle highlight language directive."""
        # This directive sets the default highlighting language
        # Skip it as it's handled at a higher level
        _print_error("ignoring highlightlang directive:", node)
        raise nodes.SkipNode

    def depart_highlightlang(self, node):
        pass

    #
    # TODO support
    #

    def visit_todo_node(self, node):
        """Handle Sphinx TODO nodes from sphinx.ext.todo extension."""
        # Use a note element with a distinctive title for TODO items
        self._push_element('note')
        
        # Add a standard "TODO" title 
        self._add_element_title('TODO')

    def depart_todo_node(self, node):
        """Depart TODO node."""
        self._pop_element()

    #
    # Error encountered...
    #

    def visit_problematic(self, node):
        _print_error('problematic node', node)

    def depart_problematic(self, node):
        pass

    def visit_system_message(self, node):
        _print_error('system message', node)

    def depart_system_message(self, node):
        pass
