"""Two donuts: share of adults vs. share of wealth for the same groups."""

import math
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path

import matplotlib.pyplot as plt
import polars as pl
from matplotlib.axes import Axes

from wid.data import cum_share_at
from wid.style import INK, INK_SECONDARY, LABEL_FONTSIZE, SOURCE_NOTE, SURFACE

# Group edges as "richest x%", from everyone down to the very top.
GROUP_EDGES: tuple[float, ...] = (100.0, 50.0, 10.0, 1.0, 0.1, 0.01, 0.001, 0.0)
GROUP_NAMES: tuple[str, ...] = (
    "Bottom 50%",
    "Middle 40%",
    "Top 10–1%",
    "Top 1–0.1%",
    "Top 0.1–0.01%",
    "Top 0.01–0.001%",
    "Top 0.001%",
)
# Categorical palette slots 1-7 in their validated order, assigned richest
# first so wedge neighbours (including the wrap-around pair top 0.001% /
# bottom 50%) pass the colour-blind separation checks.
GROUP_COLORS: tuple[str, ...] = (
    "#4a3aa7",  # Bottom 50%: violet
    "#008300",  # Middle 40%: green
    "#e87ba4",  # Top 10–1%: magenta
    "#eda100",  # Top 1–0.1%: yellow
    "#1baf7a",  # Top 0.1–0.01%: aqua
    "#eb6834",  # Top 0.01–0.001%: orange
    "#2a78d6",  # Top 0.001%: blue
)
# Wedges run clockwise from 12 o'clock, richest first.
DONUT_START_ANGLE = 90.0
DONUT_RING_WIDTH = 0.38
DONUT_LABEL_RADIUS = 1.3
DONUT_STUB_RADIUS = 1.1
DONUT_AXIS_HALF_WIDTH = 2.3
DONUT_LABEL_MIN_GAP = 0.27  # data units (radius = 1)
DONUT_LABEL_Y_MAX = 1.62
DONUT_Y_HALF_HEIGHT = 1.78


@dataclass(frozen=True)
class Group:
    name: str
    color: str
    population_pct: float
    wealth_pct: float


def build_groups(df: pl.DataFrame) -> list[Group]:
    """Population and wealth share (%) per group, poorest group first."""
    cum = [cum_share_at(df, edge) for edge in GROUP_EDGES]
    return [
        Group(name, color, upper - lower, cum_hi - cum_lo)
        for name, color, (upper, lower), (cum_hi, cum_lo) in zip(
            GROUP_NAMES, GROUP_COLORS, pairwise(GROUP_EDGES), pairwise(cum), strict=True
        )
    ]


def spread_labels(ys: list[float], min_gap: float, y_max: float) -> list[float]:
    """Place labels near their natural heights, at least `min_gap` apart.

    Overlapping labels merge into a cluster centred on their mean natural height;
    clusters are clamped to [-y_max, y_max].
    """

    def place(cluster: list[int]) -> list[float]:
        centre = sum(ys[i] for i in cluster) / len(cluster)
        half = (len(cluster) - 1) / 2 * min_gap
        top = min(max(centre + half, -y_max + 2 * half), y_max)
        return [top - k * min_gap for k in range(len(cluster))]

    clusters: list[list[int]] = []
    for i in sorted(range(len(ys)), key=lambda i: ys[i], reverse=True):
        clusters.append([i])
        while (
            len(clusters) > 1
            and place(clusters[-2])[-1] - place(clusters[-1])[0] < min_gap
        ):
            below = clusters.pop()
            clusters[-1] += below

    out = list(ys)
    for cluster in clusters:
        for i, y in zip(cluster, place(cluster), strict=True):
            out[i] = y
    return out


def plot_donut(
    ax: Axes,
    groups: list[Group],
    values: list[float],
    value_labels: list[str],
    centre: str,
) -> None:
    # Richest first, clockwise from 12 o'clock, so both donuts share the layout.
    richest_first = list(range(len(groups)))[::-1]
    wedges, *_ = ax.pie(
        [values[i] for i in richest_first],
        colors=[groups[i].color for i in richest_first],
        startangle=DONUT_START_ANGLE,
        counterclock=False,
        wedgeprops={"width": DONUT_RING_WIDTH, "edgecolor": SURFACE, "linewidth": 1.5},
    )
    ax.text(0, 0, centre, ha="center", va="center", fontsize=13, color=INK_SECONDARY)

    # Spread labels per side so thin neighbouring wedges do not stack their text.
    mids = [math.radians((w.theta1 + w.theta2) / 2) for w in wedges]
    on_right = [math.cos(m) >= 0 for m in mids]
    label_y = [DONUT_LABEL_RADIUS * math.sin(m) for m in mids]
    for side in (True, False):
        idx = [i for i, r in enumerate(on_right) if r == side]
        spread = spread_labels(
            [label_y[i] for i in idx], DONUT_LABEL_MIN_GAP, DONUT_LABEL_Y_MAX
        )
        for i, y in zip(idx, spread, strict=True):
            label_y[i] = y

    for wedge_i, group_i in enumerate(richest_first):
        mid, right, y = mids[wedge_i], on_right[wedge_i], label_y[wedge_i]
        sign = 1.0 if right else -1.0
        # Leader: a short radial stub out of the wedge, a diagonal to the
        # label's height, then a short horizontal run into the text.
        ax.plot(
            [
                math.cos(mid),
                DONUT_STUB_RADIUS * math.cos(mid),
                sign * (DONUT_LABEL_RADIUS - 0.14),
                sign * (DONUT_LABEL_RADIUS - 0.04),
            ],
            [math.sin(mid), DONUT_STUB_RADIUS * math.sin(mid), y, y],
            color=INK_SECONDARY,
            linewidth=0.6,
        )
        ax.text(
            sign * DONUT_LABEL_RADIUS,
            y,
            f"{groups[group_i].name}\n{value_labels[group_i]}",
            ha="left" if right else "right",
            va="center",
            fontsize=LABEL_FONTSIZE,
            color=INK,
        )
    ax.set_xlim(-DONUT_AXIS_HALF_WIDTH, DONUT_AXIS_HALF_WIDTH)
    ax.set_ylim(-DONUT_Y_HALF_HEIGHT, DONUT_Y_HALF_HEIGHT)
    ax.set_aspect("equal")


def plot_donuts(df: pl.DataFrame, year: int, out_path: Path) -> None:
    groups = build_groups(df)
    fig, (ax_pop, ax_wealth) = plt.subplots(1, 2, figsize=(13, 6), facecolor=SURFACE)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.88, bottom=0.08, wspace=0.0)

    plot_donut(
        ax_pop,
        groups,
        [g.population_pct for g in groups],
        [f"{g.population_pct:g}%" for g in groups],
        "Share of\nadults",
    )
    plot_donut(
        ax_wealth,
        groups,
        [g.wealth_pct for g in groups],
        [f"{g.wealth_pct:.1f}%" for g in groups],
        "Share of\nwealth",
    )

    fig.suptitle(
        f"Germany {year}: who owns the wealth", color=INK_SECONDARY, fontsize=15
    )
    fig.text(
        0.99,
        0.02,
        f"{SOURCE_NOTE}\nThe top 1% of adults are slivers too thin to see in the left donut.",
        fontsize=8,
        ha="right",
        va="bottom",
        multialignment="right",
        color=INK_SECONDARY,
    )
    fig.savefig(out_path, dpi=200, facecolor=SURFACE, bbox_inches="tight")
    print(f"Saved {out_path}")
