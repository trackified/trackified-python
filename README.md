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

# Get it again, with its events (newest first)
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

# Or verify and parse in one step (raises trackified.WebhookVerificationError):
event = trackified.construct_event(raw_body, request.headers["x-tracking-signature"], secret)
if event["type"] == "tracking.delivered":
    ...
```

The same functions are available as `client.webhooks.verify(...)` and
`client.webhooks.construct_event(...)`. Signatures older than 300 seconds are rejected; pass
`tolerance=` (seconds) to change that.

## Resources

| Resource | Methods |
| --- | --- |
| `client.trackings` | `create`, `list`, `list_auto_paging`, `create_bulk`, `get`, `update`, `delete`, `retrack` |
| `client.carriers` | `list`, `get`, `detect`, `catalog`, `validation_status` |
| `client.webhooks` | `create`, `list`, `delete`, `test`, `verify`, `construct_event` |
| `client.webhook_deliveries` | `list` |
| `client.api_keys` | `create`, `list`, `revoke` |
| `client.usage` | `get` |

Responses are plain dicts typed as `TypedDict`s (`Tracking`, `TrackingEvent`, `Carrier`, `Webhook`,
`WebhookDelivery`, `ApiKey`, `Usage`, ...). Enums are `Literal` types: `TrackingStatus`,
`EventStatus`, `WebhookEventType`.

## Configuration

```python
Trackified(
    api_key="...",  # default: TRACKIFIED_API_KEY
    base_url="https://api.trackified.net",  # default: TRACKIFIED_BASE_URL or this
    timeout=30.0,  # seconds
    max_retries=2,
)
```

Network errors, 408, 429 and 5xx responses are retried with exponential backoff and jitter
(429 waits for `Retry-After`). Other 4xx are never retried. Tracking creates send an
`Idempotency-Key` (a fresh UUID, or `idempotency_key=` if you pass one) that stays the same across
retries, so a retried create never makes a duplicate.

## Errors

All errors subclass `trackified.TrackifiedError` and carry `status`, `code`, `message` and
`request_id`.

| Error | When |
| --- | --- |
| `AuthenticationError` | 401 |
| `PermissionError` | 403 |
| `NotFoundError` | 404 |
| `ValidationError` | 400, 422 |
| `RateLimitError` | 429 (`retry_after` in seconds) |
| `APIError` | 5xx |
| `ConnectionError` | no response (DNS, refused, timeout) |
| `WebhookVerificationError` | bad webhook signature |

```python
from trackified import NotFoundError

try:
    client.trackings.get("trk_missing")
except NotFoundError as e:
    print(e.code, e.request_id)
```

## License

MIT
