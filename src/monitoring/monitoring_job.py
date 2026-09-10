# Home Credit RiskIQ Enterprise Suite -- Scheduled Production Monitoring Job.
#
# Closes a real, previously-disclosed gap: this suite had PSI as a
# validation *concept* inside notebooks, but no dedicated monitoring/
# directory or monitoring job anywhere in the tracked repo. This is that
# missing piece -- a real, generic, per-model drift check, not tied to one
# Mega Project's feature set (see generate_monitoring_baseline.py for how
# a model's own baseline.json is produced from its own real bundle +
# real reference data).
#
# Intended usage (e.g. a daily cron job / Windows Task Scheduler task),
# pointed at whichever model's baseline you're monitoring:
#     python monitoring_job.py \
#         --new-data-csv path/to/new_scored_batch.csv \
#         --baseline-json 01_mega_project_1_underwriting_approval/monitoring/mp1_01_baseline.json \
#         --config-json   01_mega_project_1_underwriting_approval/monitoring/mp1_01_config.json \
#         --out-log       01_mega_project_1_underwriting_approval/monitoring/mp1_01_job_log.csv
#
# Exits 0 if all checks are OK/WATCH/NOT_COMPUTABLE, exits 1 if any check
# is ALERT (so a scheduler can act on the exit code -- e.g. fail the job /
# send a page). Modeled directly on the AMEX RiskIQ platform's own real
# monitoring_job.py (src/monitoring/monitoring_job.py there, Problem 1) --
# ported and generalized here rather than re-invented, per this suite's
# reuse-first build discipline.
import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # allow `python monitoring_job.py` directly

from monitoring.monitoring_common import bin_share, psi_from_bin_pct  # noqa: E402


def _psi_status(psi_value, thresholds):
    if psi_value is None:
        return "NOT_COMPUTABLE"
    if psi_value >= thresholds.get("psi_alert", 0.25):
        return "ALERT"
    if psi_value >= thresholds.get("psi_watch", 0.10):
        return "WATCH"
    return "OK"


def main():
    parser = argparse.ArgumentParser(
        description="Home Credit RiskIQ Enterprise Suite -- production drift monitoring job"
    )
    parser.add_argument(
        "--new-data-csv",
        required=True,
        help="Path to a new, already-preprocessed scored batch CSV",
    )
    parser.add_argument("--baseline-json", required=True)
    parser.add_argument("--config-json", required=True)
    parser.add_argument("--out-log", required=True)
    args = parser.parse_args()

    with open(args.baseline_json, "r", encoding="utf-8") as f:
        baseline = json.load(f)
    with open(args.config_json, "r", encoding="utf-8") as f:
        config = json.load(f)
    thresholds = config["thresholds"]

    import pandas as pd

    new_df = pd.read_csv(args.new_data_csv)

    result = {
        "run_at_utc": datetime.now(timezone.utc).isoformat(),
        "new_data_csv": args.new_data_csv,
        "baseline_json": args.baseline_json,
        "model_name": baseline.get("model_name", "unknown"),
        "n_rows": len(new_df),
        "checks": [],
    }
    alert = False

    target_col = baseline.get("target_col")
    train_default_rate = baseline.get("train_default_rate")
    if target_col and train_default_rate is not None and target_col in new_df.columns:
        window_default_rate = float(new_df[target_col].mean())
        delta_pp = (window_default_rate - train_default_rate) * 100.0
        status = (
            "ALERT" if abs(delta_pp) >= thresholds["default_rate_swing_pp"] else "OK"
        )
        alert = alert or (status == "ALERT")
        result["checks"].append(
            {
                "metric": "default_rate_swing_pp",
                "value": round(delta_pp, 3),
                "status": status,
            }
        )
    else:
        result["checks"].append(
            {
                "metric": "default_rate_swing_pp",
                "value": None,
                "status": "NOT_COMPUTABLE",
                "detail": f"no '{target_col}' column in this batch -- outcomes not yet realized/labeled",
            }
        )

    for feat in baseline.get("psi_top_n_features", []):
        edges = baseline.get("quantile_bin_edges", {}).get(feat)
        train_pct = baseline.get("train_bin_pct", {}).get(feat)
        if edges is None or feat not in new_df.columns:
            continue
        # NOTE: this expects an already-numeric column (categorical features
        # encoded exactly as this suite's serving layer does it -- see
        # src/serving/scoring_service_common.py's load_bundle()/OrdinalEncoder
        # convention). A still-raw string column is reported as
        # NOT_COMPUTABLE rather than crashing the whole job.
        try:
            window_pct = bin_share(edges, new_df[feat].to_numpy(dtype=float))
            psi_value = psi_from_bin_pct(train_pct, window_pct)
            status = _psi_status(psi_value, thresholds)
            alert = alert or (status == "ALERT")
            result["checks"].append(
                {
                    "metric": f"psi::{feat}",
                    "value": round(psi_value, 4) if psi_value is not None else None,
                    "window_bin_pct": window_pct,
                    "status": status,
                }
            )
        except (TypeError, ValueError) as exc:
            result["checks"].append(
                {
                    "metric": f"psi::{feat}",
                    "value": None,
                    "status": "NOT_COMPUTABLE",
                    "detail": f"column not numeric/encoded: {exc}",
                }
            )

    write_header = not Path(args.out_log).exists()
    with open(args.out_log, "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(
                ["run_at_utc", "new_data_csv", "model_name", "n_rows", "any_alert"]
            )
        writer.writerow(
            [
                result["run_at_utc"],
                result["new_data_csv"],
                result["model_name"],
                result["n_rows"],
                alert,
            ]
        )

    print(json.dumps(result, indent=2))
    sys.exit(1 if alert else 0)


if __name__ == "__main__":
    main()
