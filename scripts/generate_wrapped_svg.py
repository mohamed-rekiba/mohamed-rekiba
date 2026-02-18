#!/usr/bin/env python3
"""
Builds the "wrapped" style card: rank, longest streak, most active month and day,
top language by repo count, and a simple power level. Writes to
images/mohamed-rekiba-github-wrapped-stats.svg.

Needs GITHUB_TOKEN. Login is taken from GITHUB_REPOSITORY in CI or GITHUB_LOGIN
when you run it locally.
"""

from datetime import datetime, timezone
from pathlib import Path

from _github_api import get_login, get_token, graphql, rest_list_repos_for_user

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = REPO_ROOT / "images" / "mohamed-rekiba-github-wrapped-stats.svg"

CONTRIB_QUERY = """
  query($login: String!, $from: DateTime!, $to: DateTime!) {
    user(login: $login) {
      contributionsCollection(from: $from, to: $to) {
        contributionCalendar {
          totalContributions
          weeks { contributionDays { date contributionCount weekday } }
        }
      }
    }
  }
"""

DAY_NAMES = [
    "Sunday", "Monday", "Tuesday", "Wednesday",
    "Thursday", "Friday", "Saturday",
]
MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

RANK_BANDS = [
    (1000, "Top 1%"), (500, "Top 5%"), (300, "Top 10%"), (200, "Top 15%"),
    (100, "Top 25%"), (50, "Top 50%"), (20, "Rising"), (0, "Getting started"),
]
POWER_BANDS = [
    (500, "Pro Mode"), (200, "Power User"), (100, "Active"),
    (30, "Regular"), (0, "Casual"),
]


def main() -> None:
    token = get_token()
    login = get_login()

    now = datetime.now(timezone.utc)
    from_dt = now.replace(year=now.year - 1)
    from_iso = from_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    to_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    contrib_res = graphql(
        token,
        CONTRIB_QUERY,
        {"login": login, "from": from_iso, "to": to_iso},
    )
    weeks = (
        (contrib_res.get("user") or {})
        .get("contributionsCollection", {})
        .get("contributionCalendar", {})
        .get("weeks")
        or []
    )
    days = []
    for w in weeks:
        days.extend(w.get("contributionDays") or [])

    longest_streak = 0
    current = 0
    by_month: dict[str, int] = {}
    by_weekday: dict[int, int] = {}
    for d in days:
        count = d.get("contributionCount") or 0
        if count > 0:
            current += 1
            longest_streak = max(longest_streak, current)
        else:
            current = 0
        month = (d.get("date") or "")[:7]
        if month:
            by_month[month] = by_month.get(month, 0) + count
        wd = (d.get("weekday") or 0) % 7
        by_weekday[wd] = by_weekday.get(wd, 0) + count

    top_month_key = ""
    if by_month:
        top_month_key = max(by_month, key=by_month.get)
    most_active_month = "—"
    if top_month_key:
        parts = top_month_key.split("-")
        if len(parts) >= 2:
            try:
                m = int(parts[1])
                if 1 <= m <= 12:
                    most_active_month = MONTH_NAMES[m - 1]
            except ValueError:
                pass

    top_weekday_key = None
    if by_weekday:
        top_weekday_key = max(by_weekday, key=by_weekday.get)
    most_active_day = "—"
    if top_weekday_key is not None:
        most_active_day = DAY_NAMES[int(top_weekday_key)]

    repos = rest_list_repos_for_user(token, login)
    lang_count: dict[str, int] = {}
    for r in repos:
        lang = r.get("language")
        if lang:
            lang_count[lang] = lang_count.get(lang, 0) + 1
    top_language = "—"
    if lang_count:
        top_language = max(lang_count, key=lang_count.get)

    total_contrib = (
        (contrib_res.get("user") or {})
        .get("contributionsCollection", {})
        .get("contributionCalendar", {})
        .get("totalContributions")
        or 0
    )
    universal_rank = "Getting started"
    for min_val, label in RANK_BANDS:
        if total_contrib >= min_val:
            universal_rank = label
            break
    power_level = "Casual"
    for min_val, label in POWER_BANDS:
        if total_contrib >= min_val:
            power_level = label
            break

    svg = f'''<svg width="449" height="280" viewBox="0 0 449 280" xmlns="http://www.w3.org/2000/svg" lang="en" xml:lang="en">
<rect x="2" y="2" width="445" height="276" rx="6" stroke-width="4" stroke="rgba(56,139,253,0.4)" fill="#0d1117"/>
<text x="22" y="42" fill="#58a6ff" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="20" font-weight="700">GitHub Wrapped Metrics</text>
<text x="22" y="74" fill="#8b949e" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="14" font-weight="600">Universal Rank</text>
<text x="427" y="74" fill="#c9d1d9" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="14" font-weight="700" text-anchor="end">{universal_rank}</text>
<text x="22" y="104" fill="#8b949e" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="14" font-weight="600">Longest Streak</text>
<text x="427" y="104" fill="#c9d1d9" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="14" font-weight="700" text-anchor="end">{longest_streak} days</text>
<text x="22" y="134" fill="#8b949e" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="14" font-weight="600">Most Active Month</text>
<text x="427" y="134" fill="#c9d1d9" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="14" font-weight="700" text-anchor="end">{most_active_month}</text>
<text x="22" y="164" fill="#8b949e" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="14" font-weight="600">Most Active Day</text>
<text x="427" y="164" fill="#c9d1d9" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="14" font-weight="700" text-anchor="end">{most_active_day}</text>
<text x="22" y="194" fill="#8b949e" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="14" font-weight="600">Top Language</text>
<text x="427" y="194" fill="#c9d1d9" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="14" font-weight="700" text-anchor="end">{top_language}</text>
<text x="22" y="224" fill="#8b949e" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="14" font-weight="600">Power Level</text>
<text x="427" y="224" fill="#c9d1d9" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="14" font-weight="700" text-anchor="end">{power_level}</text>
</svg>'''

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(svg, encoding="utf-8")
    print(f"Saved {OUT_PATH}", flush=True)


if __name__ == "__main__":
    main()
