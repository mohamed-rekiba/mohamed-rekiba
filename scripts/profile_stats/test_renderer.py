"""Tests for SVG renderer. Require concrete SvgRendererImpl (Red until implemented)."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from profile_stats.renderer import SvgRendererImpl
from profile_stats.types import (
    ContributionStats,
    LanguageEntry,
    ProfileStatsData,
    WrappedMetrics,
)


def _sample_data() -> ProfileStatsData:
    return ProfileStatsData(
        contribution=ContributionStats(past_year=848, total=2026),
        languages=[
            LanguageEntry("Go", 27.05, "#00ADD8"),
            LanguageEntry("JavaScript", 20.23, "#f1e05a"),
        ],
        wrapped=WrappedMetrics(
            universal_rank="Top 15%",
            longest_streak_days=12,
            most_active_month="October",
            most_active_day="Thursday",
            top_language="Go",
            power_level="Pro Mode",
        ),
    )


def test_render_wrapped_produces_file_with_metrics() -> None:
    """Wrapped SVG file contains the expected metric values."""
    renderer = SvgRendererImpl()
    data = _sample_data()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "wrapped.svg"
        renderer.render_wrapped(data, path)
        assert path.exists()
        content = path.read_text()
        assert "GitHub Wrapped Metrics" in content
        assert "Top 15%" in content
        assert "12 days" in content
        assert "October" in content
        assert "Thursday" in content
        assert "Go" in content
        assert "Pro Mode" in content


def test_render_wrapped_is_valid_svg() -> None:
    """Output is valid SVG (root element present)."""
    renderer = SvgRendererImpl()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "wrapped.svg"
        renderer.render_wrapped(_sample_data(), path)
        content = path.read_text()
        assert content.strip().startswith("<svg ")
        assert "</svg>" in content


def test_render_stats_produces_file_with_contributions_and_languages() -> None:
    """Stats SVG contains total contribution number and language distribution (past year hidden)."""
    renderer = SvgRendererImpl()
    data = _sample_data()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "stats.svg"
        renderer.render_stats(data, path)
        assert path.exists()
        content = path.read_text()
        assert "2026" in content
        assert "Total Contributions" in content
        assert "Language Distribution" in content
        assert "Go" in content
        assert "JavaScript" in content


def test_render_stats_is_valid_svg() -> None:
    """Stats output is valid SVG."""
    renderer = SvgRendererImpl()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "stats.svg"
        renderer.render_stats(_sample_data(), path)
        content = path.read_text()
        assert content.strip().startswith("<svg ")
        assert "</svg>" in content
