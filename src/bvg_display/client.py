"""HTTP client for the v6.bvg.transport.rest API.

This module owns all HTTP concerns — retries, error handling, rate limits.
It must not know about display rendering or configuration loading.
"""

from __future__ import annotations

import logging
from types import TracebackType

import httpx

from bvg_display.config import Settings
from bvg_display.models import StopInfo

logger = logging.getLogger(__name__)

# Default API base URL for the BVG REST API
BVG_API_BASE_URL = "https://v6.bvg.transport.rest"


class TransitClient:
    """Async client for the BVG public transport REST API."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        base_url = settings.api_base_url or BVG_API_BASE_URL
        headers: dict[str, str] = {"Accept": "application/json"}
        if settings.api_key:
            headers["Authorization"] = f"Bearer {settings.api_key}"

        self._http = httpx.AsyncClient(
            base_url=base_url,
            headers=headers,
            timeout=10.0,
        )

    async def __aenter__(self) -> TransitClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()

    async def get_departures(
        self,
        stop_id: str,
        *,
        duration: int = 30,
        results: int | None = None,
    ) -> StopInfo:
        """Fetch upcoming departures for a stop.

        Args:
            stop_id: BVG stop ID (e.g. "900017101" for U Mehringdamm).
            duration: Time window in minutes to look ahead.
            results: Max number of departures to return (API default if None).

        Returns:
            A StopInfo with parsed departures. On any error, returns an
            empty StopInfo so the display can show "no data" instead of
            crashing.
        """
        params: dict[str, int] = {"duration": duration}
        if results is not None:
            params["results"] = results

        try:
            response = await self._http.get(
                f"/stops/{stop_id}/departures",
                params=params,
            )
            response.raise_for_status()

        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status == 429:
                logger.warning(
                    "Rate-limited by API (429). Back off and retry later."
                )
            else:
                body = exc.response.text[:200]
                logger.error("API returned %d: %s", status, body)
            return StopInfo(stop_id=stop_id)

        except httpx.ConnectError:
            logger.error(
                "Cannot reach API at %s", self._http.base_url
            )
            return StopInfo(stop_id=stop_id)

        except httpx.TimeoutException:
            logger.error("Request to API timed out")
            return StopInfo(stop_id=stop_id)

        data = response.json()
        return StopInfo.from_api_response(stop_id, data)

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._http.aclose()

