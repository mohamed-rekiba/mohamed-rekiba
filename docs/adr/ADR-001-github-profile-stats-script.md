# ADR-001: GitHub profile stats SVG generator

**Status**: Accepted  
**Date**: 2026-02-18

## Context

The GitHub profile README displays two static SVGs: one for contribution stats and language distribution, and one for "GitHub Wrapped" metrics. Keeping them up to date manually is error-prone. We need a single, automatable way to regenerate both files from live data (and optional config) so that the existing workflow can run weekly and commit updated SVGs.

## Options

| Option | Pros | Cons |
|--------|------|------|
| A: Python script + GitHub API + config | Single source of truth for API data; config for rank/power level; easy to run in CI. | Requires token in CI; some metrics (rank, power level) not from API. |
| B: Config-only script (no API) | No token; full control over all values. | Data can go stale unless another process updates config. |
| C: Third-party service (e.g. github-readme-stats) | No custom code. | Less control over layout; dependency on external service; may not match current SVG design. |

## Decision

We will implement **Option A**: a Python script that fetches contribution and language data from the GitHub API, merges with an optional config file for non-API metrics (e.g. universal rank, power level), and generates both SVGs via templates and programmatic donut generation. The script will be the single entrypoint; the existing GitHub Actions workflow will run it and commit updated SVGs when changed.

## Consequences

- **Gain**: Profile stats stay in sync with GitHub; one command to regenerate both SVGs; CI automation without manual edits.
- **Accept**: Token must be available in CI (e.g. `GITHUB_TOKEN`); "fun" metrics (rank, power level) come from config or defaults.
- **Risk**: API rate limits or changes could break fetches; mitigations: use GraphQL for efficiency, validate response shape, degrade gracefully (clear error or config-only path).

## Threat model (lightweight)

- **What we protect**: Token (never logged or written); integrity of generated SVGs (no injection from config/API).
- **Who might attack**: Compromised config, malicious API response, or dependency.
- **How**: Injecting script tags or event handlers into SVG; leaking token in logs or error messages.
- **Mitigations**: Validate and escape all interpolated values into SVG (text/attributes only; no raw HTML); read token from env only; no secrets in repo or workflow file.
