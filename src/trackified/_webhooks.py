from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Union, cast

from ._errors import WebhookVerificationError
from ._types import WebhookEvent

DEFAULT_TOLERANCE = 300


def _check(payload: Union[str, bytes], header: str, secret: str, tolerance: float) -> None:
    body = payload.encode() if isinstance(payload, str) else payload
    timestamp = None
    signatures = []
    for part in (header or "").split(","):
        key, sep, value = part.strip().partition("=")
        if not sep:
            continue
        if key == "t":
            timestamp = value
        elif key == "v1":
            signatures.append(value)
    if timestamp is None or not timestamp.isdigit() or not signatures:
        raise WebhookVerificationError("malformed signature header")
    if abs(time.time() - int(timestamp)) > tolerance:
        raise WebhookVerificationError("signature timestamp outside tolerance")
    expected = hmac.new(
        secret.encode(), timestamp.encode() + b"." + body, hashlib.sha256
    ).hexdigest()
    if not any(hmac.compare_digest(expected.encode(), s.encode()) for s in signatures):
        raise WebhookVerificationError("signature mismatch")


def verify(
    payload: Union[str, bytes], header: str, secret: str, tolerance: float = DEFAULT_TOLERANCE
) -> bool:
    """True when ``header`` (x-tracking-signature) is a valid signature of the raw ``payload``."""
    try:
        _check(payload, header, secret, tolerance)
    except WebhookVerificationError:
        return False
    return True


def construct_event(
    payload: Union[str, bytes], header: str, secret: str, tolerance: float = DEFAULT_TOLERANCE
) -> WebhookEvent:
    """Verify the signature and return the parsed event. Raises WebhookVerificationError."""
    _check(payload, header, secret, tolerance)
    try:
        return cast(WebhookEvent, json.loads(payload))
    except ValueError as e:
        raise WebhookVerificationError("payload is not valid JSON") from e
