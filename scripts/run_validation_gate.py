#!/usr/bin/env python3
"""
scripts/run_validation_gate.py

Added 2026-10-14 (Phase 2 hardening). A single command that runs this
suite's real evidence-gathering checks and writes validation-results.json
at the repo root -- one file, machine-readable, carrying the commit SHA
it was run against and a truthful PASS/FAIL/BLOCKED/NOT RUN verdict for
every check, instead of evidence scattered across ad-hoc terminal output
that nobody can diff between runs.

    python scripts/run_validation_gate.py
    python scripts/run_validation_gate.py --out validation-results.json

STATUS MEANINGS (assigned honestly -- this script never upgrades a
status to make a run look better than it was):
    PASS    -- the check ran to completion and every assertion inside it
               succeeded.
    FAIL    -- the check ran to completion and at least one assertion
               failed.
    BLOCKED -- the check could not run for a reason outside this suite's
               own code (a real .joblib bundle is gitignored and not
               present on this machine yet because its notebook hasn't
               been (re-)run; a tool this check depends on is not
               installed). BLOCKED is never silently treated as PASS.
    NOT RUN -- this script chose not to attempt the check at all (e.g.
               --skip-pip-audit was passed, or no network for pip-audit
               to query its vulnerability feed).

EXIT CODE (2026-10-14: now 3-valued, not a PASS/non-PASS boolean -- see
the comment above the return statement in main() for why. The original
"0 if PASS else 1" collapsed BLOCKED into the same code as FAIL, which
made the CI validation-gate job fail on every single run: on a fresh CI
checkout the real .joblib bundles are gitignored and simply do not
exist, so check_bundle_sklearn_version() is BLOCKED there by design,
forever. A CI step should fail the build on FAIL, not on BLOCKED):
    0 -- overall PASS.
    1 -- overall FAIL (at least one check actually ran and found a real
         problem). This is the only code that should block a CI build.
    2 -- overall BLOCKED, no FAIL (every check either passed or could
         not run for a reason outside this suite's own code).
         validation-results.json still records BLOCKED truthfully --
         only the exit code treats it as non-fatal to the build.

This script does not invent new test assertions -- it is a runner and
aggregator around the suite's existing real pytest suites, the real
.joblib bundles on disk, and pip-audit, all of which can be independently
re-run by hand using the exact commands this script itself uses (printed
in each check's "command" field in the JSON output).
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

MEGA_PROJECTS = [
    "01_mega_project_1_underwriting_approval",
    "02_mega_project_2_regulatory_capital",
    "03_mega_project_3_risk_segmentation",
    "04_mega_project_4_delinquency_prevention",
    "05_mega_project_5_liquidity_cashflow",
]


def _run(cmd: list[str], cwd: Path | None = None, env: dict | None = None) -> tuple[int, str]:
    import os

    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd or REPO_ROOT),
            env=full_env,
            capture_output=True,
            text=True,
            timeout=600,
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode, output
    except FileNotFoundError as e:
        return 127, str(e)
    except subprocess.TimeoutExpired as e:
        return 124, f"TIMEOUT after {e.timeout}s"


def _git_sha() -> str:
    code, out = _run(["git", "rev-parse", "HEAD"])
    return out.strip() if code == 0 else "UNKNOWN"


def _git_branch() -> str:
    code, out = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    return out.strip() if code == 0 else "UNKNOWN"


def _tail(text: str, n: int = 40) -> str:
    lines = text.strip().splitlines()
    return "\n".join(lines[-n:])


def check_shared_tests() -> dict:
    cmd = [sys.executable, "-m", "pytest", "src/tests/", "-q"]
    t0 = time.time()
    code, out = _run(cmd)
    status = "PASS" if code == 0 else "FAIL"
    return {
        "name": "shared_tests",
        "description": "src/tests/ -- HYPER shared-library tests (auth, rate limiting, explainability, monitoring, scoring/segment common code). No business data or notebook artifacts required.",
        "command": " ".join(cmd),
        "status": status,
        "duration_s": round(time.time() - t0, 2),
        "evidence": _tail(out),
    }


def check_project_tests(project: str) -> dict:
    project_dir = REPO_ROOT / project
    tests_dir = project_dir / "tests"
    if not tests_dir.exists():
        return {
            "name": f"{project}_tests",
            "description": f"{project}/tests/",
            "command": None,
            "status": "NOT RUN",
            "duration_s": 0,
            "evidence": "No tests/ directory found for this project.",
        }
    cmd = [sys.executable, "-m", "pytest", "tests/", "-v"]
    import os

    env = {"PYTHONPATH": f"{project_dir / 'services'}:{REPO_ROOT / 'src'}:{REPO_ROOT}:{os.environ.get('PYTHONPATH', '')}"}
    t0 = time.time()
    code, out = _run(cmd, cwd=project_dir, env=env)
    n_skipped = out.count(" SKIPPED")
    n_total = out.count("PASSED") + out.count("FAILED") + n_skipped
    if code != 0:
        status = "FAIL"
    elif n_total > 0 and n_skipped == n_total:
        # every collected test skipped -- real bundles/fixtures not present
        # on this machine (gitignored by design). Not a failure of this
        # suite's own code, but not a verified PASS either.
        status = "BLOCKED"
    else:
        status = "PASS"
    return {
        "name": f"{project}_tests",
        "description": f"{project}/tests/ -- scoring-service + e2e-live-service tests. Real .joblib bundles are gitignored; tests gated on them report BLOCKED (not PASS) when the bundle is absent on this machine.",
        "command": " ".join(cmd) + f"  (run from {project}/)",
        "status": status,
        "duration_s": round(time.time() - t0, 2),
        "evidence": _tail(out),
    }


def check_bundle_sklearn_version() -> dict:
    """Loads every real .joblib bundle present on this machine under the
    currently-installed scikit-learn and reports whether any of them
    triggers sklearn.exceptions.InconsistentVersionWarning (the exact,
    real symptom of the dependency-drift bug constraints.txt exists to
    prevent -- see VALIDATION_REPORT.md section 8)."""
    bundles = sorted(REPO_ROOT.glob("*/decision_engine/artifacts/*.joblib"))
    if not bundles:
        return {
            "name": "bundle_sklearn_version_consistency",
            "description": "Loads every real .joblib bundle under the installed scikit-learn and checks for InconsistentVersionWarning.",
            "command": None,
            "status": "BLOCKED",
            "duration_s": 0,
            "evidence": "No .joblib bundles found on this machine (they are gitignored; run the relevant notebooks first to generate them).",
        }
    script = (
        "import joblib, warnings, sys\n"
        "bad = []\n"
        f"files = {[str(b) for b in bundles]!r}\n"
        "for fp in files:\n"
        "    with warnings.catch_warnings(record=True) as w:\n"
        "        warnings.simplefilter('always')\n"
        "        try:\n"
        "            joblib.load(fp)\n"
        "        except Exception as e:\n"
        "            bad.append(f'{fp}: LOAD ERROR: {e}')\n"
        "            continue\n"
        "        for warn in w:\n"
        "            if 'Inconsistent' in warn.category.__name__:\n"
        "                bad.append(f'{fp}: {warn.message}')\n"
        "print(f'checked {len(files)} bundle(s)')\n"
        "for b in bad:\n"
        "    print('FINDING:', b)\n"
        "sys.exit(1 if bad else 0)\n"
    )
    t0 = time.time()
    code, out = _run([sys.executable, "-c", script])
    return {
        "name": "bundle_sklearn_version_consistency",
        "description": "Loads every real .joblib bundle under the installed scikit-learn and checks for InconsistentVersionWarning.",
        "command": "python -c \"<loads every */decision_engine/artifacts/*.joblib and checks for InconsistentVersionWarning>\"",
        "status": "PASS" if code == 0 else "FAIL",
        "duration_s": round(time.time() - t0, 2),
        "evidence": _tail(out),
    }


def check_pip_audit(skip: bool) -> dict:
    if skip:
        return {
            "name": "pip_audit",
            "description": "pip-audit against constraints.txt, honoring security/pip-audit-exceptions.txt.",
            "command": None,
            "status": "NOT RUN",
            "duration_s": 0,
            "evidence": "Skipped via --skip-pip-audit.",
        }
    if shutil.which("pip-audit") is None and _run([sys.executable, "-m", "pip_audit", "--version"])[0] != 0:
        return {
            "name": "pip_audit",
            "description": "pip-audit against constraints.txt, honoring security/pip-audit-exceptions.txt.",
            "command": None,
            "status": "BLOCKED",
            "duration_s": 0,
            "evidence": "pip-audit is not installed in this environment (`pip install pip-audit`) and/or no network access to query the vulnerability feed.",
        }
    ignore_ids = []
    exceptions_file = REPO_ROOT / "security" / "pip-audit-exceptions.txt"
    if exceptions_file.exists():
        import re

        for line in exceptions_file.read_text().splitlines():
            m = re.match(r"^(CVE|PYSEC)-[A-Za-z0-9-]+", line.strip())
            if m:
                ignore_ids.append(m.group(0))
    cmd = [sys.executable, "-m", "pip_audit", "-r", "constraints.txt"]
    for vid in ignore_ids:
        cmd += ["--ignore-vuln", vid]
    t0 = time.time()
    code, out = _run(cmd)
    return {
        "name": "pip_audit",
        "description": "pip-audit against constraints.txt, honoring security/pip-audit-exceptions.txt.",
        "command": " ".join(cmd),
        "status": "PASS" if code == 0 else "FAIL",
        "duration_s": round(time.time() - t0, 2),
        "evidence": _tail(out),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(REPO_ROOT / "validation-results.json"))
    parser.add_argument("--skip-pip-audit", action="store_true")
    parser.add_argument("--skip-project-tests", action="store_true", help="Run only src/tests/ and the bundle check (fast loop).")
    args = parser.parse_args()

    checks = [check_shared_tests()]
    if not args.skip_project_tests:
        for project in MEGA_PROJECTS:
            checks.append(check_project_tests(project))
    checks.append(check_bundle_sklearn_version())
    checks.append(check_pip_audit(args.skip_pip_audit))

    counts = {"PASS": 0, "FAIL": 0, "BLOCKED": 0, "NOT RUN": 0}
    for c in checks:
        counts[c["status"]] += 1

    result = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "commit_sha": _git_sha(),
        "branch": _git_branch(),
        "checks": checks,
        "summary": {
            **counts,
            "total": len(checks),
            "overall": "FAIL" if counts["FAIL"] > 0 else ("BLOCKED" if counts["BLOCKED"] > 0 else "PASS"),
        },
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(result, indent=2) + "\n")

    print(f"\n=== validation gate: {result['summary']['overall']} ===")
    for c in checks:
        print(f"  [{c['status']:<8}] {c['name']}")
    print(f"\nWrote {out_path}")

    # Exit codes are deliberately 3-valued, not a PASS/non-PASS boolean:
    #   0 -- PASS: every attempted check succeeded.
    #   1 -- FAIL: at least one check actually ran and found a real problem.
    #      This is the only code a CI step should treat as "block the build".
    #   2 -- BLOCKED, no FAIL: every check either passed or could not run for
    #      a reason outside this suite's own code (most commonly: real
    #      .joblib bundles are gitignored and simply do not exist on a fresh
    #      CI checkout -- see check_bundle_sklearn_version()'s own docstring).
    #      Added 2026-10-14 after the validation-gate CI job was found to
    #      fail on every single run for exactly this reason, even when
    #      nothing was actually broken: collapsing BLOCKED into the same
    #      exit code as FAIL made the gate permanently red and therefore
    #      meaningless as a signal. BLOCKED is still never silently reported
    #      as PASS in validation-results.json -- only the exit code, which a
    #      CI step uses to decide whether to block the build, treats it
    #      differently from a genuine FAIL.
    if result["summary"]["overall"] == "PASS":
        return 0
    if result["summary"]["overall"] == "FAIL":
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
