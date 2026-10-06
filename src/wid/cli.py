"""Command-line entry points (see [project.scripts] in pyproject.toml)."""

from pathlib import Path

import fire

from wid.io import DEFAULT_CSV, fetch_and_tidy, load_cumulative
from wid.io.fetch import DEFAULT_RAW_DIR
from wid.plotting import plot_donuts, plot_donuts_zoom, plot_line_chart

DEFAULT_YEAR = 2024
OUTPUT_DIR = Path("output")


def fetch_data(
    out_csv: str = str(DEFAULT_CSV), raw_dir: str = str(DEFAULT_RAW_DIR)
) -> None:
    """Download Germany from the WID bulk zip and write the tidy g-percentile CSV."""
    fetch_and_tidy(Path(out_csv), Path(raw_dir))


def plot_line(
    year: int = DEFAULT_YEAR,
    csv_path: str = str(DEFAULT_CSV),
    out_path: str = str(OUTPUT_DIR / "germany_wealth_cumulative.png"),
) -> None:
    """Log-x chart of cumulative and decade-band top wealth shares."""
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    plot_line_chart(load_cumulative(Path(csv_path), year), year, Path(out_path))


def plot_donut(
    year: int = DEFAULT_YEAR,
    csv_path: str = str(DEFAULT_CSV),
    out_path: str = str(OUTPUT_DIR / "germany_wealth_donuts.png"),
) -> None:
    """Two donuts: share of adults vs. share of wealth per group."""
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    plot_donuts(load_cumulative(Path(csv_path), year), year, Path(out_path))


def plot_donut_zoom(
    year: int = DEFAULT_YEAR,
    csv_path: str = str(DEFAULT_CSV),
    out_path: str = str(OUTPUT_DIR / "germany_wealth_donuts_zoom.png"),
) -> None:
    """Donuts with the top 1% as one group and a zoom inset on its sliver."""
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    plot_donuts_zoom(load_cumulative(Path(csv_path), year), year, Path(out_path))


def fetch_data_main() -> None:
    fire.Fire(fetch_data)


def plot_line_main() -> None:
    fire.Fire(plot_line)


def plot_donut_main() -> None:
    fire.Fire(plot_donut)


def plot_donut_zoom_main() -> None:
    fire.Fire(plot_donut_zoom)
