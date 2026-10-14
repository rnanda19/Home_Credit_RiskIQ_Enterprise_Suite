"""
Real load test for MP2 Problem 2 (stress_testing_service.py) -- a second
real, no-trained-model, closed-form Basel service (same family as MP2
Problem 1's committed locustfile), but with a real path-parameterized
endpoint (/score/{scenario}) and its own real StressRequest schema. Cycles
through all 3 real, cited scenarios so each is actually exercised, not
just "Baseline".
"""

import random

from locust import HttpUser, between, events, task

_SCENARIOS = ["Baseline", "Adverse", "Severely Adverse"]
_CONTRACT_TYPES = ["Cash loans", "Revolving loans"]
_FLAGS = ["Y", "N"]


class StressTestingUser(HttpUser):
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
        scenario = random.choice(_SCENARIOS)
        payload = {
            "PD": round(random.uniform(0.001, 0.25), 4),
            "AMT_CREDIT": round(random.uniform(50_000, 1_000_000), 2),
            "NAME_CONTRACT_TYPE": random.choice(_CONTRACT_TYPES),
            "FLAG_OWN_REALTY": random.choice(_FLAGS),
            "FLAG_OWN_CAR": random.choice(_FLAGS),
        }
        self.client.post(f"/score/{scenario}", json=payload, headers=self.auth_header, name="/score/{scenario}")

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
