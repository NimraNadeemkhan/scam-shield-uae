import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from scamshield import api  # noqa: E402
from scamshield.ratelimit import SlidingWindowLimiter  # noqa: E402


@pytest.fixture()
def client():
    api.limiter = SlidingWindowLimiter(max_requests=30, window_seconds=60)
    return TestClient(api.app)


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_check_returns_structured_result(client):
    r = client.post("/check", json={"message": "Pay a fee for your parcel https://bit.ly/x"})
    assert r.status_code == 200
    body = r.json()
    assert body["verdict"] == "verify" and body["disclaimer"]


def test_rejects_empty_and_oversized_and_malformed(client):
    assert client.post("/check", json={"message": ""}).status_code == 422
    assert client.post("/check", json={"message": "x" * 2001}).status_code == 422
    assert client.post("/check", json={}).status_code == 422
    assert client.post("/check", content="not json").status_code == 422


def test_rate_limit(client):
    api.limiter = SlidingWindowLimiter(max_requests=2, window_seconds=60)
    codes = [client.post("/check", json={"message": "hi"}).status_code for _ in range(3)]
    assert codes == [200, 200, 429]


def test_message_is_not_echoed(client):
    secret = "my-unique-secret-token-12345"
    r = client.post("/check", json={"message": f"hello {secret}"})
    assert secret not in r.text
