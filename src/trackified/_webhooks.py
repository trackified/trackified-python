from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from string import hexdigits
from typing import Optional, Sequence, Tuple, Union, cast

from ._errors import SignatureVerificationError, VerificationReason
from ._types import Tracking, WebhookEvent

DEFAULT_TOLERANCE = 300

Secrets = Union[str, Sequence[str]]


@dataclass(frozen=True)
class VerificationResult:
    """Result of ``verify_detailed``. ``reason`` is set only when ``valid`` is False."""

    valid: bool
    reason: Optional[VerificationReason] = None


def _check(
    payload: Union[str, bytes], header: str, secret: Secrets, tolerance: float
) -> Optional[Tuple[VerificationReason, str]]:
    """None when valid, else (reason, message)."""
    secrets = [secret] if isinstance(secret, str) else list(secret)
    secrets = [s for s in secrets if s]
    if not header or not secrets:
        return "missing", "missing signature header or secret"
    body = payload.encode() if isinstance(payload, str) else payload
    timestamp = None
    signatures = []
    for part in header.split(","):
        key, sep, value = part.strip().partition("=")
        if not sep:
            continue
        if key == "t":
            timestamp = value
        elif key == "v1":
            signatures.append(value)
    if timestamp is None or not timestamp.isdigit() or not signatures:
        return "malformed", "malformed signature header"
    if not all(s and len(s) % 2 == 0 and all(c in hexdigits for c in s) for s in signatures):
        return "malformed", "malformed signature header"
    if abs(time.time() - int(timestamp)) > tolerance:
        return "timestamp", "signature timestamp outside tolerance"
    signed = timestamp.encode() + b"." + body
    # Header may carry several v1= values during secret rotation; any match is valid.
    for key in secrets:
        expected = hmac.new(key.encode(), signed, hashlib.sha256).hexdigest().encode()
        if any(hmac.compare_digest(expected, s.encode()) for s in signatures):
            return None
    return "mismatch", "signature mismatch"


def verify_detailed(
    payload: Union[str, bytes], header: str, secret: Secrets, tolerance: float = DEFAULT_TOLERANCE
) -> VerificationResult:
    """Like ``verify`` but says why it failed. ``secret`` may be a list of secrets."""
    failure = _check(payload, header, secret, tolerance)
    return VerificationResult(True) if failure is None else VerificationResult(False, failure[0])


def verify(
    payload: Union[str, bytes], header: str, secret: Secrets, tolerance: float = DEFAULT_TOLERANCE
) -> bool:
    """True when ``header`` (x-tracking-signature) is a valid signature of the raw ``payload``."""
    return _check(payload, header, secret, tolerance) is None


def construct_event(
    payload: Union[str, bytes], header: str, secret: Secrets, tolerance: float = DEFAULT_TOLERANCE
) -> WebhookEvent:
    """Verify the signature and return the parsed event. Raises SignatureVerificationError."""
    failure = _check(payload, header, secret, tolerance)
    if failure is not None:
        raise SignatureVerificationError(failure[1], reason=failure[0])
    try:
        return cast(WebhookEvent, json.loads(payload))
    except ValueError as e:
        raise SignatureVerificationError("payload is not valid JSON", reason="malformed") from e


def tracking_of(event: WebhookEvent) -> Tracking:
    """The Tracking an event is about, whatever its type."""
    if event["type"] == "tracking.status_changed":
        return event["data"]["tracking"]
    return event["data"]
