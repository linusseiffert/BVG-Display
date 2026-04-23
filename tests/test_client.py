"""Tests for the BVG API client."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
import respx

from bvg_display.client import TransitClient
from bvg_display.config import Settings

FIXTURES = Path(__file__).parent / "fixtures"

VALID_ENV = {
    "API_BASE_URL": "https://v6.bvg.transport.rest",
    "STOP_ID": "900017101",
}


def _settings(**overrides: str) -> Settings:
    env = {**VALID_ENV, **overrides}
    with patch.dict(os.environ, env, clear=True):
        return Settings()


def _fixture_json(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


# ── Happy path ──────────────────────────────────────────────────


class TestGetDeparturesOk:
    @respx.mock
    @pytest.mark.asyncio
    async def test_returns_parsed_departures(self) -> None:
        fixture = _fixture_json("departures_ok.json")
        respx.get("https://v6.bvg.transport.rest/stops/900017101/departures").mock(
            return_value=httpx.Response(200, json=fixture)
        )

        settings = _settings()
        async with TransitClient(settings) as client:
            info = await client.get_departures("900017101")

        assert info.stop_id == "900017101"
        assert info.name == "U Mehringdamm"
        assert len(info.departures) == 5
        assert info.departures[0].line == "U6"
        assert info.departures[0].destination == "U Alt-Tegel"

    @respx.mock
    @pytest.mark.asyncio
    async def test_empty_departures(self) -> None:
        fixture = _fixture_json("departures_empty.json")
        respx.get("https://v6.bvg.transport.rest/stops/900017101/departures").mock(
            return_value=httpx.Response(200, json=fixture)
        )

        settings = _settings()
        async with TransitClient(settings) as client:
            info = await client.get_departures("900017101")

        assert info.departures == []

    @respx.mock
    @pytest.mark.asyncio
    async def test_passes_duration_and_results_params(self) -> None:
        route = respx.get(
            "https://v6.bvg.transport.rest/stops/900017101/departures"
        ).mock(return_value=httpx.Response(200, json={"departures": []}))

        settings = _settings()
        async with TransitClient(settings) as client:
            await client.get_departures("900017101", duration=15, results=5)

        assert route.called
        request = route.calls.last.request
        assert "duration=15" in str(request.url)
        assert "results=5" in str(request.url)


# ── Error handling ──────────────────────────────────────────────


class TestGetDeparturesErrors:
    @respx.mock
    @pytest.mark.asyncio
    async def test_500_returns_empty_stop_info(self) -> None:
        respx.get("https://v6.bvg.transport.rest/stops/900017101/departures").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )

        settings = _settings()
        async with TransitClient(settings) as client:
            info = await client.get_departures("900017101")

        assert info.stop_id == "900017101"
        assert info.departures == []
        assert info.name == ""

    @respx.mock
    @pytest.mark.asyncio
    async def test_429_returns_empty_stop_info(self) -> None:
        respx.get("https://v6.bvg.transport.rest/stops/900017101/departures").mock(
            return_value=httpx.Response(429, text="Too Many Requests")
        )

        settings = _settings()
        async with TransitClient(settings) as client:
            info = await client.get_departures("900017101")

        assert info.departures == []

    @respx.mock
    @pytest.mark.asyncio
    async def test_network_error_returns_empty_stop_info(self) -> None:
        respx.get("https://v6.bvg.transport.rest/stops/900017101/departures").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        settings = _settings()
        async with TransitClient(settings) as client:
            info = await client.get_departures("900017101")

        assert info.departures == []

    @respx.mock
    @pytest.mark.asyncio
    async def test_timeout_returns_empty_stop_info(self) -> None:
        respx.get("https://v6.bvg.transport.rest/stops/900017101/departures").mock(
            side_effect=httpx.ReadTimeout("timed out")
        )

        settings = _settings()
        async with TransitClient(settings) as client:
            info = await client.get_departures("900017101")

        assert info.departures == []


# ── Context manager ─────────────────────────────────────────────


class TestClientLifecycle:
    @respx.mock
    @pytest.mark.asyncio
    async def test_context_manager_closes_cleanly(self) -> None:
        respx.get("https://v6.bvg.transport.rest/stops/900017101/departures").mock(
            return_value=httpx.Response(200, json={"departures": []})
        )

        settings = _settings()
        async with TransitClient(settings) as client:
            await client.get_departures("900017101")
        # No exception = close() worked
