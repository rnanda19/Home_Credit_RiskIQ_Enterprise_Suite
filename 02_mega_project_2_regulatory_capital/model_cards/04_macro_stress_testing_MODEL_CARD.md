# Model Card — Problem 4: Macro Stress Testing

Notebook: `notebooks/04_macro_stress_testing.ipynb`
Hard dependency (not owned by this notebook): `../decision_engine/artifacts/notebook_01_capital_scores.csv`

## CI status

Re-verified 2026-09-05 against the current `main` branch (commit `33ebb69`):
all 12 GitHub Actions checks pass — `shared-tests`, `unit-tests` (all 5 Mega
Projects), `lint`, `security-scan`, `build`, `notebook-syntax`, `deploy`, and
`report-build-status`. GitHub's file-history view may still show a red ✗ on
an older commit that last touched this file (`517b7f4`, from the 2026-09-02
sync, when a `polars` dependency was briefly missing from the `shared-tests`
job) — that historical failure was fixed in commit `96e4321` and does not
reflect the current state of the suite.

## This is not a model, and every shock is a documented, cited assumption

This notebook trains nothing. For the Baseline scenario it reuses Notebook
01's already-computed, already-disclosed real per-applicant `PD`,
`LGD_ASSUMED`, `EAD_PROXY`, and `CORRELATION_R` directly, unmodified. Home
Credit's real dataset has no macro/time-series dimension at all — no
vintage, no economic-cycle indicator — so every shock magnitude below is a
disclosed, cited assumption, never fitted or backed out to hit a target
number, exactly this suite's existing posture on LGD/correlation.

## What a "shock" means here, precisely

| Scenario | Systematic factor (Z) | LGD | Basis |
|---|---|---|---|
| Baseline | Not shocked — real PD/LGD reused directly | Real, unmodified | Notebook 01's actual output |
| Adverse | Φ⁻¹(0.05) = -1.6449 | Unmodified | Standard-normal 95th-percentile adverse value — a documented "1-in-20 downturn" severity convention |
| Severely Adverse | Φ⁻¹(0.001) = -3.0902 | ×1.25 (capped at 100%) | The SAME 99.9th-percentile severity Basel's own closed-form retail-IRB capital function is calibrated to [BCBS05]; LGD add-on reflects the Basel II "downturn LGD" concept — LGD should be appropriate for economic-downturn conditions where more conservative than long-run averages [BCBS06] |

The PD shock mechanism is the real, already-cited single-factor Vasicek
conditional-PD formula (the same formula Notebook 03's Monte Carlo draws Z
from at random) — re-evaluated here at a specific, disclosed adverse value
of Z rather than a random draw. This is a standard, real technique in
single-factor credit stress testing, not an invented shock.

## A real mathematical mistake this notebook's own cross-check caught before delivery

The first version of this notebook defined "Baseline" as Z = 0 run through
the conditional-PD formula, on the (wrong) assumption that Φ((Φ⁻¹(PD))/√(1−R))
would reproduce PD exactly at Z=0. It does not: Φ is nonlinear, so the
unconditional PD is recovered only by *integrating* the conditional formula
over Z ~ N(0,1) (exactly how PD was calibrated in the first place), not by
evaluating it at the single point Z=0. On the fixture, this produced a real,
measurable 5.36% relative gap between "Baseline" and Notebook 01's actual
closed-form capital — caught immediately by this notebook's own Section 10
cross-check (`baseline_scenario_matches_notebook_01_exactly`), which is
exactly what that check exists for. Fixed by having the Baseline scenario
reuse Notebook 01's real PD/LGD directly rather than round-tripping through
the conditional formula at Z=0; confirmed via re-execution to a relative
difference of 2.35e-10 (floating-point noise, not a real gap). Full record
in `CHANGELOG.md` [1.4.6] and `LESSONS_LEARNED.md` #6.

## Advanced error tackling applied

- **Hard dependency** checked by actual required columns present in
  Notebook 01's output, not just file existence (`LESSONS_LEARNED.md` #4).
- **`SCENARIOS` validated at runtime**: severity strictly non-increasing,
  no scenario's LGD multiplier improves on baseline — a future edit that
  breaks severity ordering raises immediately rather than silently
  producing a wrong result.
- **Vectorized K() re-implementation cross-checked against the trusted
  scalar `basel_retail_capital_k()`** on a real 200-applicant sample before
  being trusted for the full portfolio (`np.allclose`, `rtol=1e-9`) — a
  transcription bug in the vectorized formula would raise immediately, not
  silently corrupt every scenario's numbers.
- **Severity ordering checked per-applicant**, not just on portfolio
  totals — every one of the real applicants must show non-decreasing
  stressed PD from Baseline through Severely Adverse (a real mathematical
  guarantee of the single-factor model for any applicant with R > 0).

## Swift processing

No PD re-scoring, no reloading the 7 raw tables — everything needed is
already in Notebook 01's saved CSV. Each scenario is exactly one vectorized
`scipy.stats.norm.cdf`/`norm.ppf` pass over the whole real portfolio (never
a per-applicant Python loop): all 3 scenarios over the user's own real, full-scale
307,511-applicant portfolio completed in 0.12 seconds (compare Notebook 03's Monte Carlo, which needs tens
of thousands of such passes and takes minutes — this notebook needs exactly
3).

## Scenario Validation Verdict vs. Pipeline Integrity Checks

Deliberately NOT named "Statistical Robustness Verdict" like the
TARGET-based notebooks elsewhere in this suite: there is no real historical
stress period in Home Credit's data to backtest a hypothetical macro
scenario against. This tier instead validates the scenario MECHANICS are
correct and internally consistent — baseline identity, severity ordering,
formula correctness — stated explicitly rather than forcing an ill-fitting
statistical-significance test onto a scenario analysis with no real target
to test against.

## Limitations

- Inherits every limitation already documented in Notebook 01's model card.
- EAD is NOT stressed (no credit-conversion-factor data for undrawn
  revolving limits at this dataset's scope — same limitation already
  disclosed in Notebook 01).
- LGD is stressed only in the Severely Adverse scenario, by a documented,
  disclosed 25% relative add-on — a scenario sensitivity assumption, not a
  measured or officially mandated downturn-LGD figure.
- Only 2 shocked scenarios (Adverse, Severely Adverse) plus Baseline —
  additional severities can be added to `SCENARIOS` following the same
  documented-and-validated-at-runtime pattern.

## Reproducibility

Deterministic — no random sampling anywhere in this notebook (unlike
Notebook 03's Monte Carlo). Idempotent: re-running overwrites the same
output paths given the same Notebook 01 output and the same `SCENARIOS`
definitions.
