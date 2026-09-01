"""Thin setup.py for editable-install compatibility (pip install -e .) alongside
pyproject.toml's setuptools build backend -- lets `src/` (features/reporting/
utils/serving/models) be imported as a real installed package rather than
requiring every notebook to manually sys.path.insert."""
from setuptools import setup

setup()
