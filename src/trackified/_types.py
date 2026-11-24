"""Typed models for Trackified API responses, written from https://api.trackified.net/openapi.json."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, TypedDict, Union

TrackingStatus = Literal[
    "not_yet_scanned",
    "in_transit",
    "out_for_delivery",
    "available_for_pickup",
    "delivered",
    "exception",
    "returned",
    "unknown",
]

EventStatus = Literal[
    "info_received",
    "in_transit",
    "out_for_delivery",
    "available_for_pickup",
    "delivered",
    "exception",
    "returned",
    "unknown",
]

WebhookEventType = Literal[
    "tracking.created",
    "tracking.updated",
    "tracking.status_changed",
    "tracking.delivered",
    "tracking.exception",
    "tracking.returned",
    "tracking.expired",
]

ApiKeyMode = Literal["test", "live"]
CarrierSupport = Literal["scraper", "api", "unsupported"]


class TrackingInput(TypedDict, total=False):
    tracking_number: str
    carrier: str
    custom_id: str
    customer_email: str


class TrackingEvent(TypedDict):
    occurred_at: Optional[str]
    """When the scan happened. Without an offset it is the local time where the scan happened;
    when the carrier gives an offset it is included and ``time_zone_known`` is True."""
    time_zone_known: bool
    status: EventStatus
    description: str
    location: str
    date: Optional[str]
    """Deprecated: use ``occurred_at``. Sent until 2027-06-01, removed after."""


class Tracking(TypedDict, total=False):
    id: str
    tracking_number: str
    carrier: Optional[str]
    carrier_detected: bool
    status: TrackingStatus
    events: List[TrackingEvent]
    """Newest first (sorted by ``occurred_at`` desc; guaranteed by the API)."""
    estimated_delivery: Optional[str]
    delivered_at: Optional[str]
    delivered_at_time_zone_known: bool
    delivery_detected_at: Optional[str]
    exception: Optional[str]
    service_level: Optional[str]
    custom_id: Optional[str]
    customer_email: Optional[str]
    last_scraped_at: Optional[str]
    next_scrape_at: Optional[str]
    created_at: str
    updated_at: str


class Pagination(TypedDict, total=False):
    limit: int
    offset: int
    total: int


class TrackingList(TypedDict):
    data: List[Tracking]
    pagination: Pagination


class BulkRow(TypedDict, total=False):
    ok: bool
    tracking: Tracking
    error: str


class BulkResult(TypedDict, total=False):
    data: List[BulkRow]


class DeletedTracking(TypedDict, total=False):
    deleted: bool
    id: str


class RetrackResult(TypedDict, total=False):
    queued: bool
    tracking: Tracking


class Carrier(TypedDict, total=False):
    id: str
    display_name: str
    displayName: str  # deprecated spelling; the API sends both
    aliases: List[str]


CarrierMatch = Literal["id", "alias", "name", "provider_slug", "prefix"]


class CarrierResolution(TypedDict):
    carrier: str
    name: str
    confidence: float
    matched: CarrierMatch


class Health(TypedDict, total=False):
    status: str
    checks: Dict[str, Any]


class CarrierList(TypedDict):
    data: List[Carrier]
    pagination: Pagination


class CarrierCandidate(TypedDict, total=False):
    carrier: str
    confidence: float
    reason: str


class CarrierDetection(TypedDict, total=False):
    tracking_number: str
    candidates: List[CarrierCandidate]


class CatalogResult(TypedDict, total=False):
    total: int
    data: List[Dict[str, Any]]


class Webhook(TypedDict, total=False):
    id: str
    url: str
    event_types: List[WebhookEventType]
    enabled: bool
    secret_preview: str
    secret: str  # only in the create response
    created_at: str


class RotatedWebhook(Webhook, total=False):
    previous_secret_expires_at: Optional[str]


class WebhookList(TypedDict):
    data: List[Webhook]
    pagination: Pagination


class WebhookTestResult(TypedDict, total=False):
    signature: str
    body: Dict[str, Any]


class WebhookDelivery(TypedDict, total=False):
    id: str
    webhook_id: str
    url: str
    event_type: WebhookEventType
    status: Optional[int]
    attempts: int
    error: Optional[str]
    delivered_at: Optional[str]
    created_at: str


class WebhookDeliveryList(TypedDict):
    data: List[WebhookDelivery]
    pagination: Pagination


class ApiKey(TypedDict, total=False):
    id: str
    name: str
    prefix: str
    mode: ApiKeyMode
    scopes: List[str]
    token: str  # only in the create response
    created_at: str
    last_used_at: Optional[str]
    revoked_at: Optional[str]


class ApiKeyList(TypedDict):
    data: List[ApiKey]
    pagination: Pagination


class CarrierVolume(TypedDict):
    carrier: str
    count: int


class Usage(TypedDict):
    period_start: str
    period_end: str
    plan: str
    trackings_used: int
    trackings_limit: int
    trackings_remaining: int
    rate_limit_per_minute: int
    webhook_deliveries: int
    carrier_volume: List[CarrierVolume]


class StatusChangedData(TypedDict):
    tracking: Tracking
    previous_status: TrackingStatus
    current_status: TrackingStatus


class _EventBase(TypedDict):
    id: str
    created_at: str


class TrackingCreatedEvent(_EventBase):
    type: Literal["tracking.created"]
    data: Tracking


class TrackingUpdatedEvent(_EventBase):
    type: Literal["tracking.updated"]
    data: Tracking


class TrackingStatusChangedEvent(_EventBase):
    type: Literal["tracking.status_changed"]
    data: StatusChangedData


class TrackingDeliveredEvent(_EventBase):
    type: Literal["tracking.delivered"]
    data: Tracking


class TrackingExceptionEvent(_EventBase):
    type: Literal["tracking.exception"]
    data: Tracking


class TrackingReturnedEvent(_EventBase):
    type: Literal["tracking.returned"]
    data: Tracking


class TrackingExpiredEvent(_EventBase):
    type: Literal["tracking.expired"]
    data: Tracking


# Narrow on event["type"]; use tracking_of(event) to get the Tracking from any of them.
WebhookEvent = Union[
    TrackingCreatedEvent,
    TrackingUpdatedEvent,
    TrackingStatusChangedEvent,
    TrackingDeliveredEvent,
    TrackingExceptionEvent,
    TrackingReturnedEvent,
    TrackingExpiredEvent,
]
