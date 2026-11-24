"""Typed models for Trackified API responses, written from https://api.trackified.net/openapi.json."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, TypedDict

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
    time_zone_known: bool
    status: EventStatus
    description: str
    location: str
    date: Optional[str]  # deprecated: use occurred_at


class Tracking(TypedDict, total=False):
    id: str
    tracking_number: str
    carrier: Optional[str]
    carrier_detected: bool
    status: TrackingStatus
    events: List[TrackingEvent]
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


class WebhookEvent(TypedDict, total=False):
    id: str
    type: WebhookEventType
    data: Dict[str, Any]
    created_at: str
