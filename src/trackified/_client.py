from __future__ import annotations

import asyncio
import os
import random
import time
from typing import Any, Dict, Mapping, Optional

import httpx

from ._errors import ConnectionError, TrackifiedError, error_from_response, parse_retry_after
from ._version import __version__

DEFAULT_BASE_URL = "https://api.trackified.net"
DEFAULT_TIMEOUT = 30.0
DEFAULT_MAX_RETRIES = 2
MAX_RETRY_AFTER = 60.0


class _BaseClient:
    def __init__(
        self,
        api_key: Optional[str],
        base_url: Optional[str],
        timeout: float,
        max_retries: int,
    ) -> None:
        api_key = api_key or os.environ.get("TRACKIFIED_API_KEY")
        if not api_key:
            raise TrackifiedError(
                "No API key. Pass api_key= or set the TRACKIFIED_API_KEY environment variable."
            )
        self.api_key = api_key
        self.base_url = (
            base_url or os.environ.get("TRACKIFIED_BASE_URL") or DEFAULT_BASE_URL
        ).rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

    def _headers(self, idempotency_key: Optional[str]) -> Dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": f"trackified-python/{__version__}",
            "Accept": "application/json",
        }
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        return headers

    @staticmethod
    def _params(params: Optional[Mapping[str, Any]]) -> Optional[Dict[str, Any]]:
        return {k: v for k, v in params.items() if v is not None} if params else None

    @staticmethod
    def _should_retry(response: httpx.Response) -> bool:
        return response.status_code in (408, 429) or response.status_code >= 500

    @staticmethod
    def _delay(attempt: int, response: Optional[httpx.Response]) -> float:
        if response is not None and response.status_code == 429:
            retry_after = parse_retry_after(response)
            if retry_after is not None:
                return min(retry_after, MAX_RETRY_AFTER)
        return min(0.5 * 2.0**attempt, 8.0) * random.uniform(0.5, 1.0)

    @staticmethod
    def _result(response: httpx.Response) -> Any:
        if response.status_code >= 400:
            raise error_from_response(response)
        if not response.content:
            return {}
        return response.json()


class SyncClient(_BaseClient):
    def __init__(
        self,
        api_key: Optional[str],
        base_url: Optional[str],
        timeout: float,
        max_retries: int,
        http_client: Optional[httpx.Client],
    ) -> None:
        super().__init__(api_key, base_url, timeout, max_retries)
        self._http = http_client or httpx.Client(timeout=timeout)

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        json: Any = None,
        idempotency_key: Optional[str] = None,
    ) -> Any:
        headers = self._headers(idempotency_key)
        for attempt in range(self.max_retries + 1):
            last = attempt == self.max_retries
            try:
                response = self._http.request(
                    method,
                    self.base_url + path,
                    params=self._params(params),
                    json=json,
                    headers=headers,
                    timeout=self.timeout,
                )
            except httpx.TransportError as e:
                if last:
                    raise ConnectionError(f"Connection error: {e}") from e
                time.sleep(self._delay(attempt, None))
                continue
            if last or not self._should_retry(response):
                return self._result(response)
            time.sleep(self._delay(attempt, response))
        raise AssertionError("unreachable")

    def close(self) -> None:
        self._http.close()


class AsyncClient(_BaseClient):
    def __init__(
        self,
        api_key: Optional[str],
        base_url: Optional[str],
        timeout: float,
        max_retries: int,
        http_client: Optional[httpx.AsyncClient],
    ) -> None:
        super().__init__(api_key, base_url, timeout, max_retries)
        self._http = http_client or httpx.AsyncClient(timeout=timeout)

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        json: Any = None,
        idempotency_key: Optional[str] = None,
    ) -> Any:
        headers = self._headers(idempotency_key)
        for attempt in range(self.max_retries + 1):
            last = attempt == self.max_retries
            try:
                response = await self._http.request(
                    method,
                    self.base_url + path,
                    params=self._params(params),
                    json=json,
                    headers=headers,
                    timeout=self.timeout,
                )
            except httpx.TransportError as e:
                if last:
                    raise ConnectionError(f"Connection error: {e}") from e
                await asyncio.sleep(self._delay(attempt, None))
                continue
            if last or not self._should_retry(response):
                return self._result(response)
            await asyncio.sleep(self._delay(attempt, response))
        raise AssertionError("unreachable")

    async def aclose(self) -> None:
        await self._http.aclose()
