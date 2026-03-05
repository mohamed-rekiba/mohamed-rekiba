#!/usr/bin/env python3
"""Generate GitHub profile stats SVGs (contributions + language, wrapped metrics).

Reads GITHUB_TOKEN or GH_TOKEN from the environment for API access. Optional
config YAML can override rank, power level, and other metrics.

Usage:
  python scripts/generate_github_profile_stats.py [--config PATH] [--output-dir DIR] [USERNAME]

Defaults: output-dir=images, username from GITHUB_ACTOR or a fallback.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Allow running from repo root with PYTHONPATH=scripts
sys.path.insert(0, str(Path(__file__).resolve().parent))
from profile_stats.contracts import render_all
from profile_stats.fetcher import GitHubDataFetcher
from profile_stats.renderer import SvgRendererImpl


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate mohamed-rekiba-github-stats.svg and mohamed-rekiba-github-wrapped-stats.svg",
    )
    parser.add_argument(
        "username",
        nargs="?",
        default=os.environ.get("GITHUB_ACTOR", "mohamed-rekiba"),
        help="GitHub username to fetch stats for",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to optional YAML config (overrides for rank, power_level, etc.)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("images"),
        help="Directory to write SVG files into (default: images)",
    )
    args = parser.parse_args()
    config_path = Path(args.config) if args.config else None
    if config_path is not None and not config_path.exists():
        print(f"Warning: config file not found: {config_path}", file=sys.stderr)
        config_path = None
    fetcher = GitHubDataFetcher()
    try:
        data = fetcher.fetch(args.username, config_path=config_path)
    except Exception as e:
        print(f"Error fetching data: {e}", file=sys.stderr)
        return 1
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    renderer = SvgRendererImpl()
    render_all(renderer, data, output_dir)
    print(f"Wrote {output_dir / 'mohamed-rekiba-github-stats.svg'} and {output_dir / 'mohamed-rekiba-github-wrapped-stats.svg'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
