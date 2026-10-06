"""Wealth donut with the top 1% as one slice, split up in a stacked bar beside it.

After matplotlib's "bar of pie" example: the top 1% slice faces the bar and two
connector lines run from its edges to the bar's top and bottom.
"""

import math
from pathlib import Path

import matplotlib.pyplot as plt
import polars as pl
from matplotlib.axes import Axes
from matplotlib.patches import ConnectionPatch

from wid.plotting.donut_chart import (
    BLUE,
    GREEN,
    MAGENTA,
    VIOLET,
    Group,
    GroupSpec,
    build_groups,
    finish_figure,
    plot_donut,
)
from wid.plotting.style import INK_SECONDARY, LABEL_FONTSIZE, SURFACE

TOP_NAME = "Top 1%"
# Ring colours, validated in wedge order (including the wrap-around pair top 1% /
# bottom 50%) for colour-blind separation.
DONUT_GROUPS: tuple[GroupSpec, ...] = (
    GroupSpec("Bottom 50%", 100.0, 50.0, MAGENTA),
    GroupSpec("Middle 40%", 50.0, 10.0, GREEN),
    GroupSpec("Top 10–1%", 10.0, 1.0, BLUE),
    GroupSpec(TOP_NAME, 1.0, 0.0, VIOLET),
)
# The top 1% split up in the bar (richest last): an ordinal purple ramp at the
# violet's hue (OKLCH h ≈ 284), darker = richer.
TOP_PARTS: tuple[GroupSpec, ...] = (
    GroupSpec("Top 1–0.1%", 1.0, 0.1, "#a2a2e8"),
    GroupSpec("Top 0.1–0.01%", 0.1, 0.01, "#7d78d7"),
    GroupSpec("Top 0.01–0.001%", 0.01, 0.001, "#5b50b9"),
    GroupSpec("Top 0.001%", 0.001, 0.0, "#3d2e8d"),
)

BAR_WIDTH = 0.2
BOTTOM_LABEL_HEIGHT = 1.45  # donut data units (radius = 1)
BAR_X_LIMITS: tuple[float, float] = (-0.25, 0.95)  # room for labels on the right
BAR_Y_MARGIN = 0.18  # fraction of the bar height left free above and below


def plot_bar(ax: Axes, parts: list[Group], total_pct: float) -> None:
    """Stack the parts bottom-up (richest on top) with labels to the right."""
    bottom = 0.0
    for part in parts:
        ax.bar(
            0,
            part.wealth_pct,
            BAR_WIDTH,
            bottom=bottom,
            color=part.color,
            edgecolor=SURFACE,
            linewidth=1.5,
        )
        ax.text(
            BAR_WIDTH / 2 + 0.06,
            bottom + part.wealth_pct / 2,
            f"{part.name}\n{part.wealth_pct:.1f}%",
            ha="left",
            va="center",
            fontsize=LABEL_FONTSIZE,
            color=part.color,
        )
        bottom += part.wealth_pct
    ax.text(
        0,
        total_pct * (1 + BAR_Y_MARGIN / 3),
        f"{TOP_NAME}\n{total_pct:.1f}%",
        ha="center",
        va="bottom",
        fontsize=LABEL_FONTSIZE + 1,
        color=VIOLET,
    )
    ax.set_xlim(*BAR_X_LIMITS)
    ax.set_ylim(-BAR_Y_MARGIN * total_pct, (1 + BAR_Y_MARGIN) * total_pct)
    ax.axis("off")


def connect_slice_to_bar(
    fig: plt.Figure,
    ax_donut: Axes,
    ax_bar: Axes,
    theta1: float,
    theta2: float,
    top: float,
) -> None:
    """Lines from the slice's two outer corners to the bar's top and bottom."""
    for theta, bar_y in ((theta2, top), (theta1, 0.0)):
        fig.add_artist(
            ConnectionPatch(
                xyA=(-BAR_WIDTH / 2, bar_y),
                coordsA=ax_bar.transData,
                xyB=(math.cos(theta), math.sin(theta)),
                coordsB=ax_donut.transData,
                color=INK_SECONDARY,
                linewidth=0.8,
            )
        )


def plot_bar_of_donut(df: pl.DataFrame, year: int, out_path: Path) -> None:
    groups = build_groups(df, DONUT_GROUPS)
    parts = build_groups(df, TOP_PARTS)
    wealth = [g.wealth_pct for g in groups]
    top = groups[-1]

    fig, (ax_donut, ax_bar) = plt.subplots(
        1, 2, figsize=(10, 5.6), facecolor=SURFACE, width_ratios=(2, 1)
    )
    fig.subplots_adjust(left=0.02, right=0.98, top=0.88, bottom=0.06, wspace=0.0)

    # Turn the donut so the top 1% slice (drawn first, clockwise) is centred
    # on 3 o'clock, facing the bar.
    half_slice = 180.0 * top.wealth_pct / sum(wealth)
    plot_donut(
        ax_donut,
        groups,
        wealth,
        [f"{g.name}\n{g.wealth_pct:.1f}%" for g in groups],
        "Share of\nwealth",
        start_angle=half_slice,
        unlabelled=frozenset({TOP_NAME}),  # labelled above the bar
        # The bottom 50% slice borders the top 1% slice; lift its label above
        # the upper connector line.
        label_heights={"Bottom 50%": BOTTOM_LABEL_HEIGHT},
    )
    plot_bar(ax_bar, parts, top.wealth_pct)
    connect_slice_to_bar(
        fig,
        ax_donut,
        ax_bar,
        math.radians(-half_slice),
        math.radians(half_slice),
        top.wealth_pct,
    )
    finish_figure(fig, year, out_path)
