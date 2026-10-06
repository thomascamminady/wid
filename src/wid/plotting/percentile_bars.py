"""Bar chart of average net wealth per percentile of adults."""

from pathlib import Path

import matplotlib.pyplot as plt
import polars as pl
from matplotlib.ticker import FuncFormatter, MultipleLocator

from wid.plotting.bar_of_donut import DONUT_GROUPS
from wid.plotting.style import (
    GRID,
    INK_SECONDARY,
    LABEL_FONTSIZE,
    SOURCE_NOTE,
    SURFACE,
)

# Groups spanning fewer percentiles than this get a right-aligned label ending at
# the group's right edge, so it does not run off the chart.
CENTRED_LABEL_MIN_WIDTH = 20
NARROW_LABEL_INSET = 0.6  # percentiles; keeps text off the neighbouring bar
LABEL_LIFT = 0.04  # fraction of the y range between a group's tallest bar and label


def group_color(pct_lo: int) -> str:
    """Colour of the wealth group that percentile [pct_lo, pct_lo + 1) belongs to."""
    for spec in DONUT_GROUPS:
        if 100 - spec.upper <= pct_lo < 100 - spec.lower:
            return spec.color
    raise ValueError(f"no group for percentile {pct_lo}")


def format_eur(value: float, _pos: int | None = None) -> str:
    if abs(value) >= 1e6:
        return f"€{value / 1e6:g}M"
    if abs(value) >= 1e3:
        return f"€{value / 1e3:g}k"
    return f"€{value:g}"


def plot_percentile_bars(df_pct: pl.DataFrame, year: int, out_path: Path) -> None:
    """`df_pct` as returned by `wid.io.wealth_by_percentile`."""
    pct = df_pct["pct_lo"].to_list()
    avg = df_pct["avg_eur"].to_list()
    share = df_pct["share"].to_list()

    fig, ax = plt.subplots(figsize=(10, 4.8), facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    ax.bar(
        [p + 0.5 for p in pct],
        avg,
        width=1.0,
        color=[group_color(p) for p in pct],
        edgecolor=SURFACE,
        linewidth=0.5,
        zorder=3,
    )
    ax.axhline(0, color=INK_SECONDARY, linewidth=0.8, zorder=4)

    y_top = max(avg) * 1.25  # room for the top-1% label
    lift = LABEL_LIFT * y_top
    # One label per group with the share of all wealth the whole group holds.
    for spec in DONUT_GROUPS:
        x0, x1 = 100 - spec.upper, 100 - spec.lower
        idx = [i for i, p in enumerate(pct) if x0 <= p < x1]
        group_share = sum(share[i] for i in idx)
        y = max(max(avg[i] for i in idx), 0.0) + lift
        text = f"{spec.name}\n{group_share:.1%} of all wealth"
        wide = x1 - x0 >= CENTRED_LABEL_MIN_WIDTH
        if x1 - x0 > 1:
            # Bracket over the group's bars.
            ax.plot([x0 + 0.3, x1 - 0.3], [y, y], color=spec.color, linewidth=1.2)
        ax.text(
            (x0 + x1) / 2 if wide else x1 - NARROW_LABEL_INSET,
            y + lift / 2,
            text,
            ha="center" if wide else "right",
            va="bottom",
            fontsize=LABEL_FONTSIZE,
            color=spec.color,
        )

    ax.set_xlim(0, 100)
    ax.xaxis.set_major_locator(MultipleLocator(10))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"p{v:g}"))
    ax.yaxis.set_major_formatter(FuncFormatter(format_eur))
    ax.set_ylim(top=y_top)
    ax.set_xlabel("Adults ranked by net wealth (percentile)", color=INK_SECONDARY)
    ax.set_ylabel("Average net wealth per adult", color=INK_SECONDARY)
    ax.set_title(
        f"Germany {year}: average wealth in each percentile",
        color=INK_SECONDARY,
        fontsize=16,
        pad=12,
    )

    ax.grid(True, axis="y", color=GRID, linewidth=0.8, zorder=0)
    ax.tick_params(colors=INK_SECONDARY, length=0, pad=8)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)

    ax.text(
        1,
        -0.2,
        f"{SOURCE_NOTE}\nThe top bar (p99–p100) merges WID's finer bins above p99.",
        transform=ax.transAxes,
        fontsize=8,
        ha="right",
        va="top",
        multialignment="right",
        color=INK_SECONDARY,
    )
    fig.tight_layout()
    fig.savefig(out_path, dpi=200, facecolor=SURFACE, bbox_inches="tight")
    print(f"Saved {out_path}")
