"""
Real load test for MP3 Problem 1 (risk_tier_assignment_service.py) -- no
model bundle, real CART-derived tier boundaries loaded from
notebook_01_summary.json (CI fixture: tier_bin_edges [None, 0.3, 0.6,
None], written by generate_ci_fixture_bundles.py). Real /score calls with
a real, in-range PD payload.
"""

import random

from locust import HttpUser, between, events, task


class RiskTierUser(HttpUser):
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
        payload = {"PD": round(random.uniform(0.0, 1.0), 4)}
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
