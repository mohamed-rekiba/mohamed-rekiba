#!/usr/bin/env python3
"""
Gets your all-time contribution count as of today from GitHub, then adds one new
row to stats/contribution_history.csv so you can track progress over time.
Creates the file and stats folder if they don't exist yet.

Run: python scripts/fetch_contributions.py
You'll need GITHUB_TOKEN set (e.g. run `gh auth login` or set it in CI).
"""

import csv
import json
import os
import ssl
import sys
from datetime import date, timedelta
from pathlib import Path
from urllib.request import Request, urlopen

LOGIN = "mohamed-rekiba"
REPO_ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = REPO_ROOT / "stats" / "contribution_history.csv"
HEADER = ("date", "day", "total_contributions")

CONTRIB_QUERY = """
  query($login: String!, $from: DateTime!, $to: DateTime!) {
    user(login: $login) {
      contributionsCollection(from: $from, to: $to) {
        contributionCalendar { totalContributions }
      }
    }
  }
"""


def day_after(d: date) -> str:
    """Turn a date into the ISO timestamp for the start of the *next* day (for API bounds)."""
    next_d = d + timedelta(days=1)
    return next_d.isoformat() + "T00:00:00Z"


def graphql(token: str, query: str, variables: dict) -> dict:
    """Send a GraphQL request to GitHub and return the data part of the response."""
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = Request(
        "https://api.github.com/graphql",
        data=body,
        method="POST",
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "mohamed-rekiba-contribution-fetch",
        },
    )
    ctx = ssl.create_default_context()
    with urlopen(req, context=ctx) as resp:
        data = json.loads(resp.read().decode())
    if data.get("errors"):
        raise RuntimeError(data["errors"])
    if "message" in data:
        raise RuntimeError(data["message"])
    return data.get("data", {})


def fetch_total_contributions_until(token: str, up_to_date: date) -> int:
    """
    Count contributions from the beginning of time (2010) through the given date.
    GitHub only lets us ask for one year at a time, so we slice into year-sized
    chunks and add up the totals.
    """
    start = date(2010, 1, 1)
    end = up_to_date + timedelta(days=1)  # so we include the whole of up_to_date
    total = 0
    window_start = start
    while window_start < end:
        window_end = min(window_start + timedelta(days=365), end)
        from_ts = window_start.isoformat() + "T00:00:00Z"
        to_ts = window_end.isoformat() + "T00:00:00Z"
        data = graphql(
            token,
            CONTRIB_QUERY,
            {"login": LOGIN, "from": from_ts, "to": to_ts},
        )
        cal = (
            data.get("user", {})
            .get("contributionsCollection", {})
            .get("contributionCalendar", {})
        )
        total += int(cal.get("totalContributions") or 0)
        window_start = window_end
    return total


def load_existing_rows() -> list[tuple[str, str, int]]:
    """Read the CSV and return all data rows as (date, day, total). Empty list if file is missing or empty."""
    if not CSV_PATH.is_file():
        return []
    rows = []
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        # Accept both the old column name (past_year_contributions) and the new one (total_contributions)
        for row in reader:
            date_str = row.get("date", "")
            day_str = row.get("day", "")
            total = row.get("total_contributions") or row.get("past_year_contributions") or "0"
            try:
                rows.append((date_str, day_str, int(total)))
            except ValueError:
                rows.append((date_str, day_str, 0))
    return rows


def main() -> None:
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        print("Set GITHUB_TOKEN or run: gh auth login", file=sys.stderr)
        sys.exit(1)

    run_date = date.today()
    date_str = run_date.isoformat()
    day_name = run_date.strftime("%a")

    existing = load_existing_rows()
    last_date = existing[-1][0] if existing else None

    if last_date == date_str:
        print(f"We already have an entry for {date_str}, so nothing to add.", file=sys.stderr)
        return

    total = fetch_total_contributions_until(token, run_date)
    new_row = (date_str, day_name, total)
    out_rows = existing + [new_row]

    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(HEADER)
        writer.writerows(out_rows)

    print(f"Added {date_str} ({day_name}): {total} total contributions → {CSV_PATH}", file=sys.stderr)


if __name__ == "__main__":
    main()
