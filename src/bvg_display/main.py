"""Application entry point.

This module wires config, client, and display together and runs the
poll loop. It should not contain business logic -- just orchestration.
"""

from __future__ import annotations

import asyncio
import logging
import time

from bvg_display.client import TransitClient
from bvg_display.config import DisplayBackend, Settings
from bvg_display.display import DisplayRenderer, TerminalRenderer

logger = logging.getLogger(__name__)

# Backoff caps at 5 minutes no matter how many consecutive failures.
MAX_BACKOFF_SECONDS = 300


def _build_renderer(settings: Settings) -> DisplayRenderer:
    """Pick the display backend based on config."""
    backend: DisplayBackend = settings.display_backend
    match backend:
        case "terminal":
            return TerminalRenderer(
                max_rows=settings.max_departures,
                clear_screen=True,
            )
        case "eink":
            raise NotImplementedError(
                f"Display backend '{backend}' is not implemented yet"
            )
        case "lcd":
            raise NotImplementedError(
                f"Display backend '{backend}' is not implemented yet"
            )
        case "web":
            raise NotImplementedError(
                f"Display backend '{backend}' is not implemented yet"
            )
        case _:
            raise ValueError(f"Unknown display backend: {backend!r}")


def _backoff_seconds(
    consecutive_failures: int,
    base_interval: int,
) -> int:
    """Calculate sleep time with exponential backoff.

    0 failures -> base_interval  (normal)
    1 failure  -> base_interval * 2
    2 failures -> base_interval * 4
    3 failures -> base_interval * 8
    ...capped at MAX_BACKOFF_SECONDS
    """
    if consecutive_failures <= 0:
        return base_interval
    delay = base_interval * (2**consecutive_failures)
    return min(delay, MAX_BACKOFF_SECONDS)


async def _async_main() -> None:
    settings = Settings()
    settings.setup_logging()

    renderer = _build_renderer(settings)

    logger.info(
        "transit-display starting -- stop=%s  interval=%ds  backend=%s",
        settings.stop_id,
        settings.poll_interval_seconds,
        settings.display_backend,
    )

    last_success: float | None = None
    consecutive_failures: int = 0

    async with TransitClient(settings) as client:
        while True:
            t0 = time.monotonic()
            stop_info = await client.get_departures(
                settings.stop_id,
                results=settings.max_departures,
            )
            elapsed = time.monotonic() - t0

            has_data = len(stop_info.departures) > 0

            if has_data:
                last_success = time.monotonic()
                consecutive_failures = 0
                logger.info(
                    "Fetched %d departures for %s in %.1fs",
                    len(stop_info.departures),
                    stop_info.name or settings.stop_id,
                    elapsed,
                )
            else:
                consecutive_failures += 1
                logger.warning(
                    "No departures returned (%.1fs) -- failure #%d",
                    elapsed,
                    consecutive_failures,
                )

            # Data is "stale" if we haven't had a successful fetch
            # in more than 2x the poll interval.
            stale = (
                last_success is not None
                and (time.monotonic() - last_success)
                > settings.poll_interval_seconds * 2
            )

            renderer.render(stop_info, stale=stale)

            sleep_time = _backoff_seconds(
                consecutive_failures, settings.poll_interval_seconds
            )
            if consecutive_failures > 0:
                logger.info("Backing off -- next poll in %ds", sleep_time)

            await asyncio.sleep(sleep_time)


def main() -> None:
    try:
        asyncio.run(_async_main())
    except KeyboardInterrupt:
        logger.info("Shutting down")


if __name__ == "__main__":
    main()
