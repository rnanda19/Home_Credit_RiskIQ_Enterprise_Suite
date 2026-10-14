"""
Generic real load test for any MP1/MP4 scoring service built on the shared
scoring_service_common factory (or a hand-built equivalent with the same
/token + /score contract), pointed at the CI fixture classifier bundle
(scripts/generate_ci_fixture_bundles.py's scoring_bundle(): feature_cols =
["ci_fixture_feature_1", "ci_fixture_feature_2"]) -- the exact same real
auth + real rate limiting + real payload shape as MP1 Problem 1's and MP2
Problem 1's own locustfiles already committed in this suite's
LOAD_TESTING.md. Reused unmodified across every scoring-shaped service in
this Phase 4.1 pass; only --host changes per service.
"""

import random

from locust import HttpUser, between, events, task

FIXTURE_FEATURES = ["ci_fixture_feature_1", "ci_fixture_feature_2"]


class ScoringServiceUser(HttpUser):
    wait_time = between(0.1, 0.5)

    def on_start(self):
        resp = self.client.post(
            "/token",
            data={"username": "loadtest", "password": self.environment.parsed_options.api_key},
            name="/token",
        )
        token = resp.json().get("access_token") if resp.status_code == 200 else None
        self.auth_header = {"Authorization": f"Bearer {token}"} if token else {}

    @task(5)
    def score(self):
        payload = {f: random.uniform(-2.0, 2.0) for f in FIXTURE_FEATURES}
        self.client.post("/score", json=payload, headers=self.auth_header, name="/score")

    @task(1)
    def health(self):
        self.client.get("/health", name="/health")


@events.init_command_line_parser.add_listener
def _add_api_key_arg(parser):
    parser.add_argument(
        "--api-key",
        type=str,
        env_var="LOADTEST_API_KEY",
        default="e2e-pytest-only-test-key",
    )
