# Trackified Python SDK

[![CI](https://github.com/trackified/trackified-python/actions/workflows/ci.yml/badge.svg)](https://github.com/trackified/trackified-python/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/trackified)](https://pypi.org/project/trackified/)

The official Python client for the [Trackified](https://trackified.net) parcel-tracking API.
Typed, with sync and async clients, and `httpx` as its only dependency. Python 3.9+.

- API docs: https://forumulate.com/p/trackified/docs
- Webhook signing: https://trackified.net/developers/webhook-signing

## Install

```sh
pip install trackified
```

## Quickstart

```python
from trackified import Trackified

client = Trackified()  # reads TRACKIFIED_API_KEY; or Trackified("your-api-key")

# Create a tracking (leave out carrier to detect it from the number)
tracking = client.trackings.create("9434650110837017316201", carrier="usps", custom_id="order-1001")
print(tracking["id"], tracking["status"])

# Get it again, with its events (newest first, guaranteed by the API)
tracking = client.trackings.get(tracking["id"])
for event in tracking["events"]:
    print(event["occurred_at"], event["status"], event["description"])

# One page
page = client.trackings.list(limit=50, status="in_transit")
print(page["pagination"]["total"])

# Every tracking, fetching pages as needed
for t in client.trackings.list_auto_paging(status="delivered"):
    print(t["tracking_number"])
```

### Async

```python
import asyncio
from trackified import AsyncTrackified


async def main() -> None:
    async with AsyncTrackified() as client:
        tracking = await client.trackings.create("9434650110837017316201", carrier="usps")
        async for t in client.trackings.list_auto_paging():
            print(t["id"])


asyncio.run(main())
```

### Verify a webhook

Trackified signs every delivery with the `x-tracking-signature` header. Verify it against the
**raw** request body, before parsing it.

```python
import trackified

# raw_body: the request body bytes exactly as received
ok = trackified.verify(raw_body, request.headers["x-tracking-signature"], secret)

# Or verify and parse in one step (raises trackified.SignatureVerificationError):
event = trackified.construct_event(raw_body, request.headers["x-tracking-signature"], secret)
if event["type"] == "tracking.delivered":
    ...
```

The same functions are available as `client.webhooks.verify(...)` and
`client.webhooks.construct_event(...)`. Signatures older than 300 seconds are rejected; pass
`tolerance=` (seconds) to change that.

#### Typed events

`WebhookEvent` is a union of one `TypedDict` per event type; checking `event["type"]` narrows it.
`tracking.status_changed` carries `data: {tracking, previous_status, current_status}`; every other
type carries the `Tracking` itself. `tracking_of(event)` returns the Tracking for any type.

```python
if event["type"] == "tracking.status_changed":
    print(event["data"]["previous_status"], "->", event["data"]["current_status"])
tracking = trackified.tracking_of(event)
```

#### Why did verification fail?

```python
result = trackified.verify_detailed(raw_body, header, secret)
if not result.valid:
    print(result.reason)  # "missing" | "malformed" | "timestamp" | "mismatch"
```

`construct_event` raises `trackified.SignatureVerificationError` with the same `.reason`
(`WebhookVerificationError` is the 0.1 name for the same class).

#### Rotating the signing secret

```python
webhook = client.webhooks.rotate_secret("wh_123", expires_in_hours=24)  # default 24, 0..168
new_secret = webhook["secret"]  # shown once
```

Until `previous_secret_expires_at`, deliveries carry two signatures
(`t=...,v1=<new>,v1=<old>`), so receivers holding either secret keep verifying. During the window
you can pass both: `trackified.verify(raw_body, header, [new_secret, old_secret])`.
`expires_in_hours=0` drops the old secret at once.

### Update a webhook

```python
client.webhooks.update("wh_123", enabled=False)  # also url=, event_types=; secret unchanged
```

### Resolve a carrier name

```python
client.carriers.resolve("USPS Priority Mail")
# {"carrier": "usps", "name": "USPS", "confidence": 0.97, "matched": "alias"}
client.carriers.resolve("dhl_express")  # other providers' slugs work too
client.carriers.resolve("Unknown Post")  # None
```

`trackings.create(carrier=...)` accepts the same names and stores our id.

### Health

```python
client.health()  # {"status": "ok"}; a degraded API (503) raises APIError
```

## Resources

| Resource | Methods |
| --- | --- |
| `client.trackings` | `create`, `list`, `list_auto_paging`, `create_bulk`, `get`, `update`, `delete`, `retrack` |
| `client` | `health` |
| `client.carriers` | `list`, `get`, `detect`, `resolve`, `catalog`, `validation_status` |
| `client.webhooks` | `create`, `list`, `update`, `rotate_secret`, `delete`, `test`, `verify`, `verify_detailed`, `construct_event`, `tracking_of` |
| `client.webhook_deliveries` | `list` |
| `client.api_keys` | `create`, `list`, `revoke` |
| `client.usage` | `get` |

Responses are plain dicts typed as `TypedDict`s (`Tracking`, `TrackingEvent`, `Carrier`, `Webhook`,
`WebhookDelivery`, `ApiKey`, `Usage`, ...). Enums are `Literal` types: `TrackingStatus`,
`EventStatus`, `WebhookEventType`.

`usage.get()` calls `GET /v1/account/usage` (the API also answers `/v1/usage`).

Event times: `occurred_at` without an offset is the local time where the scan happened; when the
carrier gives an offset it is included and `time_zone_known` is True. `date` on events is
deprecated: it is sent until 2027-06-01 and removed after.

## Configuration

```python
Trackified(
    api_key="...",  # default: TRACKIFIED_API_KEY
    base_url="https://api.trackified.net",  # default: TRACKIFIED_BASE_URL or this; "/v1" ok
    timeout=30.0,  # seconds
    max_retries=2,
    on_request=None,  # callable(RequestInfo), once per attempt
    on_response=None,  # callable(ResponseInfo), once per attempt
)
```

### Hooks

```python
def log(info: trackified.ResponseInfo) -> None:
    print(
        info["method"],
        info["url"],
        info["attempt"],
        info["status"],
        info["request_id"],
        info["idempotent_replayed"],
        info["duration_ms"],
        info["error"],
    )


client = Trackified(on_request=lambda i: print("->", i["url"]), on_response=log)
```

`on_request` gets `{method, url, attempt, idempotency_key}`; `on_response` gets
`{method, url, attempt, status, request_id, idempotent_replayed, duration_ms, error}`, where
`error` is the typed error for status >= 400 or a connection failure (`status` is then `None`).
`attempt` starts at 1. Exceptions raised by a hook are caught and ignored.

Network errors, 408, 429 and 5xx responses are retried with exponential backoff and jitter
(429 waits for `Retry-After`). Other 4xx are never retried. Tracking creates send an
`Idempotency-Key` (a fresh UUID, or `idempotency_key=` if you pass one) that stays the same across
retries, so a retried create never makes a duplicate.

**After a timeout the outcome is unknown**: the server may already have done the work. Retry with
the same idempotency key; the client does this automatically for creates, and a replayed create
comes back with the `idempotent-replayed: true` header (`ResponseInfo["idempotent_replayed"]`).

## Errors

All errors subclass `trackified.TrackifiedError` and carry `status`, `code`, `message` and
`request_id`.

| Error | When |
| --- | --- |
| `AuthenticationError` | 401 |
| `PermissionError` | 403 |
| `NotFoundError` | 404 |
| `ValidationError` | 400, 422 |
| `QuotaExceededError` | 402 `quota_exceeded` |
| `ConflictError` | 409, e.g. `idempotency_in_progress` (not retried) |
| `RateLimitError` | 429 (`retry_after` in seconds) |
| `APIError` | 5xx |
| `ConnectionError` | no response; `code` is `"timeout"` or `"connection"` |
| `SignatureVerificationError` | bad webhook signature; `reason` says why |

```python
from trackified import NotFoundError

try:
    client.trackings.get("trk_missing")
except NotFoundError as e:
    print(e.code, e.request_id)
```

## License

MIT
