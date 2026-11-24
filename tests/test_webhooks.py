from __future__ import annotations

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
