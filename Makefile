.PHONY: install install-dev test test-services lint security notebook-check test-all

install:
	pip install -e .

install-dev:
	pip install -e ".[dev,serving,explainability]"

test:
	python -m pytest src/tests/ -v
	cd 01_mega_project_1_underwriting_approval && python -m pytest tests/ -v
	cd 02_mega_project_2_regulatory_capital && python -m pytest tests/ -v
	cd 03_mega_project_3_risk_segmentation && python -m pytest tests/ -v
	cd 04_mega_project_4_delinquency_prevention && python -m pytest tests/ -v
	cd 05_mega_project_5_liquidity_cashflow && python -m pytest tests/ -v

test-services: test

lint:
	pyflakes src/ 01_mega_project_1_underwriting_approval/services/ 01_mega_project_1_underwriting_approval/tests/ 02_mega_project_2_regulatory_capital/services/ 02_mega_project_2_regulatory_capital/tests/ 03_mega_project_3_risk_segmentation/services/ 03_mega_project_3_risk_segmentation/tests/ 04_mega_project_4_delinquency_prevention/services/ 04_mega_project_4_delinquency_prevention/tests/ 05_mega_project_5_liquidity_cashflow/services/ 05_mega_project_5_liquidity_cashflow/tests/
	-black --check --diff src/ 01_mega_project_1_underwriting_approval/services/ 01_mega_project_1_underwriting_approval/tests/ 02_mega_project_2_regulatory_capital/services/ 02_mega_project_2_regulatory_capital/tests/ 03_mega_project_3_risk_segmentation/services/ 03_mega_project_3_risk_segmentation/tests/ 04_mega_project_4_delinquency_prevention/services/ 04_mega_project_4_delinquency_prevention/tests/ 05_mega_project_5_liquidity_cashflow/services/ 05_mega_project_5_liquidity_cashflow/tests/
	# black is advisory here (repo-wide reformat deliberately deferred, see CHANGELOG) --
	# the leading "-" keeps `make lint` from failing the whole target over formatting alone,
	# matching code-quality.yml's own "|| true" on the same step.

security:
	bandit -r src/ 01_mega_project_1_underwriting_approval/services/ 02_mega_project_2_regulatory_capital/services/ 03_mega_project_3_risk_segmentation/services/ 04_mega_project_4_delinquency_prevention/services/ 05_mega_project_5_liquidity_cashflow/services/ -ll

notebook-check:
	python -c "import glob, nbformat; [nbformat.validate(nbformat.read(p, as_version=4)) or print('OK', p) for p in glob.glob('**/*.ipynb', recursive=True)]"

test-all: notebook-check test lint security
