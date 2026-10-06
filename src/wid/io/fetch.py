"""Download WID wealth data for Germany and tidy it into g-percentile bins."""

from itertools import pairwise
from pathlib import Path

import polars as pl
from remotezip import RemoteZip

from wid.io.load import DEFAULT_CSV

WID_BULK_URL = "https://wid.world/bulk_download/wid_all_data.zip"
RAW_FILE_NAME = "WID_data_DE.csv"
DEFAULT_RAW_DIR = Path("data/raw")

# Net personal wealth, equal-split adults (20+): share, threshold, average.
VARIABLES: dict[str, str] = {
    "shwealj992": "share",
    "thwealj992": "threshold_eur",
    "ahwealj992": "avg_eur",
}


def g_percentiles() -> list[str]:
    """WID's 127 disjoint g-percentile bins: 1% steps, then finer at the top."""
    bins = [f"p{i}p{i + 1}" for i in range(99)]
    for step, start in ((0.1, 99.0), (0.01, 99.9), (0.001, 99.99)):
        edges = [round(start + k * step, 3) for k in range(10)]
        bins += [f"p{lo:g}p{hi:g}" for lo, hi in pairwise(edges)]
    bins.append("p99.999p100")
    return bins


def fetch_raw(raw_dir: Path = DEFAULT_RAW_DIR) -> Path:
    """Extract the Germany file from WID's ~880 MB bulk zip via HTTP range requests."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    with RemoteZip(WID_BULK_URL) as archive:
        archive.extract(RAW_FILE_NAME, path=raw_dir)
    return raw_dir / RAW_FILE_NAME


def tidy_gpercentiles(raw_csv: Path) -> pl.DataFrame:
    """One row per (year, g-percentile bin) with share, threshold and average."""
    bins = g_percentiles()
    return (
        pl.read_csv(raw_csv, separator=";", infer_schema_length=0)
        .filter(
            pl.col("variable").is_in(list(VARIABLES)), pl.col("percentile").is_in(bins)
        )
        .with_columns(
            pl.col("year").cast(pl.Int32),
            pl.col("value").cast(pl.Float64),
            lo=pl.col("percentile").str.extract(r"^p([\d.]+)p").cast(pl.Float64),
            hi=pl.col("percentile").str.extract(r"p([\d.]+)$").cast(pl.Float64),
        )
        .pivot(on="variable", index=["year", "percentile", "lo", "hi"], values="value")
        .rename(VARIABLES)
        .select("year", "percentile", "lo", "hi", "avg_eur", "share", "threshold_eur")
        .sort("year", "lo")
    )


def fetch_and_tidy(
    out_csv: Path = DEFAULT_CSV, raw_dir: Path = DEFAULT_RAW_DIR
) -> Path:
    raw_csv = fetch_raw(raw_dir)
    df = tidy_gpercentiles(raw_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df.write_csv(out_csv)
    print(f"Saved {out_csv} ({df.height} rows, {df['year'].n_unique()} years)")
    return out_csv
