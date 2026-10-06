# wid

Wealth inequality in Germany at fine resolution, from the
[World Inequality Database](https://wid.world) (WID.world).

WID publishes 127 "g-percentile" bins of net personal wealth: 1% steps up to
p99, then 0.1%, 0.01% and 0.001% steps, down to the top 0.001% (about 700
adults). Each bin has its wealth share, its entry threshold and its average
wealth. The unit is equal-split adults aged 20+.

## Usage

```bash
make install     # uv sync
make hooks       # install pre-commit hooks (ruff, ty, nbstripout)
make data        # fetch WID_data_DE.csv from the bulk zip -> data/germany_wealth_gpercentiles_wid.csv
make plots       # all charts -> output/
make plot-donut YEAR=2018
make check       # all pre-commit hooks on all files
```

`notebooks/main.ipynb` loads the data with `wid.io` and draws the charts with
`wid.plotting`.

The commands are also available directly: `uv run fetch-data`, `uv run plot-line`,
`uv run plot-donut`, `uv run plot-bar-donut`, `uv run plot-percentiles`, `uv run plot-wealth-donut` (each takes `--year`, `--csv_path`, `--out_path`).

## Data

`data/germany_wealth_gpercentiles_wid.csv` has one row per year (1820–2024)
and g-percentile bin: `year, percentile, lo, hi, avg_eur, share, threshold_eur`.
The bins are disjoint, so the shares in a year add up to 1.

The top-tail values are modelled, not observed. They come from
Albers, Bartels & Schularick (2020), which combines surveys (PHF, SOEP) with rich
lists and a Pareto tail, scaled to the national accounts. Years after 2018 are
WID imputations.
