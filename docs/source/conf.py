# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#

import os
import sys

# sys.path.insert(0, os.path.abspath("../"))
# import globus_action_provider_tools

# -- Project information -----------------------------------------------------

project = "Globus Action Provider Tools"
html_title = "Globus Action Provider Tools"
copyright = "2020, University of Chicago"
author = "Uriel Mandujano"

# The full version, including alpha/beta/rc tags
# release = globus_action_provider_tools.__version__


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = ["sphinx.ext.autodoc", "sphinxcontrib.redoc"]
autodoc_typehints = "description"
add_module_names = False

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []

# The document containing the toctree directive
master_doc = "index"

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "furo"
html_logo = "_static/images/globus-300x300-UC-blue.png"
html_theme_options = {}
pygments_dark_style = "monokai"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

html_css_files = [
    "css/termynal.css",
]
html_js_files = ["js/termynal.js"]

redoc_uri = "https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js"
redoc = [
    {
        "name": "Action Provider Interface",
        "page": "api",
        "spec": "actions_spec.openapi.yaml",
        "embed": True,
    },
]
