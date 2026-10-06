"""Log-x line chart of top wealth shares.

Blue: cumulative share held by the richest x%.
Red: share held by each decade band, e.g. the top 1% excluding the top 0.1%.
"""

from itertools import pairwise
from pathlib import Path

import matplotlib.pyplot as plt
import polars as pl
from matplotlib.axes import Axes
from matplotlib.ticker import FuncFormatter, NullLocator, PercentFormatter

from wid.io.load import cum_share_at
from wid.plotting.style import (
    BLUE,
    GRID,
    INK,
    INK_SECONDARY,
    LABEL_FONTSIZE,
    RED,
    SOURCE_NOTE,
    SURFACE,
)

ANNOTATE_TOP_PCT: tuple[float, ...] = (0.001, 0.01, 0.1, 1.0, 10.0, 50.0)
DECADE_EDGES: tuple[float, ...] = (100.0, 10.0, 1.0, 0.1, 0.01, 0.001)

# Band labels go below their step when there is room (share >= this, in %);
# otherwise they go above the blue curve with a dotted leader line.
BAND_LABEL_BELOW_MIN_PCT = 12.0
BAND_LABEL_LIFT_PCT = 16.0


def format_pct_tick(value: float, _pos: int) -> str:
    return f"{value:g}%"


def band_label(upper: float, lower: float) -> str:
    if upper == 100.0:
        return f"Bottom {100 - lower:g}%"
    return f"Top {upper:g}–{lower:g}%"


def add_footer(ax: Axes, text: str, y: float) -> None:
    ax.text(
        1,
        y,
        text,
        transform=ax.transAxes,
        fontsize=8,
        ha="right",
        va="top",
        multialignment="right",
        color=INK_SECONDARY,
    )


def plot_cumulative(ax: Axes, df: pl.DataFrame) -> None:
    ax.plot(
        df["top_pct"].to_list(),
        df["cum_share_pct"].to_list(),
        color=BLUE,
        linewidth=2,
        zorder=3,
        label="Richest x% (cumulative)",
    )
    for top in ANNOTATE_TOP_PCT:
        share = cum_share_at(df, top)
        ax.scatter(
            [top], [share], s=36, color=BLUE, edgecolor=SURFACE, linewidth=1.5, zorder=4
        )
        # The x axis is inverted, so the curve falls left to right and the
        # space above-right of each point is clear. The two richest points
        # sit among the red band leaders and the right edge, so their labels
        # go above-left instead.
        offset, ha = ((-4, 8), "right") if top <= 0.01 else ((6, 6), "left")
        ax.annotate(
            f"Top {top:g}%\n{share:.1f}%",
            xy=(top, share),
            xytext=offset,
            textcoords="offset points",
            ha=ha,
            va="bottom",
            fontsize=LABEL_FONTSIZE,
            color=BLUE,
        )


def plot_bands(ax: Axes, df: pl.DataFrame) -> None:
    cum = [cum_share_at(df, edge) for edge in DECADE_EDGES]
    bands = [hi - lo for hi, lo in pairwise(cum)]

    # stairs needs increasing edges, so feed both lists reversed.
    ax.stairs(
        bands[::-1],
        DECADE_EDGES[::-1],
        baseline=None,
        color=RED,
        linewidth=2,
        zorder=3,
        label="Decade band, e.g. top 1% excl. top 0.1%",
    )

    for upper, lower, band, cum_upper in zip(
        DECADE_EDGES[:-1], DECADE_EDGES[1:], bands, cum[:-1], strict=True
    ):
        text = f"{band_label(upper, lower)}\n{band:.1f}%"
        x_mid = (upper * lower) ** 0.5  # geometric centre on the log axis
        if lower == DECADE_EDGES[-1]:
            # Keep the last leader clear of the top 0.001% label at the edge.
            x_mid = upper * 10**-0.35

        if band >= BAND_LABEL_BELOW_MIN_PCT:
            ax.annotate(
                text,
                xy=(x_mid, band),
                xytext=(0, -6),
                textcoords="offset points",
                ha="center",
                va="top",
                fontsize=LABEL_FONTSIZE,
                color=RED,
            )
        else:
            ax.annotate(
                text,
                xy=(x_mid, band),
                xytext=(x_mid, cum_upper + BAND_LABEL_LIFT_PCT),
                textcoords="data",
                ha="center",
                va="bottom",
                fontsize=LABEL_FONTSIZE,
                color=RED,
                arrowprops={
                    "arrowstyle": "-",
                    "color": RED,
                    "linewidth": 0.8,
                    "linestyle": ":",
                    "shrinkA": 2,
                    "shrinkB": 0,
                },
            )


def plot_line_chart(df: pl.DataFrame, year: int, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(9, 5.5), facecolor=SURFACE)
    ax.set_facecolor(SURFACE)

    plot_cumulative(ax, df)
    plot_bands(ax, df)

    ax.set_xscale("log")
    ax.set_xlim(100, 0.001)  # inverted: richest on the right
    ax.xaxis.set_minor_locator(NullLocator())
    ax.set_ylim(0, 112)
    ax.set_yticks(range(0, 101, 20))
    ax.xaxis.set_major_formatter(FuncFormatter(format_pct_tick))
    ax.yaxis.set_major_formatter(PercentFormatter(decimals=0))

    ax.set_xlabel("Richest x% of adults (log scale)", color=INK_SECONDARY)
    ax.set_ylabel("Share of total net wealth held", color=INK_SECONDARY)
    ax.set_title(
        f"Germany {year}: wealth share of the richest adults",
        color=INK_SECONDARY,
        fontsize=15,
        pad=12,
    )
    ax.legend(loc="upper right", frameon=False, fontsize=LABEL_FONTSIZE, labelcolor=INK)
    add_footer(
        ax,
        f"{SOURCE_NOTE}\nThe blue curve peaks slightly above 100% because the "
        "poorest adults have negative net wealth.",
        y=-0.14,
    )

    ax.grid(True, which="major", color=GRID, linewidth=0.8)
    ax.tick_params(colors=INK_SECONDARY, length=0, pad=8)
    for spine in ax.spines.values():
        spine.set_visible(False)

    fig.tight_layout()
    fig.savefig(out_path, dpi=200, facecolor=SURFACE, bbox_inches="tight")
    print(f"Saved {out_path}")
