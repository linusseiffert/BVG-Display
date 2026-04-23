"""Tests for the terminal display renderer."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from bvg_display.display import TerminalRenderer, _truncate, _format_delay
from bvg_display.models import Departure, StopInfo

TZ_BERLIN = timezone(timedelta(hours=2))


def _make_departure(
    line: str = "U6",
    destination: str = "U Alt-Tegel",
    minutes_from_now: int = 5,
    delay_seconds: int = 0,
    product: str = "subway",
) -> Departure:
    """Build a Departure relative to 'now' for easy testing."""
    now = datetime.now(tz=TZ_BERLIN)
    scheduled = now + timedelta(minutes=minutes_from_now)
    expected = (
        scheduled + timedelta(seconds=delay_seconds) if delay_seconds else scheduled
    )
    return Departure(
        line=line,
        destination=destination,
        scheduled=scheduled,
        expected=expected,
        product=product,
    )


def _make_stop_info(
    departures: list[Departure] | None = None,
    name: str = "U Mehringdamm",
    stop_id: str = "900017101",
) -> StopInfo:
    return StopInfo(
        stop_id=stop_id,
        name=name,
        departures=departures or [],
    )


# ── Rendering output ────────────────────────────────────────────


class TestTerminalRendererOutput:
    def test_renders_header_with_stop_name(self, capsys) -> None:
        renderer = TerminalRenderer(clear_screen=False)
        info = _make_stop_info(departures=[_make_departure()])
        renderer.render(info)

        output = capsys.readouterr().out
        assert "U Mehringdamm" in output

    def test_renders_departure_rows(self, capsys) -> None:
        deps = [
            _make_departure(line="U6", destination="U Alt-Tegel", minutes_from_now=3),
            _make_departure(line="M19", destination="S Südkreuz", minutes_from_now=7),
        ]
        renderer = TerminalRenderer(clear_screen=False)
        renderer.render(_make_stop_info(departures=deps))

        output = capsys.readouterr().out
        assert "U6" in output
        assert "U Alt-Tegel" in output
        assert "M19" in output
        assert "S Südkreuz" in output

    def test_shows_delay(self, capsys) -> None:
        deps = [_make_departure(delay_seconds=180)]
        renderer = TerminalRenderer(clear_screen=False)
        renderer.render(_make_stop_info(departures=deps))

        output = capsys.readouterr().out
        assert "+3min" in output

    def test_shows_now_for_imminent_departure(self, capsys) -> None:
        deps = [_make_departure(minutes_from_now=0)]
        renderer = TerminalRenderer(clear_screen=False)
        renderer.render(_make_stop_info(departures=deps))

        output = capsys.readouterr().out
        assert "now" in output


# ── No data state ───────────────────────────────────────────────


class TestTerminalRendererNoData:
    def test_shows_waiting_message(self, capsys) -> None:
        renderer = TerminalRenderer(clear_screen=False)
        renderer.render(_make_stop_info(departures=[]))

        output = capsys.readouterr().out
        assert "Waiting for data" in output

    def test_shows_stop_id_when_name_missing(self, capsys) -> None:
        renderer = TerminalRenderer(clear_screen=False)
        info = _make_stop_info(departures=[], name="")
        renderer.render(info)

        output = capsys.readouterr().out
        assert "900017101" in output


# ── Stale data ──────────────────────────────────────────────────


class TestTerminalRendererStale:
    def test_shows_stale_warning(self, capsys) -> None:
        renderer = TerminalRenderer(clear_screen=False)
        renderer.render(_make_stop_info(departures=[_make_departure()]), stale=True)

        output = capsys.readouterr().out
        assert "stale" in output

    def test_no_stale_warning_when_fresh(self, capsys) -> None:
        renderer = TerminalRenderer(clear_screen=False)
        renderer.render(_make_stop_info(departures=[_make_departure()]), stale=False)

        output = capsys.readouterr().out
        assert "stale" not in output


# ── Max rows ────────────────────────────────────────────────────


class TestTerminalRendererMaxRows:
    def test_limits_output_rows(self, capsys) -> None:
        deps = [
            _make_departure(line=f"L{i}", minutes_from_now=i + 1) for i in range(15)
        ]
        renderer = TerminalRenderer(max_rows=5, clear_screen=False)
        renderer.render(_make_stop_info(departures=deps))

        output = capsys.readouterr().out
        assert "L0" in output
        assert "L4" in output
        assert "L5" not in output


# ── Truncation & formatting helpers ────────────────────────────


class TestHelpers:
    def test_truncate_short_string(self) -> None:
        assert _truncate("Hello", 10) == "Hello"

    def test_truncate_long_string(self) -> None:
        assert (
            _truncate("S+U Alexanderplatz Bhf (Berlin)", 24)
            == "S+U Alexanderplatz Bhf …"
        )

    def test_truncate_exact_length(self) -> None:
        assert _truncate("Exactly24CharsLongText!!", 24) == "Exactly24CharsLongText!!"

    def test_format_delay_zero(self) -> None:
        assert _format_delay(0) == ""

    def test_format_delay_seconds(self) -> None:
        assert _format_delay(45) == "  +45s"

    def test_format_delay_minutes(self) -> None:
        assert _format_delay(180) == "  +3min"

    def test_format_delay_negative(self) -> None:
        assert _format_delay(-30) == ""
