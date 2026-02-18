"""SVG renderer implementation for profile stats and wrapped metrics."""
from __future__ import annotations

import math
from pathlib import Path
from xml.sax.saxutils import escape

from .contracts import SvgRenderer
from .types import LanguageEntry, ProfileStatsData


def _escape_svg_text(raw: str) -> str:
    """Escape text for safe use inside SVG (no script injection)."""
    return escape(raw, {"'": "&#39;"})


def _donut_segment_paths(
    radius: float, entries: list[LanguageEntry]
) -> list[tuple[str, str]]:
    """Generate SVG path 'd' for each segment (pie slice from center). Returns (color, d)."""
    if not entries:
        return []
    total = sum(e.percent for e in entries)
    if total <= 0:
        return []
    cx = cy = radius
    paths: list[tuple[str, str]] = []
    start_angle = -90  # Start from top (12 o'clock)
    for entry in entries:
        ratio = entry.percent / total
        sweep = ratio * 360
        end_angle = start_angle + sweep
        start_rad = math.radians(start_angle)
        end_rad = math.radians(end_angle)
        x1 = cx + radius * math.cos(start_rad)
        y1 = cy + radius * math.sin(start_rad)
        x2 = cx + radius * math.cos(end_rad)
        y2 = cy + radius * math.sin(end_rad)
        large = 1 if sweep > 180 else 0
        d = f"M {cx},{cy} L {x1:.4f},{y1:.4f} A {radius} {radius} 0 {large} 1 {x2:.4f},{y2:.4f} Z"
        paths.append((entry.color, d))
        start_angle = end_angle
    return paths


class SvgRendererImpl(SvgRenderer):
    """Renders both profile stats and wrapped SVGs to disk."""

    def render_wrapped(self, data: ProfileStatsData, output_path: Path) -> None:
        w = data.wrapped
        rank = _escape_svg_text(w.universal_rank)
        streak = _escape_svg_text(f"{w.longest_streak_days} days")
        month = _escape_svg_text(w.most_active_month)
        day = _escape_svg_text(w.most_active_day)
        lang = _escape_svg_text(w.top_language)
        power = _escape_svg_text(w.power_level)
        svg = f"""<svg width="449" height="280" viewBox="0 0 449 280" xmlns="http://www.w3.org/2000/svg" lang="en" xml:lang="en">
<rect x="2" y="2" width="445" height="276" rx="6" stroke-width="4" stroke="rgba(56,139,253,0.4)" fill="#0d1117"/>
<text x="22" y="42" fill="#58a6ff" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="20" font-weight="700">GitHub Wrapped Metrics</text>
<text x="22" y="74" fill="#8b949e" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="14" font-weight="600">Universal Rank</text>
<text x="427" y="74" fill="#c9d1d9" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="14" font-weight="700" text-anchor="end">{rank}</text>
<text x="22" y="104" fill="#8b949e" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="14" font-weight="600">Longest Streak</text>
<text x="427" y="104" fill="#c9d1d9" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="14" font-weight="700" text-anchor="end">{streak}</text>
<text x="22" y="134" fill="#8b949e" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="14" font-weight="600">Most Active Month</text>
<text x="427" y="134" fill="#c9d1d9" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="14" font-weight="700" text-anchor="end">{month}</text>
<text x="22" y="164" fill="#8b949e" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="14" font-weight="600">Most Active Day</text>
<text x="427" y="164" fill="#c9d1d9" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="14" font-weight="700" text-anchor="end">{day}</text>
<text x="22" y="194" fill="#8b949e" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="14" font-weight="600">Top Language</text>
<text x="427" y="194" fill="#c9d1d9" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="14" font-weight="700" text-anchor="end">{lang}</text>
<text x="22" y="224" fill="#8b949e" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="14" font-weight="600">Power Level</text>
<text x="427" y="224" fill="#c9d1d9" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="14" font-weight="700" text-anchor="end">{power}</text>
</svg>
"""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(svg, encoding="utf-8")

    def render_stats(self, data: ProfileStatsData, output_path: Path) -> None:
        # past_year kept in data for future use; only Total shown in UI
        total = data.contribution.total
        paths_with_colors = _donut_segment_paths(91.0, data.languages)
        donut_paths = "\n".join(
            f'<path fill-rule="evenodd" fill="{color}" d="{d}"/>'
            for color, d in paths_with_colors
        )
        legend_rows: list[str] = []
        row_height = 21
        for i, entry in enumerate(data.languages):
            y = 21 + i * row_height
            name_esc = _escape_svg_text(entry.name)
            pct = f"{entry.percent:.2f}%"
            legend_rows.append(
                f'<g transform="translate(15, {y})">\n'
                f'<rect x="0.5" y="0.5" rx="2" width="15" height="15" fill="{entry.color}" stroke-width="1" stroke="#ffffff"/>\n'
                f'<text transform="scale(0.095)" x="263" y="132" lengthAdjust="spacingAndGlyphs">{name_esc} {pct}</text>\n'
                f"</g>"
            )
        legend_block = "\n".join(legend_rows)
        legend_height = 21 + len(data.languages) * row_height
        total_height = max(398, 84 + 21 + legend_height + 20)
        svg = f"""<svg width="449" height="{total_height}" viewBox="0 0 449 {total_height}" xmlns="http://www.w3.org/2000/svg" lang="en" xml:lang="en">
<rect x="2" y="2" stroke-width="4" rx="6" width="445" height="{total_height - 4}" stroke="rgba(56,139,253,0.4)" fill="#0d1117"/>
<g font-weight="600" font-size="110pt" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" text-rendering="geometricPrecision">
<g transform="translate(0, 21)" fill="#c9d1d9">
<g transform="translate(15, 0)"><g transform="scale(0.095)">
<text x="0" y="132" textLength="1115" lengthAdjust="spacingAndGlyphs">Contributions</text>
<text x="3537" y="132" textLength="418" lengthAdjust="spacingAndGlyphs">Total</text>
</g></g>
<g transform="translate(15, 21)">
<path fill="#1f6feb" fill-rule="evenodd" d="M2.5 1.75a.25.25 0 01.25-.25h10.5a.25.25 0 01.25.25v10.5a.25.25 0 01-.25.25H2.75a.25.25 0 01-.25-.25V1.75zM2.75 0A1.75 1.75 0 001 1.75v10.5c0 .966.784 1.75 1.75 1.75h10.5A1.75 1.75 0 0015 12.25V1.75A1.75 1.75 0 0013.25 0H2.75zm8.03 6.28a.75.75 0 00-1.06-1.06L6.75 8.19l-1.97-1.97a.75.75 0 00-1.06 1.06l2.5 2.5a.75.75 0 001.06 0l3.5-3.5z"/>
<g transform="scale(0.095)">
<text lengthAdjust="spacingAndGlyphs" textLength="1589" x="263" y="132">Total Contributions</text>
<text lengthAdjust="spacingAndGlyphs" textLength="422" x="3537" y="132">{total}</text>
</g></g>
</g>
<g transform="translate(0, 84)" fill="#c9d1d9">
<g transform="translate(15, 0)"><g transform="scale(0.095)">
<text x="0" y="132" textLength="1829" lengthAdjust="spacingAndGlyphs">Language Distribution</text>
</g></g>
<g transform="translate(239, 21)"><circle cx="92" cy="92" r="92" fill="#ffffff"/></g>
<g transform="translate(240, 22)">
{donut_paths}
</g>
<g transform="translate(15, 21)">
{legend_block}
</g>
</g>
</g>
</svg>
"""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(svg, encoding="utf-8")
