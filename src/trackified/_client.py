from __future__ import annotations

import asyncio
import os
import random
import time
from typing import Any, Callable, Dict, Mapping, Optional, TypedDict

import httpx

from ._errors import ConnectionError, TrackifiedError, error_from_response, parse_retry_after
from ._version import __version__


class RequestInfo(TypedDict):
    """Passed to ``on_request`` before each attempt. ``attempt`` starts at 1."""

    method: str
    url: str
    attempt: int
    idempotency_key: Optional[str]


class ResponseInfo(TypedDict):
    """Passed to ``on_response`` after each attempt. ``status`` is None when no response came;
    ``error`` is the typed error for status >= 400 or a connection failure, else None."""

    method: str
    url: str
    attempt: int
    status: Optional[int]
    request_id: Optional[str]
    idempotent_replayed: bool
    duration_ms: float
    error: Optional[TrackifiedError]


OnRequest = Callable[[RequestInfo], object]
OnResponse = Callable[[ResponseInfo], object]

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
        on_request: Optional[OnRequest] = None,
        on_response: Optional[OnResponse] = None,
    ) -> None:
        api_key = api_key or os.environ.get("TRACKIFIED_API_KEY")
        if not api_key:
            raise TrackifiedError(
                "No API key. Pass api_key= or set the TRACKIFIED_API_KEY environment variable."
            )
        self.api_key = api_key
        url = (base_url or os.environ.get("TRACKIFIED_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        # Accept ".../v1" too: paths already start with /v1.
        self.base_url = url[: -len("/v1")] if url.endswith("/v1") else url
        self.timeout = timeout
        self.max_retries = max_retries
        self.on_request = on_request
        self.on_response = on_response

    @staticmethod
    def _call_hook(hook: Optional[Callable[[Any], object]], info: Any) -> None:
        if hook is None:
            return
        try:
            hook(info)
        except Exception:
            pass  # a broken hook must never break the request

    def _before(self, method: str, url: str, attempt: int, key: Optional[str]) -> float:
        info: RequestInfo = {
            "method": method,
            "url": url,
            "attempt": attempt + 1,
            "idempotency_key": key,
        }
        self._call_hook(self.on_request, info)
        return time.monotonic()

    def _after(
        self,
        method: str,
        url: str,
        attempt: int,
        start: float,
        response: Optional[httpx.Response],
        error: Optional[TrackifiedError],
    ) -> None:
        headers = response.headers if response is not None else httpx.Headers()
        info: ResponseInfo = {
            "method": method,
            "url": url,
            "attempt": attempt + 1,
            "status": response.status_code if response is not None else None,
            "request_id": headers.get("x-request-id") or (error.request_id if error else None),
            "idempotent_replayed": headers.get("idempotent-replayed") == "true",
            "duration_ms": (time.monotonic() - start) * 1000,
            "error": error,
        }
        self._call_hook(self.on_response, info)

    @staticmethod
    def _connection_error(e: httpx.TransportError) -> ConnectionError:
        if isinstance(e, httpx.TimeoutException):
            return ConnectionError(f"Request timed out: {e}", code="timeout")
        return ConnectionError(f"Connection error: {e}", code="connection")

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
    def _error(response: httpx.Response) -> Optional[TrackifiedError]:
        return error_from_response(response) if response.status_code >= 400 else None

    @staticmethod
    def _json(response: httpx.Response) -> Any:
        return response.json() if response.content else {}


class SyncClient(_BaseClient):
    def __init__(
        self,
        api_key: Optional[str],
        base_url: Optional[str],
        timeout: float,
        max_retries: int,
        http_client: Optional[httpx.Client],
        on_request: Optional[OnRequest] = None,
        on_response: Optional[OnResponse] = None,
    ) -> None:
        super().__init__(api_key, base_url, timeout, max_retries, on_request, on_response)
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
        url = self.base_url + path
        for attempt in range(self.max_retries + 1):
            last = attempt == self.max_retries
            start = self._before(method, url, attempt, idempotency_key)
            try:
                response = self._http.request(
                    method,
                    url,
                    params=self._params(params),
                    json=json,
                    headers=headers,
                    timeout=self.timeout,
                )
            except httpx.TransportError as e:
                conn_error = self._connection_error(e)
                self._after(method, url, attempt, start, None, conn_error)
                if last:
                    raise conn_error from e
                time.sleep(self._delay(attempt, None))
                continue
            error = self._error(response)
            self._after(method, url, attempt, start, response, error)
            if last or not self._should_retry(response):
                if error is not None:
                    raise error
                return self._json(response)
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
        on_request: Optional[OnRequest] = None,
        on_response: Optional[OnResponse] = None,
    ) -> None:
        super().__init__(api_key, base_url, timeout, max_retries, on_request, on_response)
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
        url = self.base_url + path
        for attempt in range(self.max_retries + 1):
            last = attempt == self.max_retries
            start = self._before(method, url, attempt, idempotency_key)
            try:
                response = await self._http.request(
                    method,
                    url,
                    params=self._params(params),
                    json=json,
                    headers=headers,
                    timeout=self.timeout,
                )
            except httpx.TransportError as e:
                conn_error = self._connection_error(e)
                self._after(method, url, attempt, start, None, conn_error)
                if last:
                    raise conn_error from e
                await asyncio.sleep(self._delay(attempt, None))
                continue
            error = self._error(response)
            self._after(method, url, attempt, start, response, error)
            if last or not self._should_retry(response):
                if error is not None:
                    raise error
                return self._json(response)
            await asyncio.sleep(self._delay(attempt, response))
        raise AssertionError("unreachable")

    async def aclose(self) -> None:
        await self._http.aclose()
