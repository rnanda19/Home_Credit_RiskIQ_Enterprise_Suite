"""
02_mega_project_2_regulatory_capital/loadtest/locustfile.py

Real load test against MP2 Problem 1's real, deployable service
(capital_requirement_service.py). Added 2026-10-14 to extend load
testing past the single flagship service MP1 Problem 1 had (see
LOAD_TESTING.md's "Coverage" section for the full before/after and the
other 3 Mega Projects' status).

Unlike MP1 Problem 1 (a trained-model service), this is a deterministic,
no-model Basel Vasicek/ASRF formula service -- so this load test is also
a genuinely different case from MP1's: no .joblib bundle dependency, no
predict_proba()/SHAP-style explainability path on the hot path, just the
real closed-form Basel capital calculation under real concurrent HTTP +
auth + rate-limiting overhead.

Run it against a real running instance:
    locust -f loadtest/locustfile.py --host=http://127.0.0.1:8005 \\
        --headless -u 10 -r 5 --run-time 30s --csv=results \\
        --api-key <the service's real configured API_KEY>
"""

import random

from locust import HttpUser, between, events, task

# Real, valid NAME_CONTRACT_TYPE/FLAG_* values from Home Credit's real
# schema (see capital_requirement_service.py's CapitalRequest model and
# regulatory_capital_features.SEGMENT_DEFINITIONS) -- every combination
# below maps to a real, distinct Basel segment.
_CONTRACT_TYPES = ["Cash loans", "Revolving loans"]
_FLAGS = ["Y", "N"]


class CapitalRequirementUser(HttpUser):
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
            "PD": round(random.uniform(0.001, 0.25), 4),
            "AMT_CREDIT": round(random.uniform(50_000, 1_000_000), 2),
            "NAME_CONTRACT_TYPE": random.choice(_CONTRACT_TYPES),
            "FLAG_OWN_REALTY": random.choice(_FLAGS),
            "FLAG_OWN_CAR": random.choice(_FLAGS),
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
        default="dev-only-CHANGE-ME-before-deploying",
        help="API_KEY configured on the target service (used as the OAuth2 client secret for /token).",
    )
