from __future__ import annotations

from typing import Any, Optional

import httpx


class TrackifiedError(Exception):
    """Base class for every error this library raises."""

    def __init__(
        self,
        message: str,
        *,
        status: Optional[int] = None,
        code: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status = status
        self.code = code
        self.request_id = request_id

    def __str__(self) -> str:
        parts = [self.message]
        if self.status is not None:
            parts.append(f"status={self.status}")
        if self.code:
            parts.append(f"code={self.code}")
        if self.request_id:
            parts.append(f"request_id={self.request_id}")
        return " ".join(parts)


class AuthenticationError(TrackifiedError):
    """401: missing or invalid API key."""


class PermissionError(TrackifiedError):  # noqa: A001
    """403: the key is not allowed to do this."""


class NotFoundError(TrackifiedError):
    """404."""


class ValidationError(TrackifiedError):
    """400 or 422: the request was rejected."""


class RateLimitError(TrackifiedError):
    """429. ``retry_after`` is the server's Retry-After in seconds, if sent."""

    def __init__(self, message: str, *, retry_after: Optional[float] = None, **kwargs: Any) -> None:
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class APIError(TrackifiedError):
    """5xx: the server failed."""


class ConnectionError(TrackifiedError):  # noqa: A001
    """The request never got a response (DNS, refused, timeout, ...)."""


class WebhookVerificationError(TrackifiedError):
    """A webhook signature header was missing, malformed, stale or wrong."""


def parse_retry_after(response: httpx.Response) -> Optional[float]:
    value = response.headers.get("retry-after")
    if value is None:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        return None


def error_from_response(response: httpx.Response) -> TrackifiedError:
    status = response.status_code
    code: Optional[str] = None
    message = response.reason_phrase or f"HTTP {status}"
    request_id: Optional[str] = response.headers.get("x-request-id")
    try:
        body = response.json()
        err = body.get("error") if isinstance(body, dict) else None
        if isinstance(err, dict):
            code = err.get("code") or None
            message = err.get("message") or message
            request_id = err.get("request_id") or request_id
    except ValueError:
        pass
    kwargs: Any = {"status": status, "code": code, "request_id": request_id}
    if status == 401:
        return AuthenticationError(message, **kwargs)
    if status == 403:
        return PermissionError(message, **kwargs)
    if status == 404:
        return NotFoundError(message, **kwargs)
    if status in (400, 422):
        return ValidationError(message, **kwargs)
    if status == 429:
        return RateLimitError(message, retry_after=parse_retry_after(response), **kwargs)
    if status >= 500:
        return APIError(message, **kwargs)
    return TrackifiedError(message, **kwargs)
