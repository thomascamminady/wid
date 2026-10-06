"""Two donuts: share of adults vs. share of wealth for the same groups.

`plot_donuts` labels every group around the rings. `plot_donuts_zoom` labels the
top 1% of the adults donut through a chain of zoom panels instead: each panel is
10x closer than the last, because each decade band is 10x thinner.
"""

import math
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import polars as pl
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.patches import ConnectionPatch, Rectangle

from wid.io.load import cum_share_at
from wid.plotting.style import (
    INK,
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

# Zoom chain over the 12 o'clock region of the adults donut: one panel per
# "top x%" level. Each window spans 10% of x (in donut data units) to the left
# of 12 o'clock for context and 80% to the right, ending inside the next band.
ZOOM_LEVELS_PCT: tuple[float, ...] = (1.0, 0.1, 0.01)
ZOOM_WINDOW_WIDTH_PER_PCT = 0.1  # window width = this * level
ZOOM_WINDOW_LEFT = 0.2  # fraction of the window left of 12 o'clock
ZOOM_RING_FRACTION = 0.7  # fraction of the window height showing the ring
ZOOM_LABEL_INSIDE_MIN = 0.3  # bands narrower than this (window fraction) label above

# Figure layout for the zoom chart (figure fractions).
ZOOM_FIGSIZE: tuple[float, float] = (11.0, 8.6)
ZOOM_DONUT_BOXES: tuple[tuple[float, float, float, float], ...] = (
    (0.0, 0.02, 0.5, 0.62),
    (0.5, 0.02, 0.5, 0.62),
)
ZOOM_PANEL_LEFTS: tuple[float, ...] = (0.115, 0.4, 0.685)
ZOOM_PANEL_BOTTOM = 0.69
ZOOM_PANEL_SIZE: tuple[float, float] = (0.25, 0.2)


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
    clip: bool = False,
) -> list[float]:
    """Draw the ring richest-first, clockwise; return wedge mid-angles (radians).

    pie() draws unclipped wedges; pass `clip=True` when the axes is a zoomed view.
    """
    wedges, *_ = ax.pie(
        values[::-1],
        colors=[g.color for g in groups[::-1]],
        startangle=start_angle,
        counterclock=False,
        wedgeprops={
            "width": DONUT_RING_WIDTH,
            "edgecolor": SURFACE,
            "linewidth": 1.5,
            "clip_on": clip,
        },
    )
    return [math.radians((w.theta1 + w.theta2) / 2) for w in wedges][::-1]


def plot_donut(
    ax: Axes,
    groups: list[Group],
    values: list[float],
    labels: list[str],
    centre: str,
    unlabelled: frozenset[str] = frozenset(),
    start_angle: float = DONUT_START_ANGLE,
) -> None:
    """Draw one donut with a leader-lined label per group (poorest group first)."""
    mids = draw_ring(ax, groups, values, start_angle)
    ax.text(0, 0, centre, ha="center", va="center", fontsize=13, color=INK_SECONDARY)

    shown = [i for i, g in enumerate(groups) if g.name not in unlabelled]
    n_lines = max(labels[i].count("\n") + 1 for i in shown)
    min_gap = n_lines * DONUT_LABEL_LINE_HEIGHT + DONUT_LABEL_PADDING

    # Spread labels per side so thin neighbouring wedges do not stack their text.
    on_right = {i: math.cos(mids[i]) >= 0 for i in shown}
    label_y = {i: DONUT_LABEL_RADIUS * math.sin(mids[i]) for i in shown}
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
            color=INK,
        )
    ax.set_xlim(-DONUT_AXIS_HALF_WIDTH, DONUT_AXIS_HALF_WIDTH)
    ax.set_ylim(*DONUT_Y_LIMITS)
    ax.set_aspect("equal", adjustable="box")  # pie() switches to "datalim"


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


@dataclass(frozen=True)
class ZoomWindow:
    x0: float
    x1: float
    y0: float
    y1: float


def ring_x(top_pct: float) -> float:
    """x at the outer edge of the ring where the richest `top_pct`% of adults end."""
    return math.sin(math.radians(top_pct * 3.6))


def zoom_window(level_pct: float, aspect: float) -> ZoomWindow:
    """Window around 12 o'clock showing the top `level_pct`% of the adults donut."""
    width = ZOOM_WINDOW_WIDTH_PER_PCT * level_pct
    height = width / aspect
    x0 = -ZOOM_WINDOW_LEFT * width
    y0 = 1.0 - ZOOM_RING_FRACTION * height
    return ZoomWindow(x0, x0 + width, y0, y0 + height)


def outline(ax: Axes, w: ZoomWindow) -> None:
    ax.add_patch(
        Rectangle(
            (w.x0, w.y0),
            w.x1 - w.x0,
            w.y1 - w.y0,
            fill=False,
            edgecolor=INK_SECONDARY,
            linewidth=0.8,
            zorder=5,
        )
    )


def connect(
    fig: Figure,
    ax_a: Axes,
    xy_a: tuple[float, float],
    ax_b: Axes,
    xy_b: tuple[float, float],
) -> None:
    fig.add_artist(
        ConnectionPatch(
            xyA=xy_a,
            coordsA=ax_a.transData,
            xyB=xy_b,
            coordsB=ax_b.transData,
            color=INK_SECONDARY,
            linewidth=0.8,
            # Behind the axes: the opaque zoom panels hide the stretch that would
            # otherwise cut across their bands and labels.
            zorder=-1,
        )
    )


def plot_zoom_panel(
    ax: Axes, groups: list[Group], window: ZoomWindow, level_pct: float, last: bool
) -> None:
    """One zoom panel: the ring around 12 o'clock, labelling the bands it resolves."""
    population = [g.population_pct for g in groups]
    draw_ring(ax, groups, population, clip=True)
    ax.set_xlim(window.x0, window.x1)
    ax.set_ylim(window.y0, window.y1)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_frame_on(True)  # pie() switches the frame off
    ax.set_facecolor(SURFACE)
    for spine in ax.spines.values():
        spine.set_edgecolor(INK_SECONDARY)
        spine.set_linewidth(0.8)
    closer = round(ZOOM_LEVELS_PCT[0] / level_pct)
    title = f"Top {level_pct:g}%" + (f" ({closer}× closer)" if closer > 1 else "")
    ax.set_title(title, fontsize=LABEL_FONTSIZE + 1, color=INK_SECONDARY, pad=6)

    width = window.x1 - window.x0
    ring_mid_y = 1.0 - ZOOM_RING_FRACTION * (window.y1 - window.y0) / 2
    richer = 0.0  # population share (%) of all richer groups
    for group in groups[::-1]:
        upper = richer + group.population_pct
        richer = upper
        # Label the band(s) this panel resolves: the one starting at this level,
        # and on the last panel every richer band too.
        if not (math.isclose(upper, level_pct) or (last and upper < level_pct)):
            continue
        x_lo, x_hi = ring_x(upper - group.population_pct), ring_x(upper)
        x_mid = (max(x_lo, window.x0) + min(x_hi, window.x1)) / 2
        if (
            min(x_hi, window.x1) - max(x_lo, window.x0)
        ) / width >= ZOOM_LABEL_INSIDE_MIN:
            ax.text(
                x_mid,
                ring_mid_y,
                group.name,
                ha="center",
                va="center",
                fontsize=LABEL_FONTSIZE,
                color=INK,
            )
        else:
            # Too thin for text: label in the white space above the ring.
            ax.annotate(
                group.name,
                xy=(x_mid, 1.0),
                xytext=(0, 10),
                textcoords="offset points",
                ha="left",
                va="bottom",
                fontsize=LABEL_FONTSIZE,
                color=INK,
                arrowprops={
                    "arrowstyle": "-",
                    "color": INK_SECONDARY,
                    "linewidth": 0.6,
                },
            )


def plot_donuts_zoom(df: pl.DataFrame, year: int, out_path: Path) -> None:
    groups = build_groups(df, DETAILED_GROUPS)
    fig = plt.figure(figsize=ZOOM_FIGSIZE, facecolor=SURFACE)
    ax_pop, ax_wealth = (fig.add_axes(box) for box in ZOOM_DONUT_BOXES)

    top_names = frozenset(
        spec.name for spec in DETAILED_GROUPS if spec.upper <= ZOOM_LEVELS_PCT[0]
    )
    plot_donut(
        ax_pop,
        groups,
        [g.population_pct for g in groups],
        [g.name for g in groups],
        "Share of\nadults",
        unlabelled=top_names,  # labelled in the zoom panels
    )
    plot_wealth_donut(ax_wealth, groups)

    panel_w, panel_h = ZOOM_PANEL_SIZE
    fig_w, fig_h = ZOOM_FIGSIZE
    aspect = (panel_w * fig_w) / (panel_h * fig_h)
    windows = [zoom_window(level, aspect) for level in ZOOM_LEVELS_PCT]
    panels = [
        fig.add_axes((left, ZOOM_PANEL_BOTTOM, panel_w, panel_h))
        for left in ZOOM_PANEL_LEFTS
    ]
    for k, (panel, window, level) in enumerate(
        zip(panels, windows, ZOOM_LEVELS_PCT, strict=True)
    ):
        plot_zoom_panel(panel, groups, window, level, last=k == len(panels) - 1)

    # Donut -> first panel: the rectangle's top corners to the panel's bottom ones.
    first = windows[0]
    outline(ax_pop, first)
    for x in (first.x0, first.x1):
        connect(fig, ax_pop, (x, first.y1), panels[0], (x, first.y0))
    # Panel -> next panel: matching right/left corners.
    for k in range(len(panels) - 1):
        nxt = windows[k + 1]
        outline(panels[k], nxt)
        for y in (nxt.y0, nxt.y1):
            connect(fig, panels[k], (nxt.x1, y), panels[k + 1], (nxt.x0, y))

    finish_figure(fig, year, out_path)
