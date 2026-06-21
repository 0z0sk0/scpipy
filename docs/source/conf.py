from importlib.metadata import version as get_version

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
]

source_suffix = '.rst'
master_doc = 'index'

project = 'scpipy'
author = '0Z0SK0'

version = get_version(project)
release = version

pygments_style = 'sphinx'

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']
html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
autodoc_typehints = 'description'
napoleon_google_docstring = True
napoleon_numpy_docstring = True
