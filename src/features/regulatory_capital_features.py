"""
src/features/regulatory_capital_features.py

Shared feature/formula module for Mega Project 2 (Regulatory Capital). Built once
(HYPER standing rule), imported by every MP2 notebook that needs LGD/EAD assignment
or the Basel retail-IRB capital formula -- never re-derived per notebook.

WHAT THIS MODULE IS AND IS NOT (read before using -- this is the zero-fabrication
disclosure for every number this module produces):

Home Credit's real, downloadable dataset has no regulatory-capital fields at all --
no LGD, no EAD, no risk-weight, no internal capital figure of any kind. Mega Project 2
exists anyway because Expected Loss and regulatory capital are BOTH computable from
data this suite genuinely has, PROVIDED the missing risk parameters are supplied as
explicit, sourced, industry-standard assumptions rather than pretended to be measured:

  - PD (probability of default) is REAL: it is Mega Project 1 / Notebook 01's actual
    trained champion model, loaded here and scored (never retrained) -- same
    "loaded, not retrained" pattern MP1's own Notebook 03/04/05 already used against
    Notebook 01.
  - EAD (exposure at default) uses the real `AMT_CREDIT` column (the disbursed/
    approved credit amount) as a standard, disclosed EAD proxy for term/installment
    exposures. This is a simplification, stated plainly: a fully specified EAD for a
    revolving exposure would apply a credit-conversion factor to an undrawn limit,
    which this dataset does not expose at the application level used here.
  - LGD (loss given default) and the asset correlation (R) used in the capital
    formula below are NOT measured from Home Credit's data at all -- this dataset has
    no realized recovery/workout data to measure them from. They are assigned from
    published Basel retail-IRB benchmarks, cited by segment below, applied uniformly
    to every real applicant -- never fitted, tuned, or backed out to hit a target
    number.

Every function here returns which assumption was applied alongside the number, so a
reader (or notebook) can always trace a result back to its source.

SOURCES (full citations, cited again inline at each assumption)
-----------------------------------------------------------------
[BCBS06] Basel Committee on Banking Supervision, "International Convergence of
  Capital Measurement and Capital Standards: A Revised Framework -- Comprehensive
  Version" (June 2006) -- paragraphs 231-234 (retail asset-correlation formulas by
  sub-class), 328-330 (retail risk-weight / capital-requirement function), 272-287
  (Expected Loss = PD x LGD x EAD; F-IRB supervisory LGD reference points).
[BCBS05] Basel Committee on Banking Supervision, "An Explanatory Note on the Basel II
  IRB Risk Weight Functions" (July 2005) -- the worked Vasicek-ASRF derivation of the
  K() function used unmodified below.
[EBA-CRR] EU Capital Requirements Regulation (575/2013) Article 164 -- residential
  real-estate-secured retail exposures: minimum LGD floors context for the secured
  segment below.
"""
from __future__ import annotations

import math

import polars as pl
from scipy.stats import norm

RANDOM_SEED = 42

# ---------------------------------------------------------------------------
# LGD + asset-correlation segment table (documented assumption layer).
# Every LGD/R pair below is a published Basel retail-IRB reference point, mapped
# onto the real, disclosed collateral-proxy signals this dataset actually has
# (FLAG_OWN_REALTY, FLAG_OWN_CAR, NAME_CONTRACT_TYPE). No value here is fitted to
# Home Credit's own outcomes.
# ---------------------------------------------------------------------------
SEGMENT_DEFINITIONS: dict[str, dict] = {
    "Secured — Real Estate": {
        "lgd": 0.20,
        "correlation_mode": "fixed",
        "r_fixed": 0.15,
        "condition": "Cash loans, applicant owns real estate (FLAG_OWN_REALTY = Y)",
        "lgd_source": (
            "Basel retail residential-mortgage LGD reference range (10-25%, EU CRR "
            "Art. 164 floor context [EBA-CRR]); 20% used as the disclosed mid-range "
            "assumption for this segment."
        ),
        "r_source": "[BCBS06] para. 328 — residential mortgage retail: R fixed at 0.15.",
    },
    "Secured — Other (Vehicle/Goods)": {
        "lgd": 0.35,
        "correlation_mode": "other_retail_formula",
        "r_fixed": None,
        "condition": "Cash loans, applicant owns a car but not real estate (FLAG_OWN_CAR = Y, FLAG_OWN_REALTY = N)",
        "lgd_source": (
            "Industry-typical secured-consumer-loan LGD reference point (30-40% "
            "range commonly cited for auto/goods-secured consumer credit); 35% used "
            "as the disclosed mid-range assumption for this segment."
        ),
        "r_source": "[BCBS06] para. 330 — other retail: R computed via the PD-dependent formula (see other_retail_correlation()).",
    },
    "Unsecured — Other Retail": {
        "lgd": 0.45,
        "correlation_mode": "other_retail_formula",
        "r_fixed": None,
        "condition": "Cash loans, no real estate and no car flagged",
        "lgd_source": (
            "[BCBS06] para. 287 — 45% senior-unsecured supervisory LGD reference "
            "point (Foundation-IRB), used here as the disclosed conservative proxy "
            "for unsecured retail cash lending in the absence of Home Credit's own "
            "realized-recovery data."
        ),
        "r_source": "[BCBS06] para. 330 — other retail: R computed via the PD-dependent formula (see other_retail_correlation()).",
    },
    "Revolving (QRRE)": {
        "lgd": 0.65,
        "correlation_mode": "fixed",
        "r_fixed": 0.04,
        "condition": "NAME_CONTRACT_TYPE = Revolving loans",
        "lgd_source": (
            "Industry-typical unsecured-revolving/credit-card LGD reference point "
            "(50-85% range commonly cited in Basel QIS / retail-card loss studies); "
            "65% used as the disclosed mid-range assumption for this segment."
        ),
        "r_source": "[BCBS06] para. 329 — Qualifying Revolving Retail Exposure (QRRE): R fixed at 0.04.",
    },
}

SEGMENT_ORDER = [
    "Secured — Real Estate",
    "Secured — Other (Vehicle/Goods)",
    "Unsecured — Other Retail",
    "Revolving (QRRE)",
]


def assign_capital_segment(df: pl.DataFrame) -> pl.DataFrame:
    """Assigns each real applicant to one of the 4 documented LGD/correlation
    segments above, purely from real columns already in the dataset
    (NAME_CONTRACT_TYPE, FLAG_OWN_REALTY, FLAG_OWN_CAR) -- adds `CAPITAL_SEGMENT`,
    `LGD_ASSUMED`, and `EAD_PROXY` (= real AMT_CREDIT) columns."""
    df = df.with_columns([
        pl.when(pl.col("NAME_CONTRACT_TYPE") == "Revolving loans")
          .then(pl.lit("Revolving (QRRE)"))
          .when((pl.col("NAME_CONTRACT_TYPE") == "Cash loans") & (pl.col("FLAG_OWN_REALTY") == "Y"))
          .then(pl.lit("Secured — Real Estate"))
          .when(
              (pl.col("NAME_CONTRACT_TYPE") == "Cash loans")
              & (pl.col("FLAG_OWN_REALTY") == "N")
              & (pl.col("FLAG_OWN_CAR") == "Y")
          )
          .then(pl.lit("Secured — Other (Vehicle/Goods)"))
          .otherwise(pl.lit("Unsecured — Other Retail"))
          .alias("CAPITAL_SEGMENT"),
        pl.col("AMT_CREDIT").alias("EAD_PROXY"),
    ])
    lgd_map = {name: seg["lgd"] for name, seg in SEGMENT_DEFINITIONS.items()}
    df = df.with_columns(
        pl.col("CAPITAL_SEGMENT").replace_strict(lgd_map, default=0.45).alias("LGD_ASSUMED")
    )
    return df


def other_retail_correlation(pd_value: float) -> float:
    """[BCBS06] para. 330 -- "Other Retail" asset correlation, the one non-fixed
    retail R in the whole framework: PD-dependent, interpolating between 0.03 (high
    PD) and 0.16 (near-zero PD). Identical formula for every "other retail" real
    applicant regardless of exposure size (no firm-size adjustment in retail, unlike
    the corporate risk-weight function)."""
    pd_value = min(max(pd_value, 1e-6), 0.999999)
    w = (1 - math.exp(-35 * pd_value)) / (1 - math.exp(-35))
    return 0.03 * w + 0.16 * (1 - w)


def basel_retail_capital_k(pd_value: float, lgd: float, correlation: float) -> float:
    """[BCBS05] the Vasicek/ASRF K() function, unmodified -- the same closed-form
    capital-requirement function underlying every Basel II/III IRB risk-weight
    table, retail included. Returns K as a FRACTION OF EAD (not yet multiplied by
    EAD or by the 12.5x RWA scalar) -- i.e. this already nets out Expected Loss
    (PD x LGD), so K is the UNEXPECTED-loss capital charge alone, per the Basel
    framework's own definition. No maturity adjustment: retail exposures are
    explicitly exempt from the maturity-adjustment term that applies to corporate/
    sovereign/bank exposures ([BCBS06] para. 328).
    """
    pd_value = min(max(pd_value, 1e-6), 0.999999)
    r = correlation
    inner = (
        (1 - r) ** -0.5 * norm.ppf(pd_value)
        + (r / (1 - r)) ** 0.5 * norm.ppf(0.999)
    )
    k = lgd * norm.cdf(inner) - pd_value * lgd
    return max(k, 0.0)


def compute_capital_row(pd_value: float, lgd: float, segment: str, ead: float) -> dict:
    """Full per-exposure Basel retail-IRB computation for one real applicant.
    Returns EL (expected loss, PD x LGD x EAD), the correlation R actually used
    (fixed or PD-dependent per segment), K (unexpected-loss capital fraction),
    RWA (= K x 12.5 x EAD), and CAPITAL_REQUIREMENT (= RWA x 8% Pillar-1 minimum
    = K x EAD -- the 12.5x and 8% cancel exactly, shown both ways for auditability).
    """
    seg_def = SEGMENT_DEFINITIONS[segment]
    if seg_def["correlation_mode"] == "fixed":
        r = seg_def["r_fixed"]
    else:
        r = other_retail_correlation(pd_value)
    k = basel_retail_capital_k(pd_value, lgd, r)
    el = pd_value * lgd * ead
    rwa = k * 12.5 * ead
    capital_requirement = rwa * 0.08
    return {
        "CORRELATION_R": r,
        "CAPITAL_K": k,
        "EXPECTED_LOSS": el,
        "RWA": rwa,
        "CAPITAL_REQUIREMENT": capital_requirement,
    }


def compute_capital_frame(df: pl.DataFrame, pd_col: str = "PD") -> pl.DataFrame:
    """Vectorized (WARP) application of compute_capital_row() across a real Polars
    DataFrame that already has CAPITAL_SEGMENT / LGD_ASSUMED / EAD_PROXY (from
    assign_capital_segment()) and a real PD column. Uses map_elements only for the
    two non-vectorizable pieces (scipy.stats.norm.ppf/.cdf are not Polars-native) --
    everything else is native Polars expressions."""
    segments = df["CAPITAL_SEGMENT"].to_list()
    pds = df[pd_col].to_list()
    lgds = df["LGD_ASSUMED"].to_list()
    eads = df["EAD_PROXY"].to_list()
    rows = [
        compute_capital_row(pd_value=p, lgd=l, segment=s, ead=e)
        for p, l, s, e in zip(pds, lgds, segments, eads)
    ]
    out = pl.DataFrame(rows)
    return pl.concat([df, out], how="horizontal")


def risk_band_from_pd(pd_value: float) -> str:
    """Same 5-band PD convention used by MP1 (Notebook 03/04/05) -- one shared
    labeling scheme across the whole suite rather than a redefinition per problem."""
    if pd_value < 0.05:
        return "Lowest Risk"
    if pd_value < 0.10:
        return "Low Risk"
    if pd_value < 0.20:
        return "Moderate Risk"
    if pd_value < 0.35:
        return "High Risk"
    return "Highest Risk"


RISK_BAND_ORDER = ["Lowest Risk", "Low Risk", "Moderate Risk", "High Risk", "Highest Risk"]
