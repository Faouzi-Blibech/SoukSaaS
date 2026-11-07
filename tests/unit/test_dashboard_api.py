from pathlib import Path

import httpx
import pytest

from dashboard import api


def test_token_header_and_json(monkeypatch):
    monkeypatch.setenv("OWNER_TOKEN", "secret-test")
    seen = {}

    def handler(req: httpx.Request) -> httpx.Response:
        seen["token"] = req.headers.get("X-Owner-Token")
        seen["query"] = req.url.query.decode()
        return httpx.Response(200, json=[{"id": "a"}])

    out = api.request(
        "GET", "/owner/audit", params={"limit": 5}, transport=httpx.MockTransport(handler)
    )
    assert out == [{"id": "a"}]
    assert seen == {"token": "secret-test", "query": "limit=5"}


def test_http_error_raises_api_error():
    t = httpx.MockTransport(lambda r: httpx.Response(401, json={"detail": "bad"}))
    with pytest.raises(api.ApiError):
        api.request("GET", "/owner/kpis", transport=t)


def test_connection_error_mentions_url(monkeypatch):
    monkeypatch.setenv("API_URL", "http://127.0.0.1:1")

    def boom(req):
        raise httpx.ConnectError("down")

    with pytest.raises(api.ApiError, match="Backend not reachable at http://127.0.0.1:1"):
        api.request("GET", "/owner/kpis", transport=httpx.MockTransport(boom))


def test_pages_render_with_backend_down(monkeypatch):
    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv("API_URL", "http://127.0.0.1:1")
    at = AppTest.from_file(
        str(Path(__file__).resolve().parents[2] / "dashboard" / "app.py"), default_timeout=30
    ).run()
    assert not at.exception
    for page in [
        "Approvals",
        "Q&A manager",
        "Insights",
        "Security & Evals",
        "Simulator",
        "Live feed",
    ]:
        at.sidebar.radio[0].set_value(page).run()
        assert not at.exception, page
    assert at.error
