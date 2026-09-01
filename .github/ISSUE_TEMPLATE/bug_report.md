---
name: Bug report
about: Something in the notebooks, src/ library, or services doesn't work as expected
title: "[BUG] "
labels: bug
assignees: ""
---

**Which part of the project?**
(e.g. `01_credit_default_prediction.ipynb`, `src/features/`, `credit_default_scoring_service.py`, Docker build, CI)

**What happened?**
A clear description of the actual behavior, including the full error
message/traceback if there is one.

**What did you expect to happen?**

**Steps to reproduce**
1.
2.
3.

**Environment**
- OS:
- Python version (`python --version`):
- Installed via `pip install -e .` or manual `sys.path`?
- Notebook run against the real Kaggle dataset, or a smaller/synthetic sample?

**Data note**
If this bug only reproduces on the real Home Credit dataset (not on a small
sample you can share), please describe the data characteristics that trigger
it (e.g. "column X is entirely null in my extract") rather than attaching
the real data itself.
