#!/usr/bin/env python3
"""One-shot fetch — run manually to verify the client works against the real API.

Usage:
    poetry run python scripts/fetch_once.py
"""

import asyncio
import logging

from bvg_display.config import Settings
from bvg_display.client import TransitClient

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s  %(levelname)-8s  %(message)s")


async def main() -> None:
    settings = Settings()
    print(f"Fetching departures for stop {settings.stop_id}…\n")

    async with TransitClient(settings) as client:
        info = await client.get_departures(settings.stop_id, results=10)

    if not info.departures:
        print("No departures found. Check your TRANSIT_STOP_ID.")
        return

    print(f"  {info.name}")
    print(f"  {'─' * 50}")

    for dep in info.departures:
        delay = ""
        if dep.delay_seconds > 0:
            delay = f"  +{dep.delay_seconds // 60}min"
        elif dep.delay_seconds < 0:
            delay = f"  {dep.delay_seconds // 60}min"

        eta = f"{dep.minutes_until}min" if dep.minutes_until >= 0 else "now"
        print(f"  {dep.line:>5}  →  {dep.destination:<28}  {eta:>6}{delay}")


if __name__ == "__main__":
    asyncio.run(main())
