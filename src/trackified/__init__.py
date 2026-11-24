"""Official Python client for the Trackified parcel-tracking API."""

from __future__ import annotations

from types import TracebackType
from typing import Optional, Type

import httpx

from ._client import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT,
    AsyncClient,
    OnRequest,
    OnResponse,
    RequestInfo,
    ResponseInfo,
    SyncClient,
)
from ._errors import (
    APIError,
    AuthenticationError,
    ConflictError,
    ConnectionError,
    NotFoundError,
    PermissionError,
    QuotaExceededError,
    RateLimitError,
    SignatureVerificationError,
    TrackifiedError,
    ValidationError,
    VerificationReason,
    WebhookVerificationError,
)
from ._resources import (
    ApiKeys,
    AsyncApiKeys,
    AsyncCarriers,
    AsyncTrackings,
    AsyncUsageResource,
    AsyncWebhookDeliveries,
    AsyncWebhooks,
    Carriers,
    Trackings,
    UsageResource,
    WebhookDeliveries,
    Webhooks,
)
from ._types import (
    ApiKey,
    ApiKeyMode,
    BulkResult,
    BulkRow,
    Carrier,
    CarrierCandidate,
    CarrierDetection,
    CarrierMatch,
    CarrierResolution,
    CarrierSupport,
    CatalogResult,
    EventStatus,
    Health,
    Pagination,
    RotatedWebhook,
    StatusChangedData,
    Tracking,
    TrackingCreatedEvent,
    TrackingDeliveredEvent,
    TrackingEvent,
    TrackingExceptionEvent,
    TrackingExpiredEvent,
    TrackingInput,
    TrackingReturnedEvent,
    TrackingStatus,
    TrackingStatusChangedEvent,
    TrackingUpdatedEvent,
    Usage,
    Webhook,
    WebhookDelivery,
    WebhookEvent,
    WebhookEventType,
)
from ._version import __version__
from ._webhooks import VerificationResult, construct_event, tracking_of, verify, verify_detailed


class Trackified:
    """Synchronous Trackified client.

    ``api_key`` falls back to ``TRACKIFIED_API_KEY``; ``base_url`` to ``TRACKIFIED_BASE_URL``
    (with or without a trailing ``/v1``). ``on_request`` / ``on_response`` are called once per
    attempt with a ``RequestInfo`` / ``ResponseInfo``; exceptions they raise are ignored.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        http_client: Optional[httpx.Client] = None,
        on_request: Optional[OnRequest] = None,
        on_response: Optional[OnResponse] = None,
    ) -> None:
        self._client = SyncClient(
            api_key, base_url, timeout, max_retries, http_client, on_request, on_response
        )
        self.trackings = Trackings(self._client)
        self.carriers = Carriers(self._client)
        self.webhooks = Webhooks(self._client)
        self.webhook_deliveries = WebhookDeliveries(self._client)
        self.api_keys = ApiKeys(self._client)
        self.usage = UsageResource(self._client)

    def health(self) -> Health:
        """``GET /v1/health``: ``{"status": "ok"}``. A degraded API (503) raises APIError."""
        result: Health = self._client.request("GET", "/v1/health")
        return result

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> Trackified:
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        self.close()


class AsyncTrackified:
    """Asynchronous Trackified client. Same resources as ``Trackified``, awaitable."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        http_client: Optional[httpx.AsyncClient] = None,
        on_request: Optional[OnRequest] = None,
        on_response: Optional[OnResponse] = None,
    ) -> None:
        self._client = AsyncClient(
            api_key, base_url, timeout, max_retries, http_client, on_request, on_response
        )
        self.trackings = AsyncTrackings(self._client)
        self.carriers = AsyncCarriers(self._client)
        self.webhooks = AsyncWebhooks(self._client)
        self.webhook_deliveries = AsyncWebhookDeliveries(self._client)
        self.api_keys = AsyncApiKeys(self._client)
        self.usage = AsyncUsageResource(self._client)

    async def health(self) -> Health:
        """``GET /v1/health``: ``{"status": "ok"}``. A degraded API (503) raises APIError."""
        result: Health = await self._client.request("GET", "/v1/health")
        return result

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> AsyncTrackified:
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        await self.close()


__all__ = [
    "APIError",
    "ApiKey",
    "ApiKeyMode",
    "AsyncTrackified",
    "AuthenticationError",
    "BulkResult",
    "BulkRow",
    "Carrier",
    "CarrierCandidate",
    "CarrierDetection",
    "CarrierMatch",
    "CarrierResolution",
    "CarrierSupport",
    "CatalogResult",
    "ConflictError",
    "ConnectionError",
    "EventStatus",
    "Health",
    "NotFoundError",
    "OnRequest",
    "OnResponse",
    "Pagination",
    "PermissionError",
    "QuotaExceededError",
    "RateLimitError",
    "RequestInfo",
    "ResponseInfo",
    "RotatedWebhook",
    "SignatureVerificationError",
    "StatusChangedData",
    "Trackified",
    "TrackifiedError",
    "Tracking",
    "TrackingCreatedEvent",
    "TrackingDeliveredEvent",
    "TrackingEvent",
    "TrackingExceptionEvent",
    "TrackingExpiredEvent",
    "TrackingInput",
    "TrackingReturnedEvent",
    "TrackingStatus",
    "TrackingStatusChangedEvent",
    "TrackingUpdatedEvent",
    "Usage",
    "ValidationError",
    "VerificationReason",
    "VerificationResult",
    "Webhook",
    "WebhookDelivery",
    "WebhookEvent",
    "WebhookEventType",
    "WebhookVerificationError",
    "__version__",
    "construct_event",
    "tracking_of",
    "verify",
    "verify_detailed",
]
