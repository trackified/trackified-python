# Changelog

## 0.2.0 (2026-11-24)

All additive; 0.1 code keeps working.

- T-1/T-3: `base_url` may be given with or without a trailing `/v1` (and trailing slash); never produces `/v1/v1`.
- T-2: `usage.get()` calls the canonical `/v1/account/usage` (unchanged; the API also answers `/v1/usage`).
- T-4: `client.health()` → `{"status": "ok"}`.
- T-5: `carriers.resolve(name)` → `{carrier, name, confidence, matched}` or `None`. `Carrier` gains `aliases` and documents both `display_name` and the deprecated `displayName`.
- T-6: webhook events are typed per `type` (`TrackingStatusChangedEvent`, `TrackingDeliveredEvent`, ...); `WebhookEvent` is their union and narrows on `event["type"]`. New `tracking_of(event)` / `webhooks.tracking_of(event)`.
- T-7: `TrackingEvent.date` is deprecated, removed after 2027-06-01; zoneless `occurred_at` is documented as scan-local time.
- T-8: `Tracking.events` documented as newest first (guaranteed by the API).
- T-9: `SignatureVerificationError` (0.1's `WebhookVerificationError` is now an alias) carries `reason`: `missing`, `malformed`, `timestamp` or `mismatch`. New `verify_detailed()` → `VerificationResult(valid, reason)`.
- T-10: a signature header with several `v1=` values verifies if any matches; `secret` may be a list of secrets. New `webhooks.rotate_secret(id, expires_in_hours=)`.
- T-11: `webhooks.update(id, url=, event_types=, enabled=)`.
- T-12: `QuotaExceededError` (402) and `ConflictError` (409, not retried). `ConnectionError.code` is `"timeout"` or `"connection"`.
- Bulk create sends one auto-generated `Idempotency-Key` per call, reused across retries (as single create; now documented and tested).
- `webhooks.test` docstring: it signs and returns a sample, it does not deliver.
- T-13: `on_request` / `on_response` hooks, called once per attempt with `RequestInfo` / `ResponseInfo`; exceptions they raise are ignored.

## 0.1.0 (2026-11-24)

First release.

- `Trackified` (sync) and `AsyncTrackified` (async) clients covering all 21 API operations:
  trackings, carriers, webhooks, webhook deliveries, API keys and usage.
- Typed response models (`TypedDict`) and `Literal` enums for tracking status, event status and webhook event types.
- Auto-pagination with `trackings.list_auto_paging()`.
- Automatic retries with exponential backoff and jitter for network errors, 408, 429 (honours `Retry-After`) and 5xx.
- Automatic `Idempotency-Key` on tracking creates, reused across retries.
- Typed errors: `AuthenticationError`, `PermissionError`, `NotFoundError`, `ValidationError`, `RateLimitError`, `APIError`, `ConnectionError`.
- Webhook signature verification: `webhooks.verify()` and `webhooks.construct_event()`.
