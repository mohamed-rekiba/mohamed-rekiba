"""Unit tests for profile_stats types. No implementation required."""
from __future__ import annotations

import pytest
from profile_stats.types import (
    ConfigOverrides,
    ContributionStats,
    LanguageEntry,
    ProfileStatsData,
    WrappedMetrics,
)


def test_language_entry_construction() -> None:
    entry = LanguageEntry(name="Go", percent=27.05, color="#00ADD8")
    assert entry.name == "Go"
    assert entry.percent == 27.05
    assert entry.color == "#00ADD8"


def test_wrapped_metrics_construction() -> None:
    w = WrappedMetrics(
        universal_rank="Top 15%",
        longest_streak_days=12,
        most_active_month="October",
        most_active_day="Thursday",
        top_language="Go",
        power_level="Pro Mode",
    )
    assert w.longest_streak_days == 12
    assert w.top_language == "Go"


def test_profile_stats_data_construction() -> None:
    data = ProfileStatsData(
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
    assert data.contribution.past_year == 848
    assert len(data.languages) == 2
    assert data.wrapped.power_level == "Pro Mode"


def test_config_overrides_defaults() -> None:
    c = ConfigOverrides()
    assert c.universal_rank is None
    assert c.power_level is None
