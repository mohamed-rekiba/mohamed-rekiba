#!/usr/bin/env python3
"""
Builds the main stats card: contribution counts (past year and all-time) plus a
language pie chart. Writes the result to images/mohamed-rekiba-github-stats.svg.

Needs GITHUB_TOKEN. In CI, GITHUB_REPOSITORY is used to pick the user; locally
you can set GITHUB_LOGIN if it's not the default.
"""

import math
from pathlib import Path

from _github_api import get_login, get_token, graphql

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = REPO_ROOT / "images" / "mohamed-rekiba-github-stats.svg"

CONTRIB_QUERY = """
  query($login: String!, $from: DateTime!, $to: DateTime!) {
    user(login: $login) {
      contributionsCollection(from: $from, to: $to) {
        contributionCalendar { totalContributions }
      }
    }
  }
"""

LANG_QUERY = """
  query($login: String!, $cursor: String) {
    user(login: $login) {
      repositories(first: 100, ownerAffiliations: OWNER, after: $cursor) {
        pageInfo { hasNextPage endCursor }
        nodes {
          languages(first: 20) { edges { size node { name } } }
        }
      }
    }
  }
"""

COLORS = {
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
    "Other": "#959da5",
}


def lang_color(name: str) -> str:
    """Hex color for a language name in the pie chart; gray if unknown."""
    return COLORS.get(name, "#959da5")


def esc(s: str) -> str:
    """Escape text for safe use inside SVG (so it doesn't break the markup)."""
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def main() -> None:
    token = get_token()
    login = get_login()

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    past_year_start = now.replace(year=now.year - 1)
    now_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    past_iso = past_year_start.strftime("%Y-%m-%dT%H:%M:%SZ")

    past_res = graphql(
        token,
        CONTRIB_QUERY,
        {"login": login, "from": past_iso, "to": now_iso},
    )
    total_res = graphql(
        token,
        CONTRIB_QUERY,
        {"login": login, "from": "2010-01-01T00:00:00Z", "to": now_iso},
    )

    past_year = (
        past_res.get("user", {})
        .get("contributionsCollection", {})
        .get("contributionCalendar", {})
        .get("totalContributions")
        or 0
    )
    total = (
        total_res.get("user", {})
        .get("contributionsCollection", {})
        .get("contributionCalendar", {})
        .get("totalContributions")
        or 0
    )

    lang_bytes: dict[str, int] = {}
    cursor = None
    while True:
        variables = {"login": login, "cursor": cursor}
        r = graphql(token, LANG_QUERY, variables)
        repos = (r.get("user") or {}).get("repositories")
        if not repos:
            break
        for node in repos.get("nodes") or []:
            for e in (node.get("languages") or {}).get("edges") or []:
                name = (e.get("node") or {}).get("name")
                if name:
                    lang_bytes[name] = lang_bytes.get(name, 0) + (e.get("size") or 0)
        page_info = repos.get("pageInfo") or {}
        if not page_info.get("hasNextPage"):
            break
        cursor = page_info.get("endCursor")

    total_bytes = sum(lang_bytes.values()) or 1
    sorted_langs = sorted(lang_bytes.items(), key=lambda x: -x[1])
    min_pct = 0.01
    main_langs = [(n, b) for n, b in sorted_langs if (b / total_bytes) >= min_pct]
    other_bytes = sum(b for n, b in sorted_langs if (b / total_bytes) < min_pct)
    if other_bytes > 0:
        main_langs.append(("Other", other_bytes))
    lang_list = [(name, f"{(bytes_ / total_bytes * 100):.2f}") for name, bytes_ in main_langs]

    R, cx, cy = 91, 91, 91
    angle = 0.0
    paths = []
    for name, pct_str in lang_list:
        pct = float(pct_str) / 100.0
        slice_ = pct * 2 * math.pi
        x1 = cx + R * math.sin(angle)
        y1 = cy - R * math.cos(angle)
        angle += slice_
        x2 = cx + R * math.sin(angle)
        y2 = cy - R * math.cos(angle)
        large = 1 if slice_ > math.pi else 0
        paths.append(
            f'<path fill-rule="evenodd" fill="{lang_color(name)}" '
            f'd="M {cx},{cy} L {x1:.4f},{y1:.4f} A {R} {R} 0 {large} 1 {x2:.4f},{y2:.4f} Z"/>'
        )

    check_path = "M2.5 1.75a.25.25 0 01.25-.25h10.5a.25.25 0 01.25.25v10.5a.25.25 0 01-.25.25H2.75a.25.25 0 01-.25-.25V1.75zM2.75 0A1.75 1.75 0 001 1.75v10.5c0 .966.784 1.75 1.75 1.75h10.5A1.75 1.75 0 0015 12.25V1.75A1.75 1.75 0 0013.25 0H2.75zm8.03 6.28a.75.75 0 00-1.06-1.06L6.75 8.19l-1.97-1.97a.75.75 0 00-1.06 1.06l2.5 2.5a.75.75 0 001.06 0l3.5-3.5z"
    contrib_row = (
        f'<g transform="translate(15, 21)"><path fill="#1f6feb" fill-rule="evenodd" d="{check_path}"/>'
        f'<g transform="scale(0.095)"><text lengthAdjust="spacingAndGlyphs" textLength="1589" x="263" y="132">Total Contributions</text>'
        f'<text lengthAdjust="spacingAndGlyphs" textLength="319" x="2358" y="132">{past_year}</text>'
        f'<text lengthAdjust="spacingAndGlyphs" textLength="422" x="3537" y="132">{total}</text></g></g>'
    )

    left_col = (len(lang_list) + 1) // 2
    legend_rows = []
    for i in range(left_col):
        a = lang_list[i]
        b = lang_list[left_col + i] if left_col + i < len(lang_list) else None
        row = (
            f'<g transform="translate(15, {21 + i * 21})">'
            f'<rect x="0.5" y="0.5" rx="2" width="15" height="15" fill="{lang_color(a[0])}" stroke-width="1" stroke="#ffffff"/>'
            f'<text transform="scale(0.095)" x="263" y="132" lengthAdjust="spacingAndGlyphs">{esc(a[0])} {a[1]}%</text>'
        )
        if b:
            row += (
                f'<rect x="224.5" y="0.5" rx="2" width="15" height="15" fill="{lang_color(b[0])}" stroke-width="1" stroke="#ffffff"/>'
                f'<text transform="scale(0.095)" x="2621" y="132" lengthAdjust="spacingAndGlyphs">{esc(b[0])} {b[1]}%</text>'
            )
        row += "</g>"
        legend_rows.append(row)

    card_height = 398
    stats_svg = f'''<svg width="449" height="{card_height}" viewBox="0 0 449 {card_height}" xmlns="http://www.w3.org/2000/svg" lang="en" xml:lang="en">
<rect x="2" y="2" stroke-width="4" rx="6" width="445" height="{card_height - 4}" stroke="rgba(56,139,253,0.4)" fill="#0d1117"/>
<g font-weight="600" font-size="110pt" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" text-rendering="geometricPrecision">
<g transform="translate(0, 21)" fill="#c9d1d9">
<g transform="translate(15, 0)"><g transform="scale(0.095)"><text x="0" y="132" lengthAdjust="spacingAndGlyphs">Contributions</text><text x="2358" y="132" lengthAdjust="spacingAndGlyphs">Past Year</text><text x="3537" y="132" lengthAdjust="spacingAndGlyphs">Total</text></g></g>
{contrib_row}
</g>
<g transform="translate(0, 84)" fill="#c9d1d9">
<g transform="translate(15, 0)"><g transform="scale(0.095)"><text x="0" y="132" lengthAdjust="spacingAndGlyphs">Language Distribution</text></g></g>
<g transform="translate(239, 21)"><circle cx="92" cy="92" r="92" fill="#ffffff"/></g>
<g transform="translate(240, 22)">{"".join(paths)}</g>
{"".join(legend_rows)}
</g>
</g>
</svg>'''

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(stats_svg, encoding="utf-8")
    print(f"Saved {OUT_PATH}", flush=True)


if __name__ == "__main__":
    main()
