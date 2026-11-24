from __future__ import annotations

import asyncio
import json
from typing import Any, Callable, List, Type

import httpx
import pytest

import trackified
from trackified import AsyncTrackified, Trackified

TRACKING = {"id": "trk_1", "tracking_number": "9434650110837017316201", "status": "in_transit"}


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch: pytest.MonkeyPatch) -> List[float]:
    slept: List[float] = []

    async def fake_async_sleep(s: float) -> None:
        slept.append(s)

    monkeypatch.setattr("trackified._client.time.sleep", slept.append)
    monkeypatch.setattr("trackified._client.asyncio.sleep", fake_async_sleep)
    return slept


def make(handler: Callable[[httpx.Request], httpx.Response], **kw: Any) -> Trackified:
    return Trackified(
        "tk_test_abc", http_client=httpx.Client(transport=httpx.MockTransport(handler)), **kw
    )


def err(status: int, code: str = "x", headers: Any = None) -> httpx.Response:
    body = {"error": {"code": code, "message": "nope", "request_id": "req_1"}}
    return httpx.Response(status, json=body, headers=headers)


def test_auth_headers_and_create() -> None:
    seen: List[httpx.Request] = []

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        return httpx.Response(201, json=TRACKING)

    t = make(handler).trackings.create("9434650110837017316201", carrier="usps")
    assert t["id"] == "trk_1"
    req = seen[0]
    assert req.method == "POST"
    assert str(req.url) == "https://api.trackified.net/v1/trackings"
    assert req.headers["authorization"] == "Bearer tk_test_abc"
    assert req.headers["user-agent"] == f"trackified-python/{trackified.__version__}"
    assert len(req.headers["idempotency-key"]) == 36
    assert json.loads(req.content) == {
        "tracking_number": "9434650110837017316201",
        "carrier": "usps",
    }


def test_env_fallbacks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRACKIFIED_API_KEY", "tk_env")
    monkeypatch.setenv("TRACKIFIED_BASE_URL", "http://localhost:1/")
    c = Trackified()
    assert c._client.api_key == "tk_env"
    assert c._client.base_url == "http://localhost:1"
    monkeypatch.delenv("TRACKIFIED_API_KEY")
    with pytest.raises(trackified.TrackifiedError):
        Trackified()


def test_idempotency_key_reused_across_retries(no_sleep: List[float]) -> None:
    keys: List[str] = []

    def handler(req: httpx.Request) -> httpx.Response:
        keys.append(req.headers["idempotency-key"])
        return err(503) if len(keys) < 3 else httpx.Response(201, json=TRACKING)

    make(handler).trackings.create("1")
    assert len(keys) == 3 and len(set(keys)) == 1
    assert len(no_sleep) == 2

    keys.clear()
    make(handler).trackings.create_bulk([{"tracking_number": "1"}], idempotency_key="mine")
    assert keys == ["mine"] * 3


def test_retry_after_honoured(no_sleep: List[float]) -> None:
    calls = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append(1)
        return (
            err(429, headers={"retry-after": "7"})
            if len(calls) == 1
            else httpx.Response(200, json=TRACKING)
        )

    make(handler).trackings.get("trk_1")
    assert no_sleep == [7.0]


def test_rate_limit_error_after_retries() -> None:
    calls = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append(1)
        return err(429, "rate_limited", headers={"retry-after": "2"})

    with pytest.raises(trackified.RateLimitError) as e:
        make(handler).trackings.get("trk_1")
    assert len(calls) == 3
    assert e.value.retry_after == 2.0
    assert (
        e.value.status == 429 and e.value.code == "rate_limited" and e.value.request_id == "req_1"
    )


def test_retries_408_and_network_errors() -> None:
    calls = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append(1)
        if len(calls) == 1:
            raise httpx.ConnectError("boom")
        if len(calls) == 2:
            return err(408)
        return httpx.Response(200, json=TRACKING)

    assert make(handler).trackings.get("trk_1")["id"] == "trk_1"
    assert len(calls) == 3


def test_connection_error() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    with pytest.raises(trackified.ConnectionError):
        make(handler, max_retries=0).usage.get()


@pytest.mark.parametrize(
    "status,cls",
    [
        (400, trackified.ValidationError),
        (401, trackified.AuthenticationError),
        (402, trackified.TrackifiedError),
        (403, trackified.PermissionError),
        (404, trackified.NotFoundError),
        (409, trackified.TrackifiedError),
        (422, trackified.ValidationError),
        (500, trackified.APIError),
    ],
)
def test_error_mapping_and_no_retry_on_4xx(
    status: int, cls: Type[trackified.TrackifiedError]
) -> None:
    calls = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append(1)
        return err(status, "some_code")

    with pytest.raises(cls) as e:
        make(handler).trackings.get("trk_1")
    assert e.value.status == status
    assert e.value.code == "some_code"
    assert e.value.message == "nope"
    assert e.value.request_id == "req_1"
    assert len(calls) == (3 if status >= 500 else 1)


def test_auto_paging() -> None:
    items = [{"id": f"trk_{i}"} for i in range(5)]
    offsets: List[str] = []

    def handler(req: httpx.Request) -> httpx.Response:
        offset = int(req.url.params["offset"])
        limit = int(req.url.params["limit"])
        offsets.append(req.url.params["offset"])
        assert req.url.params["status"] == "delivered"
        page = items[offset : offset + limit]
        return httpx.Response(
            200, json={"data": page, "pagination": {"limit": limit, "offset": offset, "total": 5}}
        )

    ids = [t["id"] for t in make(handler).trackings.list_auto_paging(limit=2, status="delivered")]
    assert ids == [f"trk_{i}" for i in range(5)]
    assert offsets == ["0", "2", "4"]


def test_every_operation_hits_the_right_route() -> None:
    seen: List[str] = []

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(f"{req.method} {req.url.raw_path.decode()}")
        return httpx.Response(200, json={"data": [], "pagination": {"total": 0}})

    c = make(handler)
    c.trackings.create("1")
    c.trackings.list(limit=10, carrier="usps")
    c.trackings.create_bulk([{"tracking_number": "1"}])
    c.trackings.get("trk/1")
    c.trackings.update("trk_1", custom_id="o1")
    c.trackings.delete("trk_1")
    c.trackings.retrack("trk_1")
    c.carriers.list()
    c.carriers.get("usps")
    c.carriers.detect("1Z999")
    c.carriers.catalog(q="dhl", support="api")
    c.carriers.validation_status()
    c.webhooks.create("https://example.com/h", event_types=["tracking.delivered"])
    c.webhooks.list()
    c.webhooks.delete("wh_1")
    c.webhooks.test("wh_1")
    c.webhook_deliveries.list(offset=5)
    c.api_keys.create(name="ci", mode="test")
    c.api_keys.list()
    c.api_keys.revoke("key_1")
    c.usage.get()
    assert seen == [
        "POST /v1/trackings",
        "GET /v1/trackings?limit=10&carrier=usps",
        "POST /v1/trackings/bulk",
        "GET /v1/trackings/trk%2F1",
        "PUT /v1/trackings/trk_1",
        "DELETE /v1/trackings/trk_1",
        "POST /v1/trackings/trk_1/retrack",
        "GET /v1/carriers",
        "GET /v1/carriers/usps",
        "GET /v1/carriers/detect?number=1Z999",
        "GET /v1/carriers/catalog?q=dhl&support=api",
        "GET /v1/carriers/status",
        "POST /v1/webhooks",
        "GET /v1/webhooks",
        "DELETE /v1/webhooks/wh_1",
        "POST /v1/webhooks/wh_1/test",
        "GET /v1/webhook-deliveries?offset=5",
        "POST /v1/account/api-keys",
        "GET /v1/account/api-keys",
        "DELETE /v1/account/api-keys/key_1",
        "GET /v1/account/usage",
    ]


def test_async_client() -> None:
    keys: List[str] = []
    items = [{"id": f"trk_{i}"} for i in range(3)]

    def handler(req: httpx.Request) -> httpx.Response:
        if req.method == "POST":
            keys.append(req.headers["idempotency-key"])
            return err(500) if len(keys) == 1 else httpx.Response(201, json=TRACKING)
        if req.url.path == "/v1/trackings/missing":
            return err(404)
        offset = int(req.url.params["offset"])
        return httpx.Response(
            200, json={"data": items[offset : offset + 2], "pagination": {"total": 3}}
        )

    async def run() -> None:
        http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        async with AsyncTrackified("tk_test_abc", http_client=http) as c:
            t = await c.trackings.create("1")
            assert t["id"] == "trk_1"
            assert len(keys) == 2 and keys[0] == keys[1]
            ids = [x["id"] async for x in c.trackings.list_auto_paging(limit=2)]
            assert ids == ["trk_0", "trk_1", "trk_2"]
            with pytest.raises(trackified.NotFoundError):
                await c.trackings.get("missing")
            assert c.webhooks.verify("{}", "bad", "s") is False

    asyncio.run(run())
