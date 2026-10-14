"""
Generic real load test for any segment_assignment_common-built service
(MP3 Problems 2/3/4, MP4 Problem 2, MP5 Problem 4), pointed at the CI
fixture segmentation bundle (segment_bundle(): feature_names =
["ci_fixture_feature_1", "ci_fixture_feature_2"]) -- same real auth +
rate-limit + payload shape as the scoring-service locustfile, since
build_segment_app()'s dynamically-built RequestModel uses the bundle's own
feature_names, identical field names to the CI fixture classifier bundle.
"""

import random

from locust import HttpUser, between, events, task

FIXTURE_FEATURES = ["ci_fixture_feature_1", "ci_fixture_feature_2"]


class SegmentServiceUser(HttpUser):
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
