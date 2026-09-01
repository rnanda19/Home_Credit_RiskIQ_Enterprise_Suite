.PHONY: install install-dev test test-services lint security notebook-check test-all

install:
	pip install -e .

install-dev:
	pip install -e ".[dev,serving,explainability]"

test:
	cd mega_project_1_underwriting_approval && python -m pytest tests/ -v

test-services: test

lint:
	pyflakes src/ mega_project_1_underwriting_approval/services/ mega_project_1_underwriting_approval/tests/
	-black --check --diff src/ mega_project_1_underwriting_approval/services/ mega_project_1_underwriting_approval/tests/
	# black is advisory here (repo-wide reformat deliberately deferred, see CHANGELOG) --
	# the leading "-" keeps `make lint` from failing the whole target over formatting alone,
	# matching code-quality.yml's own "|| true" on the same step.

security:
	bandit -r src/ mega_project_1_underwriting_approval/services/ -ll

notebook-check:
	python -c "import glob, nbformat; [nbformat.validate(nbformat.read(p, as_version=4)) or print('OK', p) for p in glob.glob('**/*.ipynb', recursive=True)]"

test-all: notebook-check test lint security
