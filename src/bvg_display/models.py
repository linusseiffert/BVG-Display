"""Domain models for transit data.

All JSON-shape knowledge lives here so the client module stays generic.
These models map the v6.bvg.transport.rest response format.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# BVG product types as returned by the API
Product = str  # "subway", "suburban", "tram", "bus", "ferry", "express", "regional"


def _parse_dt(value: str | None) -> datetime | None:
    """Parse an ISO 8601 datetime string from the API, or return None."""
    if value is None:
        return None
    return datetime.fromisoformat(value)


@dataclass(frozen=True)
class Departure:
    """A single upcoming departure from a stop."""

    line: str
    destination: str
    scheduled: datetime
    expected: datetime | None = None
    product: Product = ""
    platform: str | None = None
    trip_id: str = ""

    @property
    def delay_seconds(self) -> int:
        """Delay in seconds (positive = late). 0 if no real-time data."""
        if self.expected is None:
            return 0
        return int((self.expected - self.scheduled).total_seconds())

    @property
    def minutes_until(self) -> int:
        """Minutes from now until the (expected or scheduled) departure."""
        target = self.expected or self.scheduled
        delta = target - datetime.now(tz=target.tzinfo)
        return int(delta.total_seconds() / 60)

    @classmethod
    def from_api_response(cls, data: dict) -> Departure:
        """Parse a single departure dict from the BVG REST API.

        Expected shape (v6.bvg.transport.rest /stops/:id/departures):
        {
            "tripId": "1|34562|7|86|29042020",
            "direction": "U Alt-Tegel",
            "line": {"name": "U6", "product": "subway", ...},
            "when": "2020-04-29T19:31:00+02:00",       # actual / null
            "plannedWhen": "2020-04-29T19:30:00+02:00", # scheduled
            "delay": 60,                                # seconds / null
            "platform": "1",
            ...
        }
        """
        line_data = data.get("line") or {}
        return cls(
            line=line_data.get("name", "?"),
            destination=data.get("direction", ""),
            scheduled=_parse_dt(data["plannedWhen"]),  # type: ignore[arg-type]
            expected=_parse_dt(data.get("when")),
            product=line_data.get("product", ""),
            platform=data.get("platform"),
            trip_id=data.get("tripId", ""),
        )


@dataclass(frozen=True)
class StopInfo:
    """A stop/station with its upcoming departures."""

    stop_id: str
    name: str = ""
    departures: list[Departure] = field(default_factory=list)

    @classmethod
    def from_api_response(cls, stop_id: str, data: dict) -> StopInfo:
        """Parse the top-level /stops/:id/departures response.

        The response has the shape:
        {
            "departures": [ ... ]
        }

        The stop name comes from the nested stop object inside each
        departure, or can be empty if there are no departures.
        """
        raw_departures = data.get("departures") or []
        departures: list[Departure] = []

        for i, raw in enumerate(raw_departures):
            try:
                departures.append(Departure.from_api_response(raw))
            except (KeyError, TypeError, ValueError) as exc:
                logger.warning("Skipping departure %d: %s", i, exc)

        # The stop name is embedded in each departure's "stop" object.
        name = ""
        if raw_departures:
            first_stop = raw_departures[0].get("stop") or {}
            name = first_stop.get("name", "")

        return cls(stop_id=stop_id, name=name, departures=departures)
