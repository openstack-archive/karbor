# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys

sys.path.insert(0, os.path.abspath('../..'))
# -- General configuration ----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = [
    'sphinxcontrib.apidoc',
    # 'sphinx.ext.intersphinx',
    'openstackdocstheme',
    'oslo_config.sphinxext',
    'oslo_config.sphinxconfiggen',
    'oslo_policy.sphinxext',
    'oslo_policy.sphinxpolicygen',
    'reno.sphinxext'
]

# autodoc generation is a bit aggressive and a nuisance when doing heavy
# text edit cycles.
# execute "export SPHINX_DEBUG=1" in your terminal to disable
modindex_common_prefix = [
    'karbor.',
    'karbor.services.',
]
exclude_patterns = [
    'api/karbor.tests.*',
    'api/karbor.wsgi.*',
    'api/karbor.services.protection.bank_plugins.*',
    'api/karbor.services.protection.protectable_plugins.*',
    'api/karbor.services.protection.protection_plugins.*',
]

config_generator_config_file = [
    ('../../etc/oslo-config-generator/karbor.conf',
     '_static/karbor'),
]

policy_generator_config_file = '../../etc/karbor-policy-generator.conf'
sample_policy_basename = '_static/karbor'

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'karbor'
copyright = u'2013, OpenStack Foundation'

# If true, '()' will be appended to :func: etc. cross-reference text.
add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
add_module_names = True

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# -- sphinxcontrib.apidoc configuration --------------------------------------

apidoc_module_dir = '../../karbor'
apidoc_output_dir = 'contributor/api'
apidoc_excluded_paths = [
    'tests',
    'wsgi',
    'services/protection/bank_plugins',
    'services/protection/protectable_plugins',
    'services/protection/protection_plugins',
]

# -- Options for HTML output --------------------------------------------------

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
# html_theme_path = ["."]
html_theme = 'openstackdocs'
# html_static_path = ['static']

# Output file base name for HTML help builder.
htmlhelp_basename = '%sdoc' % project

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass
# [howto/manual]).
latex_documents = [
    ('index',
     '%s.tex' % project,
     u'%s Documentation' % project,
     u'OpenStack Foundation', 'manual'),
]

# -- Options for openstackdocstheme -------------------------------------------
repository_name = 'openstack/karbor'
bug_project = project.lower()
bug_tag = ''
