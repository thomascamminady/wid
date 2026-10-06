"""Command-line entry points (see [project.scripts] in pyproject.toml)."""

from pathlib import Path

import fire

from wid.io import (
    DEFAULT_ADULTS_CSV,
    DEFAULT_CSV,
    fetch_and_tidy,
    load_adults,
    load_cumulative,
    load_gpercentiles,
    wealth_by_percentile,
    wealth_in_top_percent,
)
from wid.io.fetch import DEFAULT_RAW_DIR
from wid.plotting import (
    plot_balance,
    plot_bar_of_donut,
    plot_donuts,
    plot_line_chart,
    plot_percentile_bars,
    plot_percentile_bars_staircase,
    plot_percentile_bars_zoom,
    plot_wealth_donut_shaded,
)

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


def plot_bar_donut(
    year: int = DEFAULT_YEAR,
    csv_path: str = str(DEFAULT_CSV),
    out_path: str = str(OUTPUT_DIR / "germany_wealth_bar_of_donut.png"),
) -> None:
    """Wealth donut with the top 1% as one slice, split up in a bar beside it."""
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    plot_bar_of_donut(load_cumulative(Path(csv_path), year), year, Path(out_path))


def plot_percentiles(
    year: int = DEFAULT_YEAR,
    csv_path: str = str(DEFAULT_CSV),
    out_path: str = str(OUTPUT_DIR / "germany_wealth_percentiles.png"),
) -> None:
    """Bar chart of average net wealth in each percentile of adults."""
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    plot_percentile_bars(
        wealth_by_percentile(Path(csv_path), year), year, Path(out_path)
    )


def plot_wealth_donut(
    year: int = DEFAULT_YEAR,
    csv_path: str = str(DEFAULT_CSV),
    out_path: str = str(OUTPUT_DIR / "germany_wealth_donut_shaded.png"),
) -> None:
    """Wealth donut with the top 1% arc split into purple shades."""
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    plot_wealth_donut_shaded(
        load_cumulative(Path(csv_path), year), year, Path(out_path)
    )


def plot_percentiles_zoom(
    year: int = DEFAULT_YEAR,
    csv_path: str = str(DEFAULT_CSV),
    out_path: str = str(OUTPUT_DIR / "germany_wealth_percentiles_zoom.png"),
) -> None:
    """Percentile chart with zooms into the top 1% and the top 0.01%."""
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    plot_percentile_bars_zoom(
        wealth_by_percentile(Path(csv_path), year),
        wealth_in_top_percent(Path(csv_path), year, step=0.01, top_pct=1.0),
        wealth_in_top_percent(Path(csv_path), year, step=0.001, top_pct=0.01),
        year,
        Path(out_path),
    )


def plot_percentiles_staircase(
    year: int = DEFAULT_YEAR,
    csv_path: str = str(DEFAULT_CSV),
    out_path: str = str(OUTPUT_DIR / "germany_wealth_percentiles_staircase.png"),
) -> None:
    """The percentile zooms as a staircase joined by zoom lines."""
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    plot_percentile_bars_staircase(
        wealth_by_percentile(Path(csv_path), year),
        wealth_in_top_percent(Path(csv_path), year, step=0.01, top_pct=1.0),
        wealth_in_top_percent(Path(csv_path), year, step=0.001, top_pct=0.01),
        year,
        Path(out_path),
    )


def plot_balance_scale(
    year: int = DEFAULT_YEAR,
    csv_path: str = str(DEFAULT_CSV),
    adults_csv: str = str(DEFAULT_ADULTS_CSV),
    out_path: str = str(OUTPUT_DIR / "germany_wealth_balance.png"),
) -> None:
    """Balance scale: the richest 0.001% against the poorest 50%."""
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    plot_balance(
        load_gpercentiles(Path(csv_path), year),
        load_adults(Path(adults_csv), year),
        year,
        Path(out_path),
    )


def fetch_data_main() -> None:
    fire.Fire(fetch_data)


def plot_line_main() -> None:
    fire.Fire(plot_line)


def plot_donut_main() -> None:
    fire.Fire(plot_donut)


def plot_bar_donut_main() -> None:
    fire.Fire(plot_bar_donut)


def plot_percentiles_main() -> None:
    fire.Fire(plot_percentiles)


def plot_wealth_donut_main() -> None:
    fire.Fire(plot_wealth_donut)


def plot_percentiles_zoom_main() -> None:
    fire.Fire(plot_percentiles_zoom)


def plot_percentiles_staircase_main() -> None:
    fire.Fire(plot_percentiles_staircase)


def plot_balance_main() -> None:
    fire.Fire(plot_balance_scale)
