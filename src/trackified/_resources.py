"""Sync and async resources. The two halves mirror each other; change both together."""

from __future__ import annotations

import uuid
from typing import Any, AsyncIterator, Dict, Iterator, List, Optional, Sequence, Union
from urllib.parse import quote

from . import _webhooks
from ._client import AsyncClient, SyncClient
from ._types import (
    ApiKey,
    ApiKeyList,
    ApiKeyMode,
    BulkResult,
    Carrier,
    CarrierDetection,
    CarrierList,
    CarrierSupport,
    CatalogResult,
    DeletedTracking,
    RetrackResult,
    Tracking,
    TrackingInput,
    TrackingList,
    TrackingStatus,
    Usage,
    Webhook,
    WebhookDeliveryList,
    WebhookEvent,
    WebhookEventType,
    WebhookList,
    WebhookTestResult,
)

Payload = Union[str, bytes]


def _id(value: str) -> str:
    return quote(value, safe="")


def _tracking_body(
    tracking_number: str,
    carrier: Optional[str],
    custom_id: Optional[str],
    customer_email: Optional[str],
) -> Dict[str, Any]:
    body = {
        "tracking_number": tracking_number,
        "carrier": carrier,
        "custom_id": custom_id,
        "customer_email": customer_email,
    }
    return {k: v for k, v in body.items() if v is not None}


def _drop_none(**kwargs: Any) -> Dict[str, Any]:
    return {k: v for k, v in kwargs.items() if v is not None}


class _WebhookVerifier:
    @staticmethod
    def verify(
        payload: Payload,
        header: str,
        secret: str,
        tolerance: float = _webhooks.DEFAULT_TOLERANCE,
    ) -> bool:
        """True when the x-tracking-signature ``header`` signs the raw ``payload``."""
        return _webhooks.verify(payload, header, secret, tolerance)

    @staticmethod
    def construct_event(
        payload: Payload,
        header: str,
        secret: str,
        tolerance: float = _webhooks.DEFAULT_TOLERANCE,
    ) -> WebhookEvent:
        """Verify and parse a webhook event; raises WebhookVerificationError."""
        return _webhooks.construct_event(payload, header, secret, tolerance)


# --------------------------------------------------------------------------- sync


class Trackings:
    def __init__(self, client: SyncClient) -> None:
        self._c = client

    def create(
        self,
        tracking_number: str,
        *,
        carrier: Optional[str] = None,
        custom_id: Optional[str] = None,
        customer_email: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> Tracking:
        result: Tracking = self._c.request(
            "POST",
            "/v1/trackings",
            json=_tracking_body(tracking_number, carrier, custom_id, customer_email),
            idempotency_key=idempotency_key or str(uuid.uuid4()),
        )
        return result

    def list(
        self,
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        status: Optional[TrackingStatus] = None,
        carrier: Optional[str] = None,
        custom_id: Optional[str] = None,
        tracking_number: Optional[str] = None,
    ) -> TrackingList:
        result: TrackingList = self._c.request(
            "GET",
            "/v1/trackings",
            params=_drop_none(
                limit=limit,
                offset=offset,
                status=status,
                carrier=carrier,
                custom_id=custom_id,
                tracking_number=tracking_number,
            ),
        )
        return result

    def list_auto_paging(
        self,
        *,
        limit: int = 100,
        status: Optional[TrackingStatus] = None,
        carrier: Optional[str] = None,
        custom_id: Optional[str] = None,
        tracking_number: Optional[str] = None,
    ) -> Iterator[Tracking]:
        """Yield every matching tracking, fetching pages of ``limit`` as needed."""
        offset = 0
        while True:
            page = self.list(
                limit=limit,
                offset=offset,
                status=status,
                carrier=carrier,
                custom_id=custom_id,
                tracking_number=tracking_number,
            )
            yield from page["data"]
            offset += len(page["data"])
            if not page["data"] or offset >= page["pagination"].get("total", offset):
                return

    def create_bulk(
        self, trackings: Sequence[TrackingInput], *, idempotency_key: Optional[str] = None
    ) -> BulkResult:
        result: BulkResult = self._c.request(
            "POST",
            "/v1/trackings/bulk",
            json={"trackings": list(trackings)},
            idempotency_key=idempotency_key or str(uuid.uuid4()),
        )
        return result

    def get(self, id: str) -> Tracking:
        result: Tracking = self._c.request("GET", f"/v1/trackings/{_id(id)}")
        return result

    def update(
        self,
        id: str,
        *,
        carrier: Optional[str] = None,
        custom_id: Optional[str] = None,
        customer_email: Optional[str] = None,
    ) -> Tracking:
        result: Tracking = self._c.request(
            "PUT",
            f"/v1/trackings/{_id(id)}",
            json=_drop_none(carrier=carrier, custom_id=custom_id, customer_email=customer_email),
        )
        return result

    def delete(self, id: str) -> DeletedTracking:
        """Stop tracking a parcel."""
        result: DeletedTracking = self._c.request("DELETE", f"/v1/trackings/{_id(id)}")
        return result

    def retrack(self, id: str) -> RetrackResult:
        result: RetrackResult = self._c.request("POST", f"/v1/trackings/{_id(id)}/retrack")
        return result


class Carriers:
    def __init__(self, client: SyncClient) -> None:
        self._c = client

    def list(self, *, limit: Optional[int] = None, offset: Optional[int] = None) -> CarrierList:
        result: CarrierList = self._c.request(
            "GET", "/v1/carriers", params=_drop_none(limit=limit, offset=offset)
        )
        return result

    def get(self, id: str) -> Carrier:
        result: Carrier = self._c.request("GET", f"/v1/carriers/{_id(id)}")
        return result

    def detect(self, tracking_number: str) -> CarrierDetection:
        result: CarrierDetection = self._c.request(
            "GET", "/v1/carriers/detect", params={"number": tracking_number}
        )
        return result

    def catalog(
        self,
        *,
        q: Optional[str] = None,
        support: Optional[CarrierSupport] = None,
        limit: Optional[int] = None,
    ) -> CatalogResult:
        result: CatalogResult = self._c.request(
            "GET", "/v1/carriers/catalog", params=_drop_none(q=q, support=support, limit=limit)
        )
        return result

    def validation_status(self) -> Dict[str, Any]:
        result: Dict[str, Any] = self._c.request("GET", "/v1/carriers/status")
        return result


class Webhooks(_WebhookVerifier):
    def __init__(self, client: SyncClient) -> None:
        self._c = client

    def create(self, url: str, *, event_types: Optional[List[WebhookEventType]] = None) -> Webhook:
        result: Webhook = self._c.request(
            "POST", "/v1/webhooks", json=_drop_none(url=url, event_types=event_types)
        )
        return result

    def list(self, *, limit: Optional[int] = None, offset: Optional[int] = None) -> WebhookList:
        result: WebhookList = self._c.request(
            "GET", "/v1/webhooks", params=_drop_none(limit=limit, offset=offset)
        )
        return result

    def delete(self, id: str) -> Dict[str, Any]:
        result: Dict[str, Any] = self._c.request("DELETE", f"/v1/webhooks/{_id(id)}")
        return result

    def test(self, id: str) -> WebhookTestResult:
        result: WebhookTestResult = self._c.request("POST", f"/v1/webhooks/{_id(id)}/test")
        return result


class WebhookDeliveries:
    def __init__(self, client: SyncClient) -> None:
        self._c = client

    def list(
        self, *, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> WebhookDeliveryList:
        result: WebhookDeliveryList = self._c.request(
            "GET", "/v1/webhook-deliveries", params=_drop_none(limit=limit, offset=offset)
        )
        return result


class ApiKeys:
    def __init__(self, client: SyncClient) -> None:
        self._c = client

    def create(
        self,
        *,
        name: Optional[str] = None,
        mode: Optional[ApiKeyMode] = None,
        scopes: Optional[List[str]] = None,
    ) -> ApiKey:
        result: ApiKey = self._c.request(
            "POST", "/v1/account/api-keys", json=_drop_none(name=name, mode=mode, scopes=scopes)
        )
        return result

    def list(self, *, limit: Optional[int] = None, offset: Optional[int] = None) -> ApiKeyList:
        result: ApiKeyList = self._c.request(
            "GET", "/v1/account/api-keys", params=_drop_none(limit=limit, offset=offset)
        )
        return result

    def revoke(self, id: str) -> Dict[str, Any]:
        result: Dict[str, Any] = self._c.request("DELETE", f"/v1/account/api-keys/{_id(id)}")
        return result


class UsageResource:
    def __init__(self, client: SyncClient) -> None:
        self._c = client

    def get(self) -> Usage:
        result: Usage = self._c.request("GET", "/v1/account/usage")
        return result


# -------------------------------------------------------------------------- async


class AsyncTrackings:
    def __init__(self, client: AsyncClient) -> None:
        self._c = client

    async def create(
        self,
        tracking_number: str,
        *,
        carrier: Optional[str] = None,
        custom_id: Optional[str] = None,
        customer_email: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> Tracking:
        result: Tracking = await self._c.request(
            "POST",
            "/v1/trackings",
            json=_tracking_body(tracking_number, carrier, custom_id, customer_email),
            idempotency_key=idempotency_key or str(uuid.uuid4()),
        )
        return result

    async def list(
        self,
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        status: Optional[TrackingStatus] = None,
        carrier: Optional[str] = None,
        custom_id: Optional[str] = None,
        tracking_number: Optional[str] = None,
    ) -> TrackingList:
        result: TrackingList = await self._c.request(
            "GET",
            "/v1/trackings",
            params=_drop_none(
                limit=limit,
                offset=offset,
                status=status,
                carrier=carrier,
                custom_id=custom_id,
                tracking_number=tracking_number,
            ),
        )
        return result

    async def list_auto_paging(
        self,
        *,
        limit: int = 100,
        status: Optional[TrackingStatus] = None,
        carrier: Optional[str] = None,
        custom_id: Optional[str] = None,
        tracking_number: Optional[str] = None,
    ) -> AsyncIterator[Tracking]:
        """Yield every matching tracking, fetching pages of ``limit`` as needed."""
        offset = 0
        while True:
            page = await self.list(
                limit=limit,
                offset=offset,
                status=status,
                carrier=carrier,
                custom_id=custom_id,
                tracking_number=tracking_number,
            )
            for item in page["data"]:
                yield item
            offset += len(page["data"])
            if not page["data"] or offset >= page["pagination"].get("total", offset):
                return

    async def create_bulk(
        self, trackings: Sequence[TrackingInput], *, idempotency_key: Optional[str] = None
    ) -> BulkResult:
        result: BulkResult = await self._c.request(
            "POST",
            "/v1/trackings/bulk",
            json={"trackings": list(trackings)},
            idempotency_key=idempotency_key or str(uuid.uuid4()),
        )
        return result

    async def get(self, id: str) -> Tracking:
        result: Tracking = await self._c.request("GET", f"/v1/trackings/{_id(id)}")
        return result

    async def update(
        self,
        id: str,
        *,
        carrier: Optional[str] = None,
        custom_id: Optional[str] = None,
        customer_email: Optional[str] = None,
    ) -> Tracking:
        result: Tracking = await self._c.request(
            "PUT",
            f"/v1/trackings/{_id(id)}",
            json=_drop_none(carrier=carrier, custom_id=custom_id, customer_email=customer_email),
        )
        return result

    async def delete(self, id: str) -> DeletedTracking:
        """Stop tracking a parcel."""
        result: DeletedTracking = await self._c.request("DELETE", f"/v1/trackings/{_id(id)}")
        return result

    async def retrack(self, id: str) -> RetrackResult:
        result: RetrackResult = await self._c.request("POST", f"/v1/trackings/{_id(id)}/retrack")
        return result


class AsyncCarriers:
    def __init__(self, client: AsyncClient) -> None:
        self._c = client

    async def list(
        self, *, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> CarrierList:
        result: CarrierList = await self._c.request(
            "GET", "/v1/carriers", params=_drop_none(limit=limit, offset=offset)
        )
        return result

    async def get(self, id: str) -> Carrier:
        result: Carrier = await self._c.request("GET", f"/v1/carriers/{_id(id)}")
        return result

    async def detect(self, tracking_number: str) -> CarrierDetection:
        result: CarrierDetection = await self._c.request(
            "GET", "/v1/carriers/detect", params={"number": tracking_number}
        )
        return result

    async def catalog(
        self,
        *,
        q: Optional[str] = None,
        support: Optional[CarrierSupport] = None,
        limit: Optional[int] = None,
    ) -> CatalogResult:
        result: CatalogResult = await self._c.request(
            "GET", "/v1/carriers/catalog", params=_drop_none(q=q, support=support, limit=limit)
        )
        return result

    async def validation_status(self) -> Dict[str, Any]:
        result: Dict[str, Any] = await self._c.request("GET", "/v1/carriers/status")
        return result


class AsyncWebhooks(_WebhookVerifier):
    def __init__(self, client: AsyncClient) -> None:
        self._c = client

    async def create(
        self, url: str, *, event_types: Optional[List[WebhookEventType]] = None
    ) -> Webhook:
        result: Webhook = await self._c.request(
            "POST", "/v1/webhooks", json=_drop_none(url=url, event_types=event_types)
        )
        return result

    async def list(
        self, *, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> WebhookList:
        result: WebhookList = await self._c.request(
            "GET", "/v1/webhooks", params=_drop_none(limit=limit, offset=offset)
        )
        return result

    async def delete(self, id: str) -> Dict[str, Any]:
        result: Dict[str, Any] = await self._c.request("DELETE", f"/v1/webhooks/{_id(id)}")
        return result

    async def test(self, id: str) -> WebhookTestResult:
        result: WebhookTestResult = await self._c.request("POST", f"/v1/webhooks/{_id(id)}/test")
        return result


class AsyncWebhookDeliveries:
    def __init__(self, client: AsyncClient) -> None:
        self._c = client

    async def list(
        self, *, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> WebhookDeliveryList:
        result: WebhookDeliveryList = await self._c.request(
            "GET", "/v1/webhook-deliveries", params=_drop_none(limit=limit, offset=offset)
        )
        return result


class AsyncApiKeys:
    def __init__(self, client: AsyncClient) -> None:
        self._c = client

    async def create(
        self,
        *,
        name: Optional[str] = None,
        mode: Optional[ApiKeyMode] = None,
        scopes: Optional[List[str]] = None,
    ) -> ApiKey:
        result: ApiKey = await self._c.request(
            "POST", "/v1/account/api-keys", json=_drop_none(name=name, mode=mode, scopes=scopes)
        )
        return result

    async def list(
        self, *, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> ApiKeyList:
        result: ApiKeyList = await self._c.request(
            "GET", "/v1/account/api-keys", params=_drop_none(limit=limit, offset=offset)
        )
        return result

    async def revoke(self, id: str) -> Dict[str, Any]:
        result: Dict[str, Any] = await self._c.request("DELETE", f"/v1/account/api-keys/{_id(id)}")
        return result


class AsyncUsageResource:
    def __init__(self, client: AsyncClient) -> None:
        self._c = client

    async def get(self) -> Usage:
        result: Usage = await self._c.request("GET", "/v1/account/usage")
        return result
