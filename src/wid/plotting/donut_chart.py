"""Two donuts: share of adults vs. share of wealth for the same groups."""

import math
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import polars as pl
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from wid.io.load import cum_share_at
from wid.plotting.style import (
    INK_SECONDARY,
    LABEL_FONTSIZE,
    SOURCE_NOTE,
    SURFACE,
)

# Categorical palette slots, validated in wedge order (including the
# wrap-around pair at 12 o'clock) for colour-blind separation.
VIOLET = "#4a3aa7"
GREEN = "#008300"
MAGENTA = "#e87ba4"
YELLOW = "#eda100"
AQUA = "#1baf7a"
ORANGE = "#eb6834"
BLUE = "#2a78d6"


@dataclass(frozen=True)
class GroupSpec:
    """A population group as a band of "richest x%": from `upper` down to `lower`."""

    name: str
    upper: float
    lower: float
    color: str


# Poorest first. Shared groups keep the same colour in both charts.
DETAILED_GROUPS: tuple[GroupSpec, ...] = (
    GroupSpec("Bottom 50%", 100.0, 50.0, VIOLET),
    GroupSpec("Middle 40%", 50.0, 10.0, GREEN),
    GroupSpec("Top 10–1%", 10.0, 1.0, MAGENTA),
    GroupSpec("Top 1–0.1%", 1.0, 0.1, YELLOW),
    GroupSpec("Top 0.1–0.01%", 0.1, 0.01, AQUA),
    GroupSpec("Top 0.01–0.001%", 0.01, 0.001, ORANGE),
    GroupSpec("Top 0.001%", 0.001, 0.0, BLUE),
)

# Wedges run clockwise, richest first. The adults donut starts at 12 o'clock;
# the wealth donut is rotated so this group sits where it does in the adults one.
DONUT_START_ANGLE = 90.0
ALIGN_GROUP = "Middle 40%"
DONUT_RING_WIDTH = 0.38
DONUT_LABEL_RADIUS = 1.3
DONUT_STUB_RADIUS = 1.1
DONUT_AXIS_HALF_WIDTH = 1.9  # labels may run past it
DONUT_LABEL_LINE_HEIGHT = 0.135  # data units (radius = 1) per text line
DONUT_LABEL_PADDING = 0.01
DONUT_LABEL_Y_MAX = 1.62
DONUT_Y_LIMITS: tuple[float, float] = (-1.78, 1.78)


@dataclass(frozen=True)
class Group:
    name: str
    color: str
    population_pct: float
    wealth_pct: float


def build_groups(df: pl.DataFrame, specs: tuple[GroupSpec, ...]) -> list[Group]:
    """Population and wealth share (%) per group, poorest group first."""
    return [
        Group(
            spec.name,
            spec.color,
            spec.upper - spec.lower,
            cum_share_at(df, spec.upper) - cum_share_at(df, spec.lower),
        )
        for spec in specs
    ]


def spread_labels(ys: list[float], min_gap: float, y_max: float) -> list[float]:
    """Place labels near their natural heights, at least `min_gap` apart.

    Overlapping labels merge into a cluster centred on their mean natural height;
    clusters are clamped to [-y_max, y_max]. The top-to-bottom order of the
    natural heights is kept, so leader lines on one side do not cross.
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


def mid_angle(values: list[float], index: int, start_angle: float) -> float:
    """Mid-angle (degrees) of wedge `index` when drawn richest-first, clockwise."""
    richer = sum(values[index + 1 :])  # values are poorest first
    return start_angle - 360.0 * (richer + values[index] / 2) / sum(values)


def aligned_start_angle(
    values: list[float], reference: list[float], index: int
) -> float:
    """Start angle that puts wedge `index` where it sits in the `reference` donut."""
    target = mid_angle(reference, index, DONUT_START_ANGLE)
    return target - mid_angle(values, index, 0.0)


def draw_ring(
    ax: Axes,
    groups: list[Group],
    values: list[float],
    start_angle: float = DONUT_START_ANGLE,
) -> list[float]:
    """Draw the ring richest-first, clockwise; return wedge mid-angles (radians)."""
    wedges, *_ = ax.pie(
        values[::-1],
        colors=[g.color for g in groups[::-1]],
        startangle=start_angle,
        counterclock=False,
        wedgeprops={
            "width": DONUT_RING_WIDTH,
            "edgecolor": SURFACE,
            "linewidth": 1.5,
        },
    )
    return [math.radians((w.theta1 + w.theta2) / 2) for w in wedges][::-1]


def plot_donut(
    ax: Axes,
    groups: list[Group],
    values: list[float],
    labels: list[str],
    centre: str,
    start_angle: float = DONUT_START_ANGLE,
    unlabelled: frozenset[str] = frozenset(),
    label_heights: dict[str, float] | None = None,
) -> list[float]:
    """Draw one donut with a leader-lined label per group (poorest group first).

    `label_heights` pins a group's label to a height (data units) instead of its
    wedge's. Returns the wedge mid-angles in radians.
    """
    mids = draw_ring(ax, groups, values, start_angle)
    ax.text(0, 0, centre, ha="center", va="center", fontsize=13, color=INK_SECONDARY)

    shown = [i for i, g in enumerate(groups) if g.name not in unlabelled]
    n_lines = max(labels[i].count("\n") + 1 for i in shown)
    min_gap = n_lines * DONUT_LABEL_LINE_HEIGHT + DONUT_LABEL_PADDING

    # Spread labels per side so thin neighbouring wedges do not stack their text.
    on_right = {i: math.cos(mids[i]) >= 0 for i in shown}
    label_y = {i: DONUT_LABEL_RADIUS * math.sin(mids[i]) for i in shown}
    for i in shown:
        if label_heights and groups[i].name in label_heights:
            label_y[i] = label_heights[groups[i].name]
    for side in (True, False):
        idx = [i for i in shown if on_right[i] == side]
        spread = spread_labels([label_y[i] for i in idx], min_gap, DONUT_LABEL_Y_MAX)
        label_y.update(zip(idx, spread, strict=True))

    for i in shown:
        mid, y = mids[i], label_y[i]
        sign = 1.0 if on_right[i] else -1.0
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
            labels[i],
            ha="left" if on_right[i] else "right",
            va="center",
            fontsize=LABEL_FONTSIZE,
            color=groups[i].color,  # label in its slice's colour
        )
    ax.set_xlim(-DONUT_AXIS_HALF_WIDTH, DONUT_AXIS_HALF_WIDTH)
    ax.set_ylim(*DONUT_Y_LIMITS)
    ax.set_aspect("equal", adjustable="box")  # pie() switches to "datalim"
    return mids


def plot_wealth_donut(ax: Axes, groups: list[Group]) -> None:
    """Wealth donut, rotated so ALIGN_GROUP lines up with the adults donut."""
    wealth = [g.wealth_pct for g in groups]
    align = [g.name for g in groups].index(ALIGN_GROUP)
    plot_donut(
        ax,
        groups,
        wealth,
        [f"{g.name}\n{g.wealth_pct:.1f}%" for g in groups],
        "Share of\nwealth",
        start_angle=aligned_start_angle(
            wealth, [g.population_pct for g in groups], align
        ),
    )


def finish_figure(fig: Figure, year: int, out_path: Path) -> None:
    fig.suptitle(
        f"Germany {year}: who owns the wealth", color=INK_SECONDARY, fontsize=20
    )
    fig.text(
        0.99,
        0.02,
        SOURCE_NOTE,
        fontsize=8,
        ha="right",
        va="bottom",
        multialignment="right",
        color=INK_SECONDARY,
    )
    fig.savefig(out_path, dpi=200, facecolor=SURFACE, bbox_inches="tight")
    print(f"Saved {out_path}")


def plot_donuts(df: pl.DataFrame, year: int, out_path: Path) -> None:
    groups = build_groups(df, DETAILED_GROUPS)
    fig, (ax_pop, ax_wealth) = plt.subplots(1, 2, figsize=(11, 5.6), facecolor=SURFACE)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.88, bottom=0.08, wspace=0.0)

    # Group names already state the share of adults, so no second line.
    plot_donut(
        ax_pop,
        groups,
        [g.population_pct for g in groups],
        [g.name for g in groups],
        "Share of\nadults",
    )
    plot_wealth_donut(ax_wealth, groups)
    finish_figure(fig, year, out_path)
