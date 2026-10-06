"""Load the tidy g-percentile CSV and derive cumulative top shares."""

from pathlib import Path

import polars as pl

DEFAULT_CSV = Path("data/germany_wealth_gpercentiles_wid.csv")


def load_gpercentiles(
    csv_path: Path = DEFAULT_CSV, year: int | None = None
) -> pl.DataFrame:
    """One row per (year, g-percentile bin), optionally for a single year."""
    df = pl.read_csv(csv_path)
    return df if year is None else df.filter(pl.col("year") == year)


def load_cumulative(csv_path: Path = DEFAULT_CSV, year: int = 2024) -> pl.DataFrame:
    """Return top population fraction (%) vs. cumulative wealth share (%)."""
    return (
        load_gpercentiles(csv_path, year)
        .sort("lo", descending=True)
        .select(
            top_pct=(100.0 - pl.col("lo")).round(3),  # 100 - 99.9 != 0.1 in floats
            cum_share_pct=pl.col("share").cum_sum() * 100.0,
        )
    )


def cum_share_at(df: pl.DataFrame, top_pct: float) -> float:
    """Cumulative share (%) held by the richest `top_pct` percent."""
    if top_pct == 0.0:
        return 0.0
    return df.filter((pl.col("top_pct") - top_pct).abs() < 1e-9)["cum_share_pct"].item()
