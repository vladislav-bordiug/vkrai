from __future__ import annotations

import logging
from typing import Any

import httpx


logger = logging.getLogger(__name__)


class HttpToolError(RuntimeError):
    pass


class HttpClient:
    def __init__(self, timeout: int = 20):
        self.timeout = timeout

    async def get(self, url: str, headers: dict[str, str] | None = None, params: dict[str, Any] | None = None) -> dict:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers, params=params)
        except httpx.HTTPError as exc:
            logger.exception("HTTP GET failed", extra={"url": url})
            raise HttpToolError(f"HTTP GET failed for {url}: {exc}") from exc
        return self._parse(response)

    async def post(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        json_body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, headers=headers, json=json_body, params=params)
        except httpx.HTTPError as exc:
            logger.exception("HTTP POST failed", extra={"url": url})
            raise HttpToolError(f"HTTP POST failed for {url}: {exc}") from exc
        return self._parse(response)

    async def patch(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        json_body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.patch(url, headers=headers, json=json_body, params=params)
        except httpx.HTTPError as exc:
            logger.exception("HTTP PATCH failed", extra={"url": url})
            raise HttpToolError(f"HTTP PATCH failed for {url}: {exc}") from exc
        return self._parse(response)

    @staticmethod
    def _parse(response: httpx.Response) -> dict:
        if not response.is_success:
            logger.error(
                "HTTP request failed",
                extra={
                    "method": response.request.method,
                    "url": str(response.request.url),
                    "status_code": response.status_code,
                    "response_text": response.text[:1500],
                },
            )
            raise HttpToolError(f"HTTP {response.status_code}: {response.text}")
        if not response.text:
            return {}
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            try:
                return response.json()
            except ValueError as exc:
                logger.exception(
                    "Failed to decode JSON response",
                    extra={
                        "method": response.request.method,
                        "url": str(response.request.url),
                        "status_code": response.status_code,
                    },
                )
                raise HttpToolError(f"Invalid JSON response: {exc}") from exc
        return {"text": response.text}
