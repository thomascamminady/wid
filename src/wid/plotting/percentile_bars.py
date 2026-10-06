"""Bar charts of average net wealth across adults ranked from poorest to richest.

Bar widths are population shares and heights are average wealth, so a bar's area
is the wealth it holds. `plot_percentile_bars` shows the 100 percentiles;
`plot_percentile_bars_zoom` adds a second panel zooming into the top 1%.
"""

from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import polars as pl
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter, MultipleLocator

from wid.plotting.bar_of_donut import DONUT_GROUPS, TOP_PARTS
from wid.plotting.style import GRID, INK_SECONDARY, LABEL_FONTSIZE, SOURCE_NOTE, SURFACE


@dataclass(frozen=True)
class BarGroup:
    """A labelled run of bars from `x0` to `x1` (percent of adults, poorest first)."""

    name: str
    x0: float
    x1: float
    color: str


ALL_ADULTS_GROUPS: tuple[BarGroup, ...] = tuple(
    BarGroup(spec.name, 100 - spec.upper, 100 - spec.lower, spec.color)
    for spec in DONUT_GROUPS
)
# Inside the top 1%: the purple shades of the bar-of-donut chart, lightest first.
TOP_PERCENT_GROUPS: tuple[BarGroup, ...] = (
    BarGroup("Top 1–0.1%", 99.0, 99.9, TOP_PARTS[0].color),
    BarGroup("Top 0.1–0.01%", 99.9, 99.99, TOP_PARTS[1].color),
    BarGroup("Top 0.01%", 99.99, 100.0, TOP_PARTS[-1].color),
)

# Groups narrower than this fraction of the x range get a right-aligned label
# ending at the group's right edge, so it does not run off the chart.
CENTRED_LABEL_MIN_FRACTION = 0.2
NARROW_LABEL_INSET = 0.006  # fraction of the x range; keeps text off the next bar
LABEL_LIFT = 0.04  # fraction of the y range between a group's tallest bar and label
Y_HEADROOM = 1.25  # y range = tallest bar * this, room for the top label


def format_eur(value: float, _pos: int | None = None) -> str:
    if abs(value) >= 1e6:
        return f"€{value / 1e6:g}M"
    if abs(value) >= 1e3:
        return f"€{value / 1e3:g}k"
    return f"€{value:g}"


def group_of(groups: tuple[BarGroup, ...], x: float) -> BarGroup:
    for group in groups:
        if group.x0 <= x < group.x1:
            return group
    raise ValueError(f"no group contains {x}")


def draw_bars(
    ax: Axes,
    bars: pl.DataFrame,
    groups: tuple[BarGroup, ...],
    tick_step: float,
    xlabel: str,
) -> None:
    """Bars from `bars` (columns lo, hi, avg_eur, share), one share label per group."""
    lo, hi = bars["lo"].to_list(), bars["hi"].to_list()
    avg, share = bars["avg_eur"].to_list(), bars["share"].to_list()
    x_min, x_max = min(lo), max(hi)
    x_range = x_max - x_min

    ax.set_facecolor(SURFACE)
    ax.bar(
        lo,
        avg,
        width=[h - lo_ for lo_, h in zip(lo, hi, strict=True)],
        align="edge",
        color=[group_of(groups, x).color for x in lo],
        edgecolor=SURFACE,
        linewidth=0.5,
        zorder=3,
    )
    ax.axhline(0, color=INK_SECONDARY, linewidth=0.8, zorder=4)

    y_top = max(avg) * Y_HEADROOM
    lift = LABEL_LIFT * y_top
    # One label per group with the share of all wealth the whole group holds.
    for group in groups:
        idx = [i for i, x in enumerate(lo) if group.x0 <= x < group.x1]
        y = max(max(avg[i] for i in idx), 0.0) + lift
        wide = (group.x1 - group.x0) / x_range >= CENTRED_LABEL_MIN_FRACTION
        if len(idx) > 1:
            # Bracket over the group's bars.
            pad = 0.003 * x_range
            ax.plot([group.x0 + pad, group.x1 - pad], [y, y], color=group.color, lw=1.2)
        ax.text(
            (group.x0 + group.x1) / 2
            if wide
            else group.x1 - NARROW_LABEL_INSET * x_range,
            y + lift / 2,
            f"{group.name}\n{sum(share[i] for i in idx):.1%} of all wealth",
            ha="center" if wide else "right",
            va="bottom",
            fontsize=LABEL_FONTSIZE,
            color=group.color,
        )

    ax.set_xlim(x_min, x_max)
    ax.set_ylim(top=y_top)
    ax.xaxis.set_major_locator(MultipleLocator(tick_step))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}%"))
    ax.yaxis.set_major_formatter(FuncFormatter(format_eur))
    ax.set_xlabel(xlabel, color=INK_SECONDARY)
    ax.set_ylabel("Average net wealth per adult", color=INK_SECONDARY)

    ax.grid(True, axis="y", color=GRID, linewidth=0.8, zorder=0)
    ax.tick_params(colors=INK_SECONDARY, length=0, pad=8)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)


def draw_all_adults(ax: Axes, df_pct: pl.DataFrame) -> None:
    draw_bars(
        ax,
        df_pct.rename({"pct_lo": "lo", "pct_hi": "hi"}),
        ALL_ADULTS_GROUPS,
        tick_step=10,
        xlabel="All adults, sorted from poorest (left) to richest (right). "
        "Each bar is 1% of adults.",
    )


def save(fig: Figure, out_path: Path) -> None:
    fig.text(
        0.99,
        0.005,
        SOURCE_NOTE,
        fontsize=8,
        ha="right",
        va="bottom",
        color=INK_SECONDARY,
    )
    fig.savefig(out_path, dpi=200, facecolor=SURFACE, bbox_inches="tight")
    print(f"Saved {out_path}")


def plot_percentile_bars(df_pct: pl.DataFrame, year: int, out_path: Path) -> None:
    """`df_pct` as returned by `wid.io.wealth_by_percentile`."""
    fig, ax = plt.subplots(figsize=(10, 4.8), facecolor=SURFACE)
    draw_all_adults(ax, df_pct)
    ax.set_title(
        f"Germany {year}: average wealth in each percentile",
        color=INK_SECONDARY,
        fontsize=16,
        pad=12,
    )
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    save(fig, out_path)


def plot_percentile_bars_zoom(
    df_pct: pl.DataFrame, df_top: pl.DataFrame, year: int, out_path: Path
) -> None:
    """The percentile chart, plus a panel zooming into its top-1% bar.

    `df_top` as returned by `wid.io.wealth_in_top_percent`.
    """
    fig, (ax_all, ax_top) = plt.subplots(2, 1, figsize=(10, 9.4), facecolor=SURFACE)
    draw_all_adults(ax_all, df_pct)
    draw_bars(
        ax_top,
        df_top,
        TOP_PERCENT_GROUPS,
        tick_step=0.1,
        xlabel="The richest 1% of adults. Bars are 0.1% of adults wide up to 99.9%, "
        "then 0.01%.",
    )
    fig.suptitle(
        f"Germany {year}: average wealth in each percentile",
        color=INK_SECONDARY,
        fontsize=16,
    )
    ax_top.set_title(
        "Zoom into the top 1%",
        color=INK_SECONDARY,
        fontsize=12,
        pad=10,
    )
    fig.tight_layout(rect=(0, 0.02, 1, 1), h_pad=3)
    save(fig, out_path)
