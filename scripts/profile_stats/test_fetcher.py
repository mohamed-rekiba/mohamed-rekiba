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
