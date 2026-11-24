"""Official Python client for the Trackified parcel-tracking API."""

from __future__ import annotations

from types import TracebackType
from typing import Optional, Type

import httpx

from ._client import DEFAULT_MAX_RETRIES, DEFAULT_TIMEOUT, AsyncClient, SyncClient
from ._errors import (
    APIError,
    AuthenticationError,
    ConnectionError,
    NotFoundError,
    PermissionError,
    RateLimitError,
    TrackifiedError,
    ValidationError,
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
    CarrierSupport,
    CatalogResult,
    EventStatus,
    Pagination,
    Tracking,
    TrackingEvent,
    TrackingInput,
    TrackingStatus,
    Usage,
    Webhook,
    WebhookDelivery,
    WebhookEvent,
    WebhookEventType,
)
from ._version import __version__
from ._webhooks import construct_event, verify


class Trackified:
    """Synchronous Trackified client.

    ``api_key`` falls back to ``TRACKIFIED_API_KEY``; ``base_url`` to ``TRACKIFIED_BASE_URL``.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        self._client = SyncClient(api_key, base_url, timeout, max_retries, http_client)
        self.trackings = Trackings(self._client)
        self.carriers = Carriers(self._client)
        self.webhooks = Webhooks(self._client)
        self.webhook_deliveries = WebhookDeliveries(self._client)
        self.api_keys = ApiKeys(self._client)
        self.usage = UsageResource(self._client)

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
    ) -> None:
        self._client = AsyncClient(api_key, base_url, timeout, max_retries, http_client)
        self.trackings = AsyncTrackings(self._client)
        self.carriers = AsyncCarriers(self._client)
        self.webhooks = AsyncWebhooks(self._client)
        self.webhook_deliveries = AsyncWebhookDeliveries(self._client)
        self.api_keys = AsyncApiKeys(self._client)
        self.usage = AsyncUsageResource(self._client)

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
    "CarrierSupport",
    "CatalogResult",
    "ConnectionError",
    "EventStatus",
    "NotFoundError",
    "Pagination",
    "PermissionError",
    "RateLimitError",
    "Tracking",
    "TrackingEvent",
    "TrackingInput",
    "TrackingStatus",
    "Trackified",
    "TrackifiedError",
    "Usage",
    "ValidationError",
    "Webhook",
    "WebhookDelivery",
    "WebhookEvent",
    "WebhookEventType",
    "WebhookVerificationError",
    "__version__",
    "construct_event",
    "verify",
]
