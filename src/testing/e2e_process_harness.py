"""
src/testing/e2e_process_harness.py

HYPER shared component: launches a real, deployable FastAPI service the same
way this suite's own `README.md`/`docker/Dockerfile` tells a human to run it
-- `uvicorn <module>:app --host 127.0.0.1 --port <N>` as a real OS subprocess,
binding a real TCP socket -- so a test built on this harness talks to the
service over real HTTP (real sockets, real serialization, real process
startup/shutdown), not FastAPI's `TestClient`, which calls the ASGI app
in-process and never opens a socket at all.

Real, previously-disclosed gap this closes: "No end-to-end integration test
suite exists -- every existing service test uses in-process `TestClient`,
which never exercises the real `uvicorn` startup path, real networking, or
real process lifecycle a Docker container (or `README.md`'s own documented
`uvicorn ...` command) actually goes through." `TestClient`-based tests
(`test_scoring_services.py` in every Mega Project, `test_rate_limit_common.py`,
`test_adverse_action_endpoint.py`) remain valuable and are NOT replaced --
they are fast, precise, bit-identical-output checks. This harness adds the
real round trip those tests cannot provide, without duplicating them.

Built once here, imported by every Mega Project's own end-to-end test file
-- not copy-pasted per service, the same HYPER pattern as
`serving.scoring_service_common`/`serving.segment_assignment_common`
themselves.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

import requests

SUITE_ROOT = Path(__file__).resolve().parents[2]


class ServiceStartupError(RuntimeError):
    """Raised when a real subprocess-launched service never became healthy
    within the allotted time -- carries the real captured stdout/stderr so a
    failure here is diagnosable, not just a bare timeout."""


@contextmanager
def run_service_subprocess(
    module_name: str,
    service_dir: Path,
    port: int,
    env_overrides: Optional[dict] = None,
    startup_timeout: float = 20.0,
    health_path: str = "/health",
) -> Iterator[str]:
    """Starts `uvicorn <module_name>:app` as a real subprocess on
    `127.0.0.1:<port>`, polls the real `health_path` over real HTTP until it
    answers (or `startup_timeout` elapses), yields the service's real
    `base_url`, and guarantees real process teardown afterward -- even if the
    caller's test body raises.

    `env_overrides` is merged over a real copy of this process's own
    environment, with `PYTHONPATH` set so the subprocess can import both this
    suite's shared `src/` modules and the target service module itself,
    exactly like the service's own module-level `sys.path.insert()` calls do
    when run directly -- see e.g. `credit_default_scoring_service.py`.
    """
    full_env = os.environ.copy()
    existing_pythonpath = full_env.get("PYTHONPATH", "")
    path_parts = [str(SUITE_ROOT / "src"), str(service_dir)]
    if existing_pythonpath:
        path_parts.append(existing_pythonpath)
    full_env["PYTHONPATH"] = os.pathsep.join(path_parts)
    if env_overrides:
        full_env.update(env_overrides)

    base_url = f"http://127.0.0.1:{port}"
    log_file = tempfile.NamedTemporaryFile(
        mode="w+", prefix=f"e2e_{module_name}_", suffix=".log", delete=False
    )
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            f"{module_name}:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=str(service_dir),
        env=full_env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        deadline = time.monotonic() + startup_timeout
        healthy = False
        while time.monotonic() < deadline:
            if process.poll() is not None:
                break  # the real process exited before ever becoming healthy
            try:
                resp = requests.get(f"{base_url}{health_path}", timeout=1)
                if resp.status_code == 200:
                    healthy = True
                    break
            except requests.exceptions.ConnectionError:
                pass
            time.sleep(0.25)

        if not healthy:
            log_file.flush()
            log_file.seek(0)
            captured = log_file.read()
            raise ServiceStartupError(
                f"{module_name} never became healthy on {base_url}{health_path} "
                f"within {startup_timeout}s (exit code: {process.poll()}).\n"
                f"--- real captured subprocess output ---\n{captured}"
            )

        yield base_url
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        log_file.close()
        try:
            os.unlink(log_file.name)
        except OSError:
            pass
