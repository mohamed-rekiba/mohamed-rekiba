"""Contracts (interfaces) for profile stats generation.

Implementations: GitHub API fetcher, SVG renderers. No implementation bodies here.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from .types import ConfigOverrides, ProfileStatsData


class DataFetcher(ABC):
    """Fetches and computes profile stats (API + optional config merge)."""

    @abstractmethod
    def fetch(
        self,
        username: str,
        config_path: Optional[Path] = None,
    ) -> ProfileStatsData:
        """Fetch and merge data for the given username.

        If config_path is provided, read overrides and merge with API data.
        Returns merged ProfileStatsData for both SVGs.
        """
        ...


class SvgRenderer(ABC):
    """Renders one or both SVGs to the filesystem."""

    @abstractmethod
    def render_wrapped(self, data: ProfileStatsData, output_path: Path) -> None:
        """Write the wrapped metrics SVG to output_path."""
        ...

    @abstractmethod
    def render_stats(self, data: ProfileStatsData, output_path: Path) -> None:
        """Write the contribution + language stats SVG to output_path."""
        ...


def render_all(renderer: SvgRenderer, data: ProfileStatsData, output_dir: Path) -> None:
    """Convenience: render both SVGs into output_dir with fixed filenames."""
    output_dir = Path(output_dir)
    renderer.render_wrapped(
        data,
        output_dir / "mohamed-rekiba-github-wrapped-stats.svg",
    )
    renderer.render_stats(
        data,
        output_dir / "mohamed-rekiba-github-stats.svg",
    )
