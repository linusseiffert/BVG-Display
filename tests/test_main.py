"""Tests for the main loop and renderer factory."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from bvg_display.display import TerminalRenderer
from bvg_display.main import _build_renderer
from bvg_display.config import Settings

VALID_ENV = {
    "API_BASE_URL": "https://v6.bvg.transport.rest",
    "STOP_ID": "900017101",
}


def _settings(**overrides: str) -> Settings:
    env = {**VALID_ENV, **overrides}
    with patch.dict(os.environ, env, clear=True):
        return Settings()


class TestBuildRenderer:
    def test_terminal_backend(self) -> None:
        settings = _settings(DISPLAY_BACKEND="terminal")
        renderer = _build_renderer(settings)
        assert isinstance(renderer, TerminalRenderer)

    def test_eink_not_implemented(self) -> None:
        settings = _settings(DISPLAY_BACKEND="eink")
        with pytest.raises(NotImplementedError, match="eink"):
            _build_renderer(settings)

    def test_lcd_not_implemented(self) -> None:
        settings = _settings(DISPLAY_BACKEND="lcd")
        with pytest.raises(NotImplementedError, match="lcd"):
            _build_renderer(settings)

    def test_web_not_implemented(self) -> None:
        settings = _settings(DISPLAY_BACKEND="web")
        with pytest.raises(NotImplementedError, match="web"):
            _build_renderer(settings)

    def test_respects_max_departures(self) -> None:
        settings = _settings(MAX_DEPARTURES="6")
        renderer = _build_renderer(settings)
        assert isinstance(renderer, TerminalRenderer)
        assert renderer._max_rows == 6
