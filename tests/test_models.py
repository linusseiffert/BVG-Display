"""Tests for domain models and BVG API parsing."""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

from bvg_display.models import Departure, StopInfo

FIXTURES = Path(__file__).parent / "fixtures"
TZ_BERLIN = timezone(timedelta(hours=2))


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


# ── Departure basics ────────────────────────────────────────────


class TestDeparture:
    def test_no_delay_when_no_expected(self) -> None:
        dep = Departure(
            line="U6",
            destination="Alt-Mariendorf",
            scheduled=datetime(2026, 1, 1, 8, 0, tzinfo=TZ_BERLIN),
        )
        assert dep.delay_seconds == 0

    def test_delay_calculated_from_expected(self) -> None:
        scheduled = datetime(2026, 1, 1, 8, 0, tzinfo=TZ_BERLIN)
        expected = scheduled + timedelta(minutes=3)
        dep = Departure(
            line="S1",
            destination="Wannsee",
            scheduled=scheduled,
            expected=expected,
        )
        assert dep.delay_seconds == 180

    def test_negative_delay_when_early(self) -> None:
        scheduled = datetime(2026, 1, 1, 8, 0, tzinfo=TZ_BERLIN)
        expected = scheduled - timedelta(seconds=30)
        dep = Departure(
            line="M10",
            destination="Warschauer Str.",
            scheduled=scheduled,
            expected=expected,
        )
        assert dep.delay_seconds == -30


# ── Departure.from_api_response ─────────────────────────────────


class TestDepartureFromApi:
    def test_parses_full_departure(self) -> None:
        raw = {
            "tripId": "1|34562|7|86|23042026",
            "direction": "U Alt-Tegel",
            "line": {"name": "U6", "product": "subway"},
            "when": "2026-04-23T14:32:00+02:00",
            "plannedWhen": "2026-04-23T14:30:00+02:00",
            "delay": 120,
            "platform": "2",
        }
        dep = Departure.from_api_response(raw)
        assert dep.line == "U6"
        assert dep.destination == "U Alt-Tegel"
        assert dep.product == "subway"
        assert dep.platform == "2"
        assert dep.delay_seconds == 120

    def test_when_null_means_no_realtime(self) -> None:
        """when=null typically means cancelled or no real-time data."""
        raw = {
            "tripId": "1|55201|12|86|23042026",
            "direction": "S Südkreuz",
            "line": {"name": "M19", "product": "bus"},
            "when": None,
            "plannedWhen": "2026-04-23T14:38:00+02:00",
            "delay": None,
            "platform": None,
        }
        dep = Departure.from_api_response(raw)
        assert dep.expected is None
        assert dep.delay_seconds == 0

    def test_missing_line_defaults_to_question_mark(self) -> None:
        raw = {
            "direction": "Somewhere",
            "line": None,
            "when": "2026-04-23T14:30:00+02:00",
            "plannedWhen": "2026-04-23T14:30:00+02:00",
        }
        dep = Departure.from_api_response(raw)
        assert dep.line == "?"


# ── StopInfo.from_api_response ──────────────────────────────────


class TestStopInfoFromApi:
    def test_parses_fixture(self) -> None:
        data = _load_fixture("departures_ok.json")
        info = StopInfo.from_api_response("900017101", data)
        assert info.stop_id == "900017101"
        assert info.name == "U Mehringdamm"
        assert len(info.departures) == 5

    def test_empty_departures(self) -> None:
        data = _load_fixture("departures_empty.json")
        info = StopInfo.from_api_response("900017101", data)
        assert info.departures == []
        assert info.name == ""

    def test_skips_malformed_departure(self) -> None:
        """One broken departure should not kill the whole response."""
        data = {
            "departures": [
                {
                    "direction": "U Alt-Tegel",
                    "line": {"name": "U6", "product": "subway"},
                    "when": "2026-04-23T14:30:00+02:00",
                    "plannedWhen": "2026-04-23T14:30:00+02:00",
                },
                {
                    # missing plannedWhen → will raise KeyError
                    "direction": "Broken",
                    "line": {"name": "X1"},
                },
                {
                    "direction": "S Südkreuz",
                    "line": {"name": "M19", "product": "bus"},
                    "when": "2026-04-23T14:38:00+02:00",
                    "plannedWhen": "2026-04-23T14:38:00+02:00",
                },
            ]
        }
        info = StopInfo.from_api_response("900017101", data)
        assert len(info.departures) == 2
        assert info.departures[0].line == "U6"
        assert info.departures[1].line == "M19"
