# Sphinx DocBook Builder

A Sphinx builder to generate DocBook output (`sphinx_docbook.docbook_builder`).

## Prerequisites

Before installing `sphinx_docbook` on Linux, you'll need the following
prerequisites:

* libxml2 and headers (**libxml2** and **libxml2-dev**)
* Python bindings for libxml2 (**python3-lxml**)
* libxslt1 headers (**libxslt1-dev**)
* Python headers (**python3-dev**)

**You can install these on Ubuntu / Debian** by running:

```shell
sudo apt-get install libxml2 libxml2-dev libxslt1-dev python3-lxml python3-dev
```

### DocBook template files

When using a DocBook template file, use {{data.root_element}} and {{data.contents}} to represent the
root element (chapter, section, etc.) and {{data.contents}} to represent the transformed contents of
your ``.rst`` source.

For example, you could use a template that looks like this:

```xml
<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE {{data.root_element}} PUBLIC "-//OASIS//DTD DocBook XML V4.1.2//EN"
            "http://www.oasis-open.org/docbook/xml/4.1.2/docbookx.dtd">
<{{data.root_element}}>
    {{data.contents}}
</{{data.root_element}}>
```

A template is only necessary if you want to customize the output. A standard DocBook XML header will
be included in each output file by default.

## Using the Sphinx Docbook builders

To build DocBook output with Sphinx, add `sphinx_docbook.docbook_builder` to the
*extensions* list in `conf.py`:

```python
extensions = [
    #... other extensions here ...
    'sphinx_docbook.docbook_builder',
]
```

There are two configurable parameters for `conf.py` that correspond to
`rst2db.py` parameters:

| Name | Description |
|------|-------------|
| *docbook_template_file* | template file that will be used to position the document parts. This should be a valid DocBook .xml file that contains  Requires Jinja2 to be installed if specified. |
| *docbook_default_root_element* | default root element for a file-level document.  Default is 'section'. |

For example:

```python
docbook_template_file = 'dbtemplate.xml'
docbook_default_root_element = chapter
```

Then, build your project using `sphinx-build` with the `-b docbook` option:

```shell
sphinx-build source output -b docbook
```

### License

This software is provided under the
[BSD 3-Clause](http://opensource.org/licenses/BSD-3-Clause) license. See the
[LICENSE](https://github.com/Abstrys/abstrys-toolkit/blob/master/LICENSE) file
for more details.
