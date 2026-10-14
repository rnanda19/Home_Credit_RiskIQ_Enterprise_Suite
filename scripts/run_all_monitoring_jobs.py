#!/usr/bin/env python3
"""
scripts/run_all_monitoring_jobs.py

Added 2026-10-14 (Phase 2 hardening) to close the gap MONITORING.md
itself discloses: monitoring was "wired for one flagship model" (MP1
Problem 1) with no live scheduler, and extending to another model meant
manually constructing and scheduling its own `monitoring_job.py`
invocation by hand. This script is the generic, multi-model runner that
was missing: it discovers every `*/monitoring/*_config.json` that has a
matching `*_baseline.json` next to it (i.e. every model that has actually
been onboarded -- see generate_monitoring_baseline.py), runs
`monitoring_job.py` for each one against its own new-data CSV, and
aggregates the results into one real exit code and one real summary --
so scheduling "all of production drift monitoring" is one command and
one cron/Task Scheduler entry, not N of them.

THIS DOES NOT INVENT BASELINES. A model with no committed
`*_baseline.json` (which, as of 2026-10-14, is every model in this
suite -- see MONITORING.md: even MP1 Problem 1's own baseline has not
been generated yet, because this build environment has no real,
downloaded Kaggle dataset to generate it from) is reported as
NOT_ONBOARDED, never silently skipped without being counted, and never
treated as a passing check.

Usage:
    # one new-data CSV per onboarded model, keyed by its config.json's
    # own path (matching the per-model --new-data-csv monitoring_job.py
    # already requires -- this script does not guess which CSV belongs
    # to which model):
    python scripts/run_all_monitoring_jobs.py \\
        --new-data-csv 01_mega_project_1_underwriting_approval/monitoring/mp1_01_config.json=path/to/mp1_batch.csv \\
        --new-data-csv 04_mega_project_4_delinquency_prevention/monitoring/mp4_01_config.json=path/to/mp4_batch.csv

    # discover onboarded models without running anything (a dry run --
    # also what the scheduled CI workflow uses to report onboarding
    # status without fabricating a monitoring result against no data):
    python scripts/run_all_monitoring_jobs.py --list-only
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MONITORING_JOB = REPO_ROOT / "src" / "monitoring" / "monitoring_job.py"


def discover_onboarded_models() -> list[dict]:
    """Every */monitoring/*_config.json in the repo, paired with its
    sibling *_baseline.json if one exists. A config with no baseline is
    real (a real, committed policy-threshold file) but NOT ONBOARDED --
    there is nothing yet to monitor it against."""
    models = []
    for config_path in sorted(REPO_ROOT.glob("*/monitoring/*_config.json")):
        baseline_path = Path(str(config_path).replace("_config.json", "_baseline.json"))
        models.append(
            {
                "project": config_path.parent.parent.name,
                "config": config_path,
                "baseline": baseline_path if baseline_path.exists() else None,
                "onboarded": baseline_path.exists(),
            }
        )
    return models


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--new-data-csv",
        action="append",
        default=[],
        metavar="CONFIG_JSON_PATH=NEW_DATA_CSV_PATH",
        help="Repeatable. Maps one onboarded model's config.json to the new-data CSV to check it against this run.",
    )
    parser.add_argument("--list-only", action="store_true", help="Report onboarding status for every model found and exit -- runs nothing.")
    args = parser.parse_args()

    models = discover_onboarded_models()
    csv_map = {}
    for pair in args.new_data_csv:
        if "=" not in pair:
            print(f"ERROR: --new-data-csv expects CONFIG_JSON_PATH=NEW_DATA_CSV_PATH, got: {pair}", file=sys.stderr)
            return 2
        k, v = pair.split("=", 1)
        csv_map[str((REPO_ROOT / k).resolve())] = v

    if not models:
        print("No */monitoring/*_config.json files found in this repo.")
        return 0

    print(f"Discovered {len(models)} model(s) with a committed monitoring config:\n")
    results = []
    for m in models:
        rel_config = m["config"].relative_to(REPO_ROOT)
        if not m["onboarded"]:
            print(f"  NOT_ONBOARDED  {m['project']:<45} {rel_config}  (no *_baseline.json committed -- see generate_monitoring_baseline.py)")
            results.append({"project": m["project"], "config": str(rel_config), "status": "NOT_ONBOARDED"})
            continue

        config_key = str(m["config"].resolve())
        if args.list_only:
            print(f"  ONBOARDED      {m['project']:<45} {rel_config}")
            results.append({"project": m["project"], "config": str(rel_config), "status": "ONBOARDED (not run -- --list-only)"})
            continue

        new_data_csv = csv_map.get(config_key)
        if new_data_csv is None:
            print(f"  BLOCKED        {m['project']:<45} {rel_config}  (onboarded, but no --new-data-csv given for it this run)")
            results.append({"project": m["project"], "config": str(rel_config), "status": "BLOCKED"})
            continue

        baseline_rel = m["baseline"].relative_to(REPO_ROOT)
        out_log = m["baseline"].parent / (m["baseline"].stem.replace("_baseline", "") + "_job_log.csv")
        cmd = [
            sys.executable,
            str(MONITORING_JOB),
            "--new-data-csv", new_data_csv,
            "--baseline-json", str(baseline_rel),
            "--config-json", str(rel_config),
            "--out-log", str(out_log.relative_to(REPO_ROOT)),
        ]
        proc = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True)
        status = "OK" if proc.returncode == 0 else "ALERT"
        print(f"  {status:<14} {m['project']:<45} {rel_config}")
        if proc.returncode != 0:
            detail = proc.stderr.strip()
            try:
                payload = json.loads(proc.stdout)
                alerting = [c for c in payload.get("checks", []) if c.get("status") == "ALERT"]
                if alerting:
                    detail = "; ".join(f"{c['metric']}={c.get('value')}" for c in alerting)
            except (json.JSONDecodeError, KeyError):
                pass
            print(f"                 ALERT detail: {detail}")
        results.append({"project": m["project"], "config": str(rel_config), "status": status})

    n_alert = sum(1 for r in results if r["status"] == "ALERT")
    n_onboarded = sum(1 for r in results if r["status"] not in ("NOT_ONBOARDED",))
    print(f"\n{n_onboarded}/{len(results)} model(s) onboarded. {n_alert} ALERT.")
    return 1 if n_alert > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
