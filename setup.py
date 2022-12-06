#!/usr/bin/env python
import re
from setuptools import setup, find_packages

long_desc = ""
with open("./README.md", "r", encoding="utf-8") as long_desc_file:
    long_desc = long_desc_file.read()

version = "0.0"
with open("./sphinx_docbook/__init__.py", "r", encoding="utf-8") as init_file:
    version = re.findall(r"\= (\d{1,2}\.\d{1,2})", init_file.read())

setup(
    name='spinx_docbook',
    description="reStructuredText to DocBook converter using Python docutils.",
    version=version,
    long_description=long_desc,
    long_description_content_type="text/markdown",
    install_requires=['docutils>=0.12', 'lxml>=2.3'],
    packages=find_packages(),
    author='Eron Hennessey', # TODO
    author_email='eron@abstrys.com', # TODO
    url='https://github.com/engineerjoe440/sphinx_docbook',
)
