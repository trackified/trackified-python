"""Optional live smoke test: runs only when TRACKIFIED_API_KEY is set.

Creates one tracking and deletes it."""

from __future__ import annotations

import os

import pytest

from trackified import Trackified

pytestmark = pytest.mark.skipif(
    not os.environ.get("TRACKIFIED_API_KEY"), reason="TRACKIFIED_API_KEY not set"
)


def test_live_create_get_list_delete() -> None:
    with Trackified() as client:
        usage = client.usage.get()
        assert usage["plan"]
        tracking = client.trackings.create("9434650110837017316201", carrier="usps")
        try:
            assert client.trackings.get(tracking["id"])["id"] == tracking["id"]
            page = client.trackings.list(tracking_number="9434650110837017316201", limit=5)
            assert any(t["id"] == tracking["id"] for t in page["data"])
            assert client.carriers.detect("9434650110837017316201")["candidates"]
        finally:
            assert client.trackings.delete(tracking["id"])["deleted"]
