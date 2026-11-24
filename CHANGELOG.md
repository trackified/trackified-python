# Changelog

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
