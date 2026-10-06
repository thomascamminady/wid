"""Bar charts of average net wealth across adults ranked from poorest to richest.

Bar widths are population shares and heights are average wealth, so a bar's area
is the wealth it holds. `plot_percentile_bars` shows the 100 percentiles;
`plot_percentile_bars_zoom` stacks zooms into the top 1% and the top 0.01%;
`plot_percentile_bars_staircase` draws the same zooms as a staircase, each
panel centred under the bar it enlarges and joined to it by zoom lines.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import matplotlib.pyplot as plt
import polars as pl
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.patches import ConnectionPatch, Rectangle
from matplotlib.ticker import FuncFormatter, MultipleLocator
from matplotlib.transforms import blended_transform_factory, offset_copy

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
# Inside the top 0.01%: WID's finest bins, 0.001% of adults each.
TOP_BASIS_POINT_GROUPS: tuple[BarGroup, ...] = (
    BarGroup("Top 0.01–0.001%", 99.99, 99.999, TOP_PARTS[2].color),
    BarGroup("Top 0.001%", 99.999, 100.0, TOP_PARTS[3].color),
)

# Groups narrower than this fraction of the x range get a right-aligned label
# ending at the group's right edge, so it does not run off the chart.
CENTRED_LABEL_MIN_FRACTION = 0.2
NARROW_LABEL_INSET = 0.006  # fraction of the x range; keeps text off the next bar
LABEL_LIFT = 0.04  # fraction of the y range between a group's tallest bar and label
Y_HEADROOM = 1.25  # y range = tallest bar * this, room for the top label

# Staircase layout (figure fractions): wide panels, each stepping right by a
# fixed amount. That keeps the next panel left of centre under the zoomed bar
# (which sits at the right edge), so the chart uses the width with little
# white space.
STAIRCASE_FIGSIZE: tuple[float, float] = (13.0, 14.0)
STAIRCASE_PANEL_WIDTH = 0.6
STAIRCASE_PANEL_HEIGHT = 0.22
STAIRCASE_LEFTS: tuple[float, ...] = (0.07, 0.22, 0.37)
STAIRCASE_BOTTOMS: tuple[float, ...] = (0.71, 0.395, 0.08)
# Zoom lines start from one point this far below the x axis (axes fraction),
# just under the "100%" tick label. Their label sits this far right of the
# right-hand line's midpoint (points).
ZOOM_LINE_START_Y = -0.12
ZOOM_LABEL_OFFSET = 8.0


def format_eur(value: float, _pos: int | None = None) -> str:
    if abs(value) >= 1e9:
        return f"€{value / 1e9:g}bn"
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
    xlabel_loc: Literal["left", "center", "right"] = "center",
    clip_at_zero: bool = False,
) -> None:
    """Bars from `bars` (columns lo, hi, avg_eur, share), one share label per group.

    `clip_at_zero` starts the y axis at €0, hiding the (small) negative bars.
    """
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
    ax.set_ylim(bottom=0.0 if clip_at_zero else None, top=y_top)
    ax.xaxis.set_major_locator(MultipleLocator(tick_step))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}%"))
    ax.yaxis.set_major_formatter(FuncFormatter(format_eur))
    ax.set_xlabel(xlabel, color=INK_SECONDARY, loc=xlabel_loc)
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
    df_pct: pl.DataFrame,
    df_top1: pl.DataFrame,
    df_top001: pl.DataFrame,
    year: int,
    out_path: Path,
) -> None:
    """The percentile chart, then zooms into its top 1% and into the top 0.01%.

    `df_top1` and `df_top001` as returned by `wid.io.wealth_in_top_percent` with
    `top_pct=1.0` and `top_pct=0.01`.
    """
    fig, (ax_all, ax_top1, ax_top001) = plt.subplots(
        3, 1, figsize=(10, 13.8), facecolor=SURFACE
    )
    draw_all_adults(ax_all, df_pct)
    draw_bars(
        ax_top1,
        df_top1,
        TOP_PERCENT_GROUPS,
        tick_step=0.1,
        xlabel="The richest 1% of adults. Bars are 0.1% of adults wide up to 99.9%, "
        "then 0.01%.",
    )
    draw_bars(
        ax_top001,
        df_top001,
        TOP_BASIS_POINT_GROUPS,
        tick_step=0.001,
        xlabel="The richest 0.01% of adults. Each bar is 0.001% of adults.",
    )
    fig.suptitle(
        f"Germany {year}: average wealth in each percentile",
        color=INK_SECONDARY,
        fontsize=16,
    )
    for ax, title in (
        (ax_top1, "Zoom into the top 1%"),
        (ax_top001, "Zoom into the top 0.01%"),
    ):
        ax.set_title(title, color=INK_SECONDARY, fontsize=12, pad=10)
    fig.tight_layout(rect=(0, 0.015, 1, 1), h_pad=3)
    save(fig, out_path)


def link_zoom(
    fig: Figure,
    ax_from: Axes,
    ax_to: Axes,
    x0: float,
    x1: float,
    height: float,
    label: str,
) -> None:
    """Box the bar(s) x0..x1 in `ax_from` and draw zoom lines down to `ax_to`.

    Both lines start at one point just under the x axis of `ax_from` (below the
    "100%" tick label) and end at the top corners of `ax_to`, which spans
    exactly x0..x1.
    `label` is written next to the right-hand line.
    """
    ax_from.add_patch(
        Rectangle(
            (x0, 0.0),
            x1 - x0,
            height,
            fill=False,
            edgecolor=INK_SECONDARY,
            linewidth=0.8,
            zorder=5,
        )
    )
    # Both lines leave from one point under "100%" (the right edge, x1).
    below_axis = blended_transform_factory(ax_from.transData, ax_from.transAxes)
    start = (x1, ZOOM_LINE_START_Y)
    y_top = ax_to.get_ylim()[1]
    for x in (x0, x1):
        fig.add_artist(
            ConnectionPatch(
                xyA=start,
                coordsA=below_axis,
                xyB=(x, y_top),
                coordsB=ax_to.transData,
                color=INK_SECONDARY,
                linewidth=0.8,
            )
        )

    # Label just right of the right-hand line's midpoint, kept horizontal.
    start_px = below_axis.transform(start)
    end_px = ax_to.transData.transform((x1, y_top))
    mid = fig.transFigure.inverted().transform((start_px + end_px) / 2)
    fig.text(
        mid[0],
        mid[1],
        label,
        ha="left",
        va="center",
        fontsize=LABEL_FONTSIZE + 1,
        color=INK_SECONDARY,
        transform=offset_copy(
            fig.transFigure, fig=fig, x=ZOOM_LABEL_OFFSET, y=0.0, units="points"
        ),
    )


def plot_percentile_bars_staircase(
    df_pct: pl.DataFrame,
    df_top1: pl.DataFrame,
    df_top001: pl.DataFrame,
    year: int,
    out_path: Path,
) -> None:
    """The three panels of `plot_percentile_bars_zoom` as a staircase of zooms."""
    fig = plt.figure(figsize=STAIRCASE_FIGSIZE, facecolor=SURFACE)
    ax_all, ax_top1, ax_top001 = (
        fig.add_axes((left, bottom, STAIRCASE_PANEL_WIDTH, STAIRCASE_PANEL_HEIGHT))
        for left, bottom in zip(STAIRCASE_LEFTS, STAIRCASE_BOTTOMS, strict=True)
    )
    # x labels sit left so the zoom lines, which leave from under "100%" on the
    # right, never cross them.
    draw_bars(
        ax_all,
        df_pct.rename({"pct_lo": "lo", "pct_hi": "hi"}),
        ALL_ADULTS_GROUPS,
        tick_step=20,
        xlabel="All adults, sorted from poorest (left) to richest (right)",
        xlabel_loc="left",
        clip_at_zero=True,
    )
    draw_bars(
        ax_top1,
        df_top1,
        TOP_PERCENT_GROUPS,
        tick_step=0.2,
        xlabel="The richest 1% of adults",
        xlabel_loc="left",
    )
    draw_bars(
        ax_top001,
        df_top001,
        TOP_BASIS_POINT_GROUPS,
        tick_step=0.002,
        xlabel="The richest 0.01% of adults",
        xlabel_loc="left",
    )
    fig.suptitle(
        f"Germany {year}: average wealth in each percentile",
        color=INK_SECONDARY,
        fontsize=16,
        y=0.97,
    )
    link_zoom(
        fig,
        ax_all,
        ax_top1,
        99.0,
        100.0,
        df_pct["avg_eur"][-1],
        "Zoom into\nthe top 1%",
    )
    link_zoom(
        fig,
        ax_top1,
        ax_top001,
        99.99,
        100.0,
        df_top1["avg_eur"][-1],
        "Zoom into\nthe top 0.01%",
    )
    save(fig, out_path)
