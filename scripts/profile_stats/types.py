"""Data types for GitHub profile stats and wrapped metrics.

Used by the generator script and by tests. No implementation logic here.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class LanguageEntry:
    """A single language in the distribution (name, percentage, hex color)."""

    name: str
    percent: float
    color: str  # Hex e.g. "#00ADD8"


@dataclass
class WrappedMetrics:
    """Metrics for the 'GitHub Wrapped' SVG."""

    universal_rank: str
    longest_streak_days: int
    most_active_month: str
    most_active_day: str
    top_language: str
    power_level: str


@dataclass
class ContributionStats:
    """Contribution numbers for the stats SVG."""

    past_year: int
    total: int


@dataclass
class ProfileStatsData:
    """Aggregate data for both SVGs."""

    contribution: ContributionStats
    languages: List[LanguageEntry]
    wrapped: WrappedMetrics


@dataclass
class ConfigOverrides:
    """Optional overrides from config file (e.g. rank, power level)."""

    universal_rank: str | None = None
    power_level: str | None = None
    longest_streak_days: int | None = None
    most_active_month: str | None = None
    most_active_day: str | None = None
    top_language: str | None = None
    past_year_contributions: int | None = None
    total_contributions: int | None = None
