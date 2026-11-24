from __future__ import annotations

from typing import Any

import pytest

import trackified
from trackified import Trackified, WebhookVerificationError

SECRET = "whsec_trackified_test_vector"
BODY = '{"id":"evt_test","type":"tracking.updated","data":{"id":"trk_123"}}'
T = 1792560000
SIG = "19752dd2fca1872cc8aa6cc36c412fce3bbfa120480580bdb1ad9d7957dfc9f4"
HEADER = f"t={T},v1={SIG}"


@pytest.fixture(autouse=True)
def pin_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("trackified._webhooks.time.time", lambda: float(T))


def test_vector_verifies() -> None:
    assert trackified.verify(BODY, HEADER, SECRET)
    assert trackified.verify(BODY.encode(), HEADER, SECRET)
    assert Trackified(api_key="k").webhooks.verify(BODY, HEADER, SECRET)


def test_construct_event() -> None:
    event = trackified.construct_event(BODY, HEADER, SECRET)
    assert event["type"] == "tracking.updated"
    assert event["data"]["id"] == "trk_123"


def test_flipped_hex_digit() -> None:
    flipped = SIG[:-1] + ("5" if SIG[-1] != "5" else "6")
    assert not trackified.verify(BODY, f"t={T},v1={flipped}", SECRET)


def test_different_body() -> None:
    assert not trackified.verify(BODY.replace("trk_123", "trk_124"), HEADER, SECRET)


def test_wrong_secret() -> None:
    assert not trackified.verify(BODY, HEADER, "whsec_other")


def test_outside_tolerance(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("trackified._webhooks.time.time", lambda: float(T + 301))
    assert not trackified.verify(BODY, HEADER, SECRET)
    assert trackified.verify(BODY, HEADER, SECRET, tolerance=400)
    monkeypatch.setattr("trackified._webhooks.time.time", lambda: float(T - 301))
    assert not trackified.verify(BODY, HEADER, SECRET)


@pytest.mark.parametrize(
    "header",
    [
        "",
        "garbage",
        f"t={T}",
        f"v1={SIG}",
        f"t=abc,v1={SIG}",
        f"t={T};v1={SIG}",
        f"t={T},v1=\u00e9",
    ],
)
def test_malformed_header(header: str) -> None:
    assert not trackified.verify(BODY, header, SECRET)
    with pytest.raises(WebhookVerificationError):
        trackified.construct_event(BODY, header, SECRET)


SECRET_B = "whsec_trackified_test_vector_b"
SIG_B = "aaa4b846892609125e20b07a531d46e9e4614d8eec8d6dd3ecccae877b58111f"
DUAL_HEADER = f"t={T},v1={SIG_B},v1={SIG}"


def test_dual_signature_vector() -> None:
    # Only the second v1 matches secret A; only the first matches B.
    assert trackified.verify(BODY, DUAL_HEADER, SECRET)
    assert trackified.verify(BODY, DUAL_HEADER, SECRET_B)
    assert trackified.verify(BODY, DUAL_HEADER, [SECRET, SECRET_B])
    assert trackified.verify(BODY, HEADER, [SECRET_B, SECRET])
    assert not trackified.verify(BODY, f"t={T},v1={SIG_B}", SECRET)
    assert trackified.construct_event(BODY, DUAL_HEADER, [SECRET_B])["id"] == "evt_test"


@pytest.mark.parametrize(
    "header,secret,reason",
    [
        ("", SECRET, "missing"),
        (HEADER, "", "missing"),
        (HEADER, [], "missing"),
        ("garbage", SECRET, "malformed"),
        (f"v1={SIG}", SECRET, "malformed"),
        (f"t={T}", SECRET, "malformed"),
        (f"t=abc,v1={SIG}", SECRET, "malformed"),
        (f"t={T},v1=zz", SECRET, "malformed"),
        (f"t={T},v1=abc", SECRET, "malformed"),
        (f"t={T - 301},v1={SIG}", SECRET, "timestamp"),
        (HEADER, "whsec_other", "mismatch"),
    ],
)
def test_reasons(header: str, secret: Any, reason: str) -> None:
    result = trackified.verify_detailed(BODY, header, secret)
    assert result == trackified.VerificationResult(False, reason)  # type: ignore[arg-type]
    assert not trackified.verify(BODY, header, secret)
    with pytest.raises(trackified.SignatureVerificationError) as e:
        trackified.construct_event(BODY, header, secret)
    assert e.value.reason == reason
    assert isinstance(e.value, WebhookVerificationError)


def test_verify_detailed_valid() -> None:
    assert Trackified(api_key="k").webhooks.verify_detailed(BODY, HEADER, SECRET) == (
        trackified.VerificationResult(True, None)
    )


def test_tracking_of() -> None:
    tracking: trackified.Tracking = {"id": "trk_1"}
    changed: trackified.TrackingStatusChangedEvent = {
        "id": "evt_1",
        "type": "tracking.status_changed",
        "created_at": "2026-01-01T00:00:00Z",
        "data": {
            "tracking": tracking,
            "previous_status": "in_transit",
            "current_status": "delivered",
        },
    }
    delivered: trackified.TrackingDeliveredEvent = {
        "id": "evt_2",
        "type": "tracking.delivered",
        "created_at": "2026-01-01T00:00:00Z",
        "data": tracking,
    }
    assert trackified.tracking_of(changed) is tracking
    assert Trackified(api_key="k").webhooks.tracking_of(delivered) is tracking
