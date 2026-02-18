"""GitHub data fetcher: API + optional config merge."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from .contracts import DataFetcher
from .types import (
    ConfigOverrides,
    ContributionStats,
    LanguageEntry,
    ProfileStatsData,
    WrappedMetrics,
)

GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"
MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DEFAULT_RANK = "Top 15%"
DEFAULT_POWER = "Pro Mode"
LANGUAGE_COLORS: dict[str, str] = {
    "Go": "#00ADD8",
    "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6",
    "Python": "#3572A5",
    "CSS": "#563d7c",
    "HTML": "#e34c26",
    "Dart": "#00B4AB",
    "Haml": "#ece2a9",
    "PHP": "#4F5D95",
    "SCSS": "#c6538c",
    "Java": "#b07219",
    "C#": "#178600",
    "Makefile": "#427819",
    "Shell": "#89e051",
    "C++": "#f34b7d",
}
FALLBACK_COLOR = "#959da5"


def _get_token() -> Optional[str]:
    return os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")


def _graphql(token: str, query: str, variables: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    req = urllib.request.Request(
        GITHUB_GRAPHQL_URL,
        data=json.dumps({"query": query, "variables": variables or {}}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _load_config(config_path: Path) -> ConfigOverrides:
    try:
        import yaml
    except ImportError:
        return ConfigOverrides()
    if not config_path.exists():
        return ConfigOverrides()
    with open(config_path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    if not raw or not isinstance(raw, dict):
        return ConfigOverrides()
    return ConfigOverrides(
        universal_rank=raw.get("universal_rank"),
        power_level=raw.get("power_level"),
        longest_streak_days=raw.get("longest_streak_days"),
        most_active_month=raw.get("most_active_month"),
        most_active_day=raw.get("most_active_day"),
        top_language=raw.get("top_language"),
        past_year_contributions=raw.get("past_year_contributions"),
        total_contributions=raw.get("total_contributions"),
    )


# GitHub's contributionCalendar returns at most ~1 year of data per query.
# Chunk ranges into 365-day windows and sum to get true all-time total.
_DAYS_PER_CHUNK = 365

_CONTRIBUTIONS_QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    createdAt
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
  }
}
"""

_CONTRIBUTIONS_ONLY_QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar { totalContributions }
    }
  }
}
"""


def _compute_wrapped_from_calendar(weeks: list[Any]) -> tuple[int, str, str]:
    """From contributionCalendar.weeks compute longest_streak_days, most_active_month, most_active_day."""
    if not weeks:
        return 0, "—", "—"
    days: list[tuple[str, int]] = []
    for week in weeks:
        for day in week.get("contributionDays") or []:
            d = day.get("date")
            c = int(day.get("contributionCount") or 0)
            if d:
                days.append((d, c))
    days.sort(key=lambda x: x[0])
    if not days:
        return 0, "—", "—"

    # Longest streak: max consecutive days with contributionCount > 0
    longest_streak = 0
    current_streak = 0
    for _date, count in days:
        if count > 0:
            current_streak += 1
            longest_streak = max(longest_streak, current_streak)
        else:
            current_streak = 0

    # Most active month: aggregate by month (YYYY-MM), find max
    month_totals: dict[str, int] = {}
    for date_str, count in days:
        if len(date_str) >= 7:
            month_key = date_str[:7]
            month_totals[month_key] = month_totals.get(month_key, 0) + count
    if month_totals:
        best_month_key = max(month_totals, key=month_totals.get)
        try:
            y, m = int(best_month_key[:4]), int(best_month_key[5:7])
            most_active_month = MONTH_NAMES[m - 1] if 1 <= m <= 12 else "—"
        except (ValueError, IndexError):
            most_active_month = "—"
    else:
        most_active_month = "—"

    # Most active day of week: aggregate by weekday (Monday=0 .. Sunday=6)
    weekday_totals: list[int] = [0] * 7
    for date_str, count in days:
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            weekday_totals[dt.weekday()] += count
        except (ValueError, IndexError):
            continue
    if weekday_totals and max(weekday_totals) > 0:
        best_weekday_idx = max(range(7), key=lambda i: weekday_totals[i])
        most_active_day = WEEKDAYS[best_weekday_idx]
    else:
        most_active_day = "—"

    return longest_streak, most_active_month, most_active_day


def _fetch_contributions(token: str, username: str) -> tuple[int, int, list[Any]]:
    """Return (past_year, total, calendar_weeks). Past year = last 365 days; total = all-time (chunked)."""
    end = datetime.utcnow()
    to_str = end.strftime("%Y-%m-%dT23:59:59Z")
    start_past = end - timedelta(days=365)
    from_past_str = start_past.strftime("%Y-%m-%dT00:00:00Z")

    # Query 1: user createdAt + past year contributions + calendar weeks (for streak/month/day)
    try:
        data = _graphql(
            token,
            _CONTRIBUTIONS_QUERY,
            {"login": username, "from": from_past_str, "to": to_str},
        )
    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError):
        return 0, 0, []
    if not data:
        return 0, 0, []
    payload = data.get("data") or {}
    user = payload.get("user")
    if not user:
        return 0, 0, []
    collection = user.get("contributionsCollection") or {}
    cal = collection.get("contributionCalendar") or {}
    past_year = int(cal.get("totalContributions") or 0)
    weeks = cal.get("weeks") or []
    created_at = user.get("createdAt")
    if not created_at:
        return past_year, past_year, weeks

    # Total: chunk from createdAt to now in 365-day windows and sum (API returns at most ~1 year per query)
    try:
        created_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        if created_dt.tzinfo is not None:
            created_dt = created_dt.replace(tzinfo=None)  # work in naive UTC like end
    except (ValueError, TypeError):
        return past_year, past_year, weeks
    total = 0
    chunk_start = created_dt
    while chunk_start < end:
        chunk_end_dt = min(chunk_start + timedelta(days=_DAYS_PER_CHUNK), end)
        from_str = chunk_start.strftime("%Y-%m-%dT00:00:00Z")
        chunk_to_str = chunk_end_dt.strftime("%Y-%m-%dT23:59:59Z")
        try:
            data_chunk = _graphql(
                token,
                _CONTRIBUTIONS_ONLY_QUERY,
                {"login": username, "from": from_str, "to": chunk_to_str},
            )
        except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError):
            break
        if not data_chunk:
            break
        p = data_chunk.get("data") or {}
        u = p.get("user")
        if not u:
            break
        coll = u.get("contributionsCollection") or {}
        c = coll.get("contributionCalendar") or {}
        total += int(c.get("totalContributions") or 0)
        chunk_start = chunk_end_dt
        if chunk_start >= end:
            break

    return past_year, total if total > 0 else past_year, weeks


def _fetch_languages(token: str, username: str) -> list[LanguageEntry]:
    """Aggregate primary languages from user's repos."""
    query = """
    query($login: String!) {
      user(login: $login) {
        repositories(first: 100, ownerAffiliations: OWNER, orderBy: { field: PUSHED_AT, direction: DESC }) {
          nodes {
            primaryLanguage { name }
          }
        }
      }
    }
    """
    try:
        data = _graphql(token, query, {"login": username})
    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError):
        return []
    if not data:
        return []
    payload = data.get("data") or {}
    user = payload.get("user")
    if not user:
        return []
    repos = user.get("repositories") or {}
    nodes = repos.get("nodes") or []
    counts: dict[str, int] = {}
    for repo in nodes:
        if not repo:
            continue
        primary = repo.get("primaryLanguage") or {}
        lang = primary.get("name")
        if lang:
            counts[lang] = counts.get(lang, 0) + 1
    total = sum(counts.values())
    if total == 0:
        return []
    raw_entries = [
        LanguageEntry(
            name=name,
            percent=round(100.0 * n / total, 2),
            color=LANGUAGE_COLORS.get(name, FALLBACK_COLOR),
        )
        for name, n in sorted(counts.items(), key=lambda x: -x[1])
    ]
    # Group languages < 2% into "Other"
    main_entries = [e for e in raw_entries if e.percent >= 2.0]
    other_entries = [e for e in raw_entries if e.percent < 2.0]
    if not other_entries:
        return main_entries
    other_sum = round(sum(e.percent for e in other_entries), 2)
    if other_sum <= 0:
        return main_entries
    return main_entries + [LanguageEntry(name="Other", percent=other_sum, color=FALLBACK_COLOR)]


class GitHubDataFetcher(DataFetcher):
    """Fetches profile stats from GitHub API and merges optional config overrides."""

    def fetch(
        self,
        username: str,
        config_path: Optional[Path] = None,
    ) -> ProfileStatsData:
        overrides = _load_config(Path(config_path)) if config_path else ConfigOverrides()
        token = _get_token()
        past_year, total = 0, 0
        languages: list[LanguageEntry] = []
        calendar_weeks: list[Any] = []
        if token and username:
            past_year, total, calendar_weeks = _fetch_contributions(token, username)
            languages = _fetch_languages(token, username)
        if overrides.past_year_contributions is not None:
            past_year = overrides.past_year_contributions
        if overrides.total_contributions is not None:
            total = overrides.total_contributions
        contribution = ContributionStats(past_year=past_year, total=total)
        top_lang = (languages[0].name if languages else "N/A")

        computed_streak, computed_month, computed_day = _compute_wrapped_from_calendar(calendar_weeks)
        wrapped = WrappedMetrics(
            universal_rank=overrides.universal_rank or DEFAULT_RANK,
            longest_streak_days=(
                overrides.longest_streak_days
                if overrides.longest_streak_days is not None
                else computed_streak
            ),
            most_active_month=overrides.most_active_month or computed_month,
            most_active_day=overrides.most_active_day or computed_day,
            top_language=overrides.top_language or top_lang,
            power_level=overrides.power_level or DEFAULT_POWER,
        )
        return ProfileStatsData(
            contribution=contribution,
            languages=languages,
            wrapped=wrapped,
        )
