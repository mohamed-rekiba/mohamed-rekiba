# GitHub profile stats guide

## Overview

The profile README shows two auto-generated SVG cards:

1. **GitHub stats** – Total contributions (past year and all-time) and a language distribution donut.
2. **GitHub Wrapped** – Fun metrics: rank, longest streak, most active month/day, top language, power level.

Both are produced by `scripts/generate_github_profile_stats.py` and updated by the GitHub Actions workflow (see `docs/ops/github-profile-stats.md`).

## What you can change

- **Automatically**: Nothing; the workflow updates the SVGs from GitHub data (and optional config).
- **Optional overrides**: Copy `stats/config.yaml.example` to `stats/config.yaml` and set any of:
  - `universal_rank`, `power_level`, `longest_streak_days`, `most_active_month`, `most_active_day`, `top_language`
  - `past_year_contributions`, `total_contributions`

Config values override API data when the script runs.

## Running the generator yourself

From the repo root:

```bash
export GITHUB_TOKEN=ghp_...   # or GH_TOKEN
pip install -r requirements.txt
PYTHONPATH=scripts python3 scripts/generate_github_profile_stats.py --output-dir images
```

Use `--config stats/config.yaml` to apply overrides. Use `--help` for all options.

## FAQ

**Why do the numbers not match my profile?**  
The script uses the GitHub API; the profile page may cache. After the workflow runs, the next time the README is viewed the new SVGs are shown.

**Can I add more metrics?**  
Yes, by extending the script and the SVG templates (and optionally the config schema). See `scripts/profile_stats/` for types and renderers.
