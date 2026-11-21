"""GitHub data fetcher: API + optional config merge."""
from __future__ import annotations

import json
import os
import urllib.request
from datetime import date, datetime, timedelta, timezone
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
_RANK_TIERS: list[tuple[int, str]] = [
    (1000, "Top 1%"),
    (500, "Top 5%"),
    (250, "Top 10%"),
    (100, "Top 15%"),
    (50, "Top 25%"),
    (10, "Top 50%"),
    (1, "Top 75%"),
]

_POWER_TIERS: list[tuple[int, str]] = [
    (80, "Legendary"),
    (55, "Pro Mode"),
    (30, "Grinder"),
    (10, "Rising Star"),
    (0, "Newcomer"),
]


def _compute_rank(total_contributions: int) -> str:
    for threshold, label in _RANK_TIERS:
        if total_contributions >= threshold:
            return label
    return "Unranked"


def _compute_power_level(
    total_contributions: int,
    longest_streak: int,
    language_count: int,
) -> str:
    """Weighted score from contributions, streak, and language breadth."""
    contrib_score = min(total_contributions / 50, 40)
    streak_score = min(longest_streak / 1.5, 30)
    lang_score = min(language_count * 3, 30)
    score = contrib_score + streak_score + lang_score
    for threshold, label in _POWER_TIERS:
        if score >= threshold:
            return label
    return "Newcomer"
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
        body = json.loads(resp.read().decode("utf-8"))
    if body.get("errors"):
        raise RuntimeError(f"GitHub GraphQL error: {body['errors']}")
    return body


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


_YEARS_QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection { contributionYears }
  }
}
"""

# One query per calendar year. GitHub limits a contributionsCollection range
# to one year, and calendar years match the yearly totals on the profile page.
_YEAR_QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
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


def _user(data: dict[str, Any], username: str) -> dict[str, Any]:
    user = (data.get("data") or {}).get("user")
    if not user:
        raise RuntimeError(f"GitHub user not found: {username}")
    return user


def _compute_wrapped_from_days(days: dict[str, int]) -> tuple[int, str, str]:
    """From {YYYY-MM-DD: count} compute longest_streak_days, most_active_month, most_active_day."""
    if not days:
        return 0, "—", "—"

    # Longest streak: most consecutive calendar dates with a count above zero.
    longest_streak = 0
    current_streak = 0
    previous: Optional[date] = None
    for date_str in sorted(days):
        current = date.fromisoformat(date_str)
        if days[date_str] <= 0:
            current_streak = 0
        elif previous is not None and current_streak and current - previous == timedelta(days=1):
            current_streak += 1
        else:
            current_streak = 1
        longest_streak = max(longest_streak, current_streak)
        previous = current

    # Most active month: the single month (for example "July 2026") with the most contributions.
    month_totals: dict[str, int] = {}
    for date_str, count in days.items():
        month_totals[date_str[:7]] = month_totals.get(date_str[:7], 0) + count
    best_month_key = max(month_totals, key=lambda k: month_totals[k])
    if month_totals[best_month_key] > 0:
        year, month = int(best_month_key[:4]), int(best_month_key[5:7])
        most_active_month = f"{MONTH_NAMES[month - 1]} {year}"
    else:
        most_active_month = "—"

    # Most active day of week, summed over all years (Monday=0 .. Sunday=6).
    weekday_totals = [0] * 7
    for date_str, count in days.items():
        weekday_totals[date.fromisoformat(date_str).weekday()] += count
    if max(weekday_totals) > 0:
        most_active_day = WEEKDAYS[max(range(7), key=lambda i: weekday_totals[i])]
    else:
        most_active_day = "—"

    return longest_streak, most_active_month, most_active_day


def _fetch_contributions(token: str, username: str) -> tuple[int, int, dict[str, int]]:
    """Return (past_year, all_time_total, {YYYY-MM-DD: count} for every day since the first year).

    Raises on any API error, so a failed run never writes a partial total.
    """
    years_data = _graphql(token, _YEARS_QUERY, {"login": username})
    years = _user(years_data, username)["contributionsCollection"]["contributionYears"]

    total = 0
    days: dict[str, int] = {}
    for year in sorted(years):
        data = _graphql(
            token,
            _YEAR_QUERY,
            {"login": username, "from": f"{year}-01-01T00:00:00Z", "to": f"{year}-12-31T23:59:59Z"},
        )
        calendar = _user(data, username)["contributionsCollection"]["contributionCalendar"]
        total += int(calendar["totalContributions"])
        for week in calendar["weeks"]:
            for day in week["contributionDays"]:
                if day["date"].startswith(str(year)):
                    days[day["date"]] = int(day["contributionCount"])

    past_year_start = (datetime.now(timezone.utc).date() - timedelta(days=365)).isoformat()
    past_year = sum(count for d, count in days.items() if d > past_year_start)
    return past_year, total, days


def _fetch_languages(token: str, username: str) -> list[LanguageEntry]:
    """Aggregate languages by bytes of code across all of the user's own non-fork repos."""
    query = """
    query($login: String!, $after: String) {
      user(login: $login) {
        repositories(first: 100, after: $after, ownerAffiliations: OWNER, isFork: false) {
          pageInfo { hasNextPage endCursor }
          nodes {
            languages(first: 10, orderBy: { field: SIZE, direction: DESC }) {
              edges {
                size
                node { name color }
              }
            }
          }
        }
      }
    }
    """
    byte_totals: dict[str, int] = {}
    api_colors: dict[str, str] = {}
    after: Optional[str] = None
    while True:
        data = _graphql(token, query, {"login": username, "after": after})
        repos = _user(data, username)["repositories"]
        for repo in repos["nodes"] or []:
            for edge in (repo or {}).get("languages", {}).get("edges") or []:
                size = int(edge.get("size") or 0)
                node = edge.get("node") or {}
                name = node.get("name")
                if not name or size <= 0:
                    continue
                byte_totals[name] = byte_totals.get(name, 0) + size
                color = node.get("color")
                if color and name not in api_colors:
                    api_colors[name] = color
        if not repos["pageInfo"]["hasNextPage"]:
            break
        after = repos["pageInfo"]["endCursor"]
    total_bytes = sum(byte_totals.values())
    if total_bytes == 0:
        return []
    raw_entries = [
        LanguageEntry(
            name=name,
            percent=round(100.0 * nbytes / total_bytes, 2),
            color=api_colors.get(name, LANGUAGE_COLORS.get(name, FALLBACK_COLOR)),
        )
        for name, nbytes in sorted(byte_totals.items(), key=lambda x: -x[1])
    ]
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
        days: dict[str, int] = {}
        if token and username:
            past_year, total, days = _fetch_contributions(token, username)
            languages = _fetch_languages(token, username)
        if overrides.past_year_contributions is not None:
            past_year = overrides.past_year_contributions
        if overrides.total_contributions is not None:
            total = overrides.total_contributions
        contribution = ContributionStats(past_year=past_year, total=total)
        top_lang = (languages[0].name if languages else "N/A")

        computed_streak, computed_month, computed_day = _compute_wrapped_from_days(days)
        longest_streak = (
            overrides.longest_streak_days
            if overrides.longest_streak_days is not None
            else computed_streak
        )
        wrapped = WrappedMetrics(
            universal_rank=overrides.universal_rank or _compute_rank(total),
            longest_streak_days=longest_streak,
            most_active_month=overrides.most_active_month or computed_month,
            most_active_day=overrides.most_active_day or computed_day,
            top_language=overrides.top_language or top_lang,
            power_level=overrides.power_level or _compute_power_level(
                total, longest_streak, len(languages),
            ),
        )
        return ProfileStatsData(
            contribution=contribution,
            languages=languages,
            wrapped=wrapped,
        )
