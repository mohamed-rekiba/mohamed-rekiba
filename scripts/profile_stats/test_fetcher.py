"""Tests for data fetcher. Require concrete GitHubDataFetcher (Red until implemented)."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from profile_stats.fetcher import GitHubDataFetcher
from profile_stats.types import ProfileStatsData


def test_fetcher_returns_profile_stats_data() -> None:
    """Fetch returns ProfileStatsData with required fields."""
    fetcher = GitHubDataFetcher()
    # Use a known public user to avoid auth; or mock. For Red we just need the type.
    data = fetcher.fetch("octocat", config_path=None)
    assert isinstance(data, ProfileStatsData)
    assert data.contribution is not None
    assert data.wrapped is not None
    assert data.languages is not None


def test_fetcher_merges_config_overrides() -> None:
    """When config file is provided, overrides are applied to result."""
    fetcher = GitHubDataFetcher()
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("universal_rank: Top 10%\npower_level: Pro Mode\n")
        config_path = Path(f.name)
    try:
        data = fetcher.fetch("octocat", config_path=config_path)
        assert data.wrapped.universal_rank == "Top 10%"
        assert data.wrapped.power_level == "Pro Mode"
    finally:
        config_path.unlink()


def test_wrapped_streak_spans_year_boundary_and_breaks_on_gap() -> None:
    """Streak counts consecutive dates across years and resets on a zero day or a missing date."""
    from profile_stats.fetcher import _compute_wrapped_from_days

    days = {
        "2023-12-30": 1,
        "2023-12-31": 2,
        "2024-01-01": 3,  # 3-day streak across the year boundary
        "2024-01-02": 0,
        "2024-01-03": 5,
        "2024-01-05": 9,  # 2024-01-04 missing: not consecutive
    }
    streak, month, day = _compute_wrapped_from_days(days)
    assert streak == 3
    assert month == "January 2024"
    assert day == "Friday"  # 2024-01-05 has the largest count


def test_wrapped_with_no_days() -> None:
    from profile_stats.fetcher import _compute_wrapped_from_days

    assert _compute_wrapped_from_days({}) == (0, "—", "—")
