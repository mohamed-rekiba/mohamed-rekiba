"""
Shared helpers for talking to GitHub: GraphQL and a bit of REST.
Used by the stats SVG scripts and the contribution history fetcher.
"""

import json
import os
import ssl
from urllib.request import Request, urlopen


def get_token() -> str:
    """Read the GitHub token from the environment; exit with a helpful message if it's missing."""
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        raise SystemExit("Set GITHUB_TOKEN or run: gh auth login")
    return token


def get_login() -> str:
    """Figure out the GitHub username: from repo context in CI, or env, or a default."""
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if repo:
        return repo.split("/")[0]
    return os.environ.get("GITHUB_LOGIN", "mohamed-rekiba")


def graphql(token: str, query: str, variables: dict) -> dict:
    """Run a GraphQL request against GitHub's API and return the data payload."""
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = Request(
        "https://api.github.com/graphql",
        data=body,
        method="POST",
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "mohamed-rekiba-github-stats",
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


def rest_list_repos_for_user(token: str, username: str, per_page: int = 100, sort: str = "pushed") -> list:
    """Fetch the user's public repos from the REST API (e.g. for language stats)."""
    url = f"https://api.github.com/users/{username}/repos?per_page={per_page}&sort={sort}"
    req = Request(url, method="GET", headers={
        "Authorization": f"bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "mohamed-rekiba-github-stats",
    })
    ctx = ssl.create_default_context()
    with urlopen(req, context=ctx) as resp:
        return json.loads(resp.read().decode())
