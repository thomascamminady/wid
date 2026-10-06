"""Data access: fetch from WID.world and load the tidy CSV."""

from wid.io.fetch import fetch_and_tidy, g_percentiles, tidy_gpercentiles
from wid.io.load import (
    DEFAULT_CSV,
    cum_share_at,
    load_cumulative,
    load_gpercentiles,
    wealth_by_percentile,
    wealth_in_top_percent,
)

__all__ = [
    "DEFAULT_CSV",
    "cum_share_at",
    "fetch_and_tidy",
    "g_percentiles",
    "load_cumulative",
    "load_gpercentiles",
    "tidy_gpercentiles",
    "wealth_by_percentile",
    "wealth_in_top_percent",
]
