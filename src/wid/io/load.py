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


def wealth_by_percentile(
    csv_path: Path = DEFAULT_CSV, year: int = 2024
) -> pl.DataFrame:
    """Average wealth and wealth share per whole percentile of adults.

    The finer bins above p99 are merged into the single p99-p100 percentile.
    Within a percentile the bin widths add up to 1, so the width-weighted sum of
    the bin averages is the percentile's average.
    """
    return (
        load_gpercentiles(csv_path, year)
        .group_by(
            pct_lo=pl.col("lo").floor().cast(pl.Int32),
            pct_hi=pl.col("hi").ceil().cast(pl.Int32),
        )
        .agg(avg_eur=((pl.col("hi") - pl.col("lo")) * pl.col("avg_eur")).sum())
        .with_columns(share=pl.col("avg_eur") / pl.col("avg_eur").sum())
        .sort("pct_lo")
    )


def wealth_in_top_percent(
    csv_path: Path = DEFAULT_CSV, year: int = 2024, step: float = 0.01
) -> pl.DataFrame:
    """Average wealth and share of all wealth for bins inside the top 1% (p99-p100).

    WID bins are 0.1% wide up to p99.9, 0.01% up to p99.99 and 0.001% above.
    Bins narrower than `step` are merged into `step`-wide bins; wider bins stay
    as they are, since WID has no finer data there. Columns: lo, hi, avg_eur, share.
    """
    width = pl.col("hi") - pl.col("lo")
    narrow = width < step
    # round() before floor() so that e.g. 99.99 / 0.01 = 9998.9999... lands on 9999.
    merged_lo = ((pl.col("lo") / step).round(6).floor() * step).round(6)
    bins = load_gpercentiles(csv_path, year).with_columns(
        wealth=width * pl.col("avg_eur")
    )
    return (
        bins.filter(pl.col("lo") >= 99.0)
        .group_by(
            lo=pl.when(narrow).then(merged_lo).otherwise(pl.col("lo")),
            hi=pl.when(narrow)
            .then((merged_lo + step).round(6))
            .otherwise(pl.col("hi")),
        )
        .agg(pl.col("wealth").sum(), width=width.sum())
        .select(
            "lo",
            "hi",
            avg_eur=pl.col("wealth") / pl.col("width"),
            share=pl.col("wealth") / bins["wealth"].sum(),
        )
        .sort("lo")
    )
