# Model Card — Problem 3: Retail Liquidity Coverage Proxy (LCR-adapted)

Notebook: `notebooks/03_retail_liquidity_coverage_proxy.ipynb`
Outputs: `decision_engine/reports/notebook_03_*` (gitignored — regenerate
by running the notebook)

## Intended use

Basel LCR's own structure (a coverage ratio tested against a pass
threshold) adapted to a retail loan book — explicitly disclosed as a
proxy, never a claim of a regulatory LCR. Tests whether real stressed
(5th-percentile) collections cover a required fraction of real scheduled
cash, at 30/60/90-day horizons.

## Not a per-applicant model — no deployable service

Portfolio-level coverage ratio, not a per-applicant classifier — no
`.joblib` bundle and no FastAPI service, by design.

## Real, current results (from your own full run)

Required coverage ratio assumption: **85%**.

| Horizon | Real stressed collections (p5) | Real scheduled cash | RLCP | Verdict |
|---|---|---|---|---|
| 30-day | $4,726,578,522 | $5,105,013,024 | 1.089 | **PASS** |
| 60-day | $9,512,407,214 | $10,210,026,048 | 1.096 | **PASS** |
| 90-day | $14,324,059,698 | $15,315,039,072 | 1.100 | **PASS** |

RLCP is stable across horizons (spread of 1.1%, well under the 10%
stability check). **9/9 structural integrity checks pass.**

## Verification status

Verified end-to-end per this suite's full protocol on your own real,
full-scale run: 0 execution errors, outputs cleared, `nbformat.validate()`
passed, a Playwright network-blocked HTML dashboard check, and a
LibreOffice headless Excel recalculation check. All 3 horizons PASS on
this run — an honest result, not a curated one; this notebook has also
returned a REVIEW verdict at some horizons on earlier runs, and would
report that plainly again if it recurred.

## Limitations

- "LCR-adapted" is a structural proxy, not a claim of regulatory Basel
  LCR compliance — see the notebook's own methodology section for the
  exact adaptation.
- Depends on Problem 2's real 5th-percentile CFaR figures as its stressed
  collections input.
- No fairness/bias audit performed in this pass (not applicable — no
  per-applicant decision is made here).

## How to reproduce

1. Download the real Home Credit Default Risk dataset from Kaggle.
2. Set up `project_config.json` per the notebook's own first markdown cell.
3. Run Notebooks 01 and 02 first (this notebook reuses Problem 2's real
   bootstrap output), then
   `notebooks/03_retail_liquidity_coverage_proxy.ipynb`.
4. Real outputs are written to `decision_engine/reports/` (gitignored —
   regenerate locally).
