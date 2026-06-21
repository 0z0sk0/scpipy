from pathlib import Path
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[0]
DOC = ROOT
SRC = DOC / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

pyproject = tomllib.loads((DOC / 'pyproject.toml').read_text(encoding='utf-8'))
project_meta = pyproject['project']

project = project_meta['name']
author = '0Z0SK0'
version = release = project_meta['version']

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']
html_theme = 'sphinx_rtd_theme'
autodoc_typehints = 'description'
napoleon_google_docstring = True
napoleon_numpy_docstring = True
