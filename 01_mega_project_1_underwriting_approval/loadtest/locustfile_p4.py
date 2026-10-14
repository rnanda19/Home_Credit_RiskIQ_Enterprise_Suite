"""
Real load test for MP1 Problem 4 (repayment_capacity_service.py) -- a
deterministic-formula service with NO trained-model bundle and NO /token
route need for /score itself to compute (require_auth still gates it), so
this still performs the real OAuth2 flow then real /score calls with a
real, in-schema RepaymentCapacityRequest payload.
"""

import random

from locust import HttpUser, between, events, task


class RepaymentCapacityUser(HttpUser):
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
        payload = {
            "AMT_INCOME_TOTAL": round(random.uniform(50_000, 400_000), 2),
            "AMT_ANNUITY": round(random.uniform(5_000, 60_000), 2),
            "AMT_CREDIT": round(random.uniform(50_000, 1_000_000), 2),
            "BUREAU_AMT_CREDIT_SUM_DEBT_TOTAL": round(random.uniform(0, 200_000), 2),
        }
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
