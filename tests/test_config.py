"""Tests for Settings validation and defaults."""

import os
from unittest.mock import patch

import pytest

from bvg_display.config import Settings


def _env(**overrides: str) -> dict[str, str]:
    """Build a minimal valid env, then apply overrides."""
    base = {
        "API_BASE_URL": "https://api.example.com",
        "STOP_ID": "900000100003",
    }
    base.update(overrides)
    return base


class TestSettingsValidation:
    def test_missing_stop_id_raises(self) -> None:
        env = _env(STOP_ID="")
        with patch.dict(os.environ, env, clear=True), pytest.raises(ValueError, match="STOP_ID"):
            Settings()

    def test_missing_api_base_url_raises(self) -> None:
        env = _env(API_BASE_URL="")
        with patch.dict(os.environ, env, clear=True), pytest.raises(ValueError, match="API_BASE_URL"):
            Settings()

    def test_invalid_backend_raises(self) -> None:
        env = _env(DISPLAY_BACKEND="hologram")
        with patch.dict(os.environ, env, clear=True), pytest.raises(ValueError, match="hologram"):
            Settings()

    def test_poll_interval_too_low_raises(self) -> None:
        env = _env(POLL_INTERVAL="2")
        with patch.dict(os.environ, env, clear=True), pytest.raises(ValueError, match="≥ 5"):
            Settings()

    def test_poll_interval_not_a_number_raises(self) -> None:
        env = _env(POLL_INTERVAL="fast")
        with patch.dict(os.environ, env, clear=True), pytest.raises(ValueError, match="integer"):
            Settings()

    def test_invalid_log_level_raises(self) -> None:
        env = _env(LOG_LEVEL="VERBOSE")
        with patch.dict(os.environ, env, clear=True), pytest.raises(ValueError, match="VERBOSE"):
            Settings()


class TestSettingsDefaults:
    def test_defaults_with_required_vars(self) -> None:
        with patch.dict(os.environ, _env(), clear=True):
            s = Settings()
        assert s.poll_interval_seconds == 30
        assert s.display_backend == "terminal"
        assert s.max_departures == 10
        assert s.log_level == "INFO"
        assert s.log_file == ""
        assert s.api_key == ""

    def test_overrides_applied(self) -> None:
        env = _env(
            POLL_INTERVAL="60",
            DISPLAY_BACKEND="eink",
            MAX_DEPARTURES="6",
            LOG_LEVEL="DEBUG",
        )
        with patch.dict(os.environ, env, clear=True):
            s = Settings()
        assert s.poll_interval_seconds == 60
        assert s.display_backend == "eink"
        assert s.max_departures == 6
        assert s.log_level == "DEBUG"
