"""Runtime configuration loaded from environment variables.

This module must not import any other project module — it sits at the
bottom of the dependency graph so everything else can depend on it.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Literal

from dotenv import find_dotenv, load_dotenv

# Search upward from this file until a .env is found.
# This works regardless of the working directory (e.g. when PyCharm
# runs main.py directly). Existing env vars take precedence.
load_dotenv(find_dotenv(usecwd=True), override=False)

logger = logging.getLogger(__name__)

DisplayBackend = Literal["terminal", "eink", "lcd", "web"]


def _env(key: str, default: str = "") -> str:
    """Read an env var, stripping whitespace."""
    return os.getenv(key, default).strip()


def _env_int(key: str, default: int) -> int:
    """Read an env var as int with a fallback."""
    raw = os.getenv(key)
    if raw is None:
        return default
    try:
        return int(raw.strip())
    except ValueError as exc:
        raise ValueError(f"{key} must be an integer, got {raw!r}") from exc


@dataclass(frozen=True)
class Settings:
    """Immutable app settings — override via env vars or a .env file.

    Required variables (will raise on missing):
        API_BASE_URL
        STOP_ID

    Optional variables:
        API_KEY          — auth token if the API needs one
        POLL_INTERVAL    — seconds between fetches (default 30)
        DISPLAY_BACKEND  — terminal | eink | lcd | web (default terminal)
        MAX_DEPARTURES   — rows shown on the display (default 10)
        LOG_LEVEL        — Python log level name (default INFO)
        LOG_FILE         — path to log file; omit for stderr only
    """

    # --- API ---
    # default_factory ensures env vars are read at instantiation time,
    # not at class definition time — this makes the class testable with
    # patch.dict(os.environ, ...).
    api_base_url: str = field(default_factory=lambda: _env("API_BASE_URL"))
    api_key: str = field(default_factory=lambda: _env("API_KEY"))
    stop_id: str = field(default_factory=lambda: _env("STOP_ID"))
    poll_interval_seconds: int = field(
        default_factory=lambda: _env_int("POLL_INTERVAL", 30)
    )

    # --- Display ---
    display_backend: DisplayBackend = field(default_factory=lambda: _env("DISPLAY_BACKEND", "terminal"))  # type: ignore[assignment]
    max_departures: int = field(default_factory=lambda: _env_int("MAX_DEPARTURES", 10))

    # --- Logging ---
    log_level: str = field(default_factory=lambda: _env("LOG_LEVEL", "INFO").upper())
    log_file: str = field(default_factory=lambda: _env("LOG_FILE"))

    def __post_init__(self) -> None:
        """Validate required fields and value ranges."""
        missing = []
        if not self.api_base_url:
            missing.append("API_BASE_URL")
        if not self.stop_id:
            missing.append("STOP_ID")
        if missing:
            raise ValueError(
                f"Required environment variable(s) not set: {', '.join(missing)}. "
                f"Copy .env.example to .env and fill them in."
            )

        allowed_backends: tuple[DisplayBackend, ...] = (
            "terminal",
            "eink",
            "lcd",
            "web",
        )
        if self.display_backend not in allowed_backends:
            raise ValueError(
                f"DISPLAY_BACKEND must be one of {allowed_backends}, "
                f"got {self.display_backend!r}"
            )

        if self.poll_interval_seconds < 5:
            raise ValueError(
                "POLL_INTERVAL must be ≥ 5 seconds to avoid hammering the API"
            )

        # Validate log level is recognised by Python's logging module
        numeric_level = logging.getLevelName(self.log_level)
        if not isinstance(numeric_level, int):
            raise ValueError(
                f"LOG_LEVEL must be a valid level (DEBUG, INFO, WARNING, ERROR), "
                f"got {self.log_level!r}"
            )

    def setup_logging(self) -> None:
        """Configure the root logger based on settings. Call once at startup."""
        handlers: list[logging.Handler] = [logging.StreamHandler()]

        if self.log_file:
            handlers.append(logging.FileHandler(self.log_file))

        logging.basicConfig(
            level=self.log_level,
            format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
            datefmt="%H:%M:%S",
            handlers=handlers,
        )
