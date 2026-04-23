"""Rendering logic for the display.

This module defines the base `DisplayRenderer` interface and ships a
`TerminalRenderer` that prints to stdout. Subclass for real hardware
(e-ink, LCD, web) — each backend only needs to implement `render()`.
"""

from __future__ import annotations

import os
import shutil
from abc import ABC, abstractmethod
from datetime import datetime, timezone

from bvg_display.models import StopInfo


class DisplayRenderer(ABC):
    """Base class for all display backends."""

    @abstractmethod
    def render(self, stop_info: StopInfo, *, stale: bool = False) -> None:
        """Render departures to the display.

        Args:
            stop_info: The stop and its upcoming departures.
            stale: If True, the data may be outdated (API unreachable).
        """


class TerminalRenderer(DisplayRenderer):
    """Renders departures to stdout, clearing the screen each cycle."""

    def __init__(self, *, max_rows: int = 10, clear_screen: bool = True) -> None:
        self._max_rows = max_rows
        self._clear_screen = clear_screen

    def render(self, stop_info: StopInfo, *, stale: bool = False) -> None:
        if self._clear_screen:
            os.system("cls" if os.name == "nt" else "clear")

        width = shutil.get_terminal_size((60, 20)).columns
        now = datetime.now().strftime("%H:%M")

        # ── Header ──────────────────────────────────────────────
        name = stop_info.name or stop_info.stop_id
        header = f"  {name}  ·  {now}"
        if stale:
            header += "  ⚠ stale"
        print(header)
        print(f"  {'─' * min(width - 4, 56)}")

        # ── No data ────────────────────────────────────────────
        if not stop_info.departures:
            print()
            print("  ⏳  Waiting for data…")
            print()
            return

        # ── Departure rows ──────────────────────────────────────
        for dep in stop_info.departures[: self._max_rows]:
            line_col = f"{dep.line:>5}"
            dest = _truncate(dep.destination, 24)
            minutes = dep.minutes_until

            if minutes <= 0:
                eta = "  now"
            elif minutes == 1:
                eta = " 1min"
            else:
                eta = f"{minutes:>2}min"

            delay = _format_delay(dep.delay_seconds)

            print(f"  {line_col}  →  {dest:<24}  {eta}{delay}")

        print()

    @staticmethod
    def format_row(line: str, destination: str, eta: str, delay: str) -> str:
        """Format a single departure row (useful for testing)."""
        dest = _truncate(destination, 24)
        return f"  {line:>5}  →  {dest:<24}  {eta}{delay}"


def _truncate(text: str, max_len: int) -> str:
    """Truncate text with ellipsis if it exceeds max_len."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def _format_delay(delay_seconds: int) -> str:
    """Format delay as a compact string, empty if on time."""
    if delay_seconds <= 0:
        return ""
    minutes = delay_seconds // 60
    if minutes == 0:
        return f"  +{delay_seconds}s"
    return f"  +{minutes}min"
