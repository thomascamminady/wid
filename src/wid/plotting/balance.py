"""A balance scale: the richest 0.001% against the poorest 50% of adults.

Both groups hold about the same share of all wealth. Each side carries one
circle whose area is proportional to the number of adults in the group, so
the poorest half's circle has 50,000 times the area of the richest 0.001%'s.
"""

import math
from pathlib import Path

import matplotlib.pyplot as plt
import polars as pl
from matplotlib.patches import Circle, Polygon

from wid.plotting.donut_chart import MAGENTA, VIOLET
from wid.plotting.style import GRID, INK_SECONDARY, SOURCE_NOTE, SURFACE

RICH_PCT = 0.001  # richest x% of adults
POOR_PCT = 50.0  # poorest x% of adults

# Geometry in data units; the big circle sets the scale.
DISC_RADIUS = 1.0
BEAM_HALF_LENGTH = 1.75
FULCRUM_HALF_WIDTH = 0.28
FULCRUM_HEIGHT = 0.7
FULCRUM_GAP = 0.04  # space between the wedge's tip and the beam
BEAM_CLEARANCE = 0.006  # circles rest on top of the beam's line width
RICH_RING_RADIUS = 0.06  # marks the tiny circle so it can be found

# The drawing is large so that the small circle (1/224 of the big one's radius)
# stays visible; text and line widths scale with it.
FIGSIZE: tuple[float, float] = (30.0, 20.0)
DPI = 130
TITLE_SIZE = 40
TEXT_SIZE = 28
FOOTER_SIZE = 18
BEAM_WIDTH = 5.0
LINE_WIDTH = 2.5


def group_shares(bins: pl.DataFrame) -> tuple[float, float]:
    """Share of all wealth (%) of the richest RICH_PCT% and the poorest POOR_PCT%."""
    wealth = bins.select(
        "lo", "hi", w=(pl.col("hi") - pl.col("lo")) * pl.col("avg_eur")
    )
    total = float(wealth["w"].sum())
    rich = float(wealth.filter(pl.col("lo") >= round(100 - RICH_PCT, 6))["w"].sum())
    poor = float(wealth.filter(pl.col("hi") <= POOR_PCT)["w"].sum())
    return 100 * rich / total, 100 * poor / total


def plot_balance(bins: pl.DataFrame, adults: int, year: int, out_path: Path) -> None:
    """`bins`: one year of `wid.io.load_gpercentiles`; `adults`: `wid.io.load_adults`."""
    rich_share, poor_share = group_shares(bins)
    n_rich = adults * RICH_PCT / 100
    n_poor = adults * POOR_PCT / 100
    # Areas proportional to head counts: radius ratio is sqrt(50,000) ≈ 224.
    rich_radius = DISC_RADIUS * math.sqrt(n_rich / n_poor)

    fig, ax = plt.subplots(figsize=FIGSIZE, facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    ax.set_aspect("equal")
    ax.axis("off")

    # Level beam resting on a wedge, with a little space above the wedge's tip.
    ax.plot(
        [-BEAM_HALF_LENGTH, BEAM_HALF_LENGTH],
        [0.0, 0.0],
        color=INK_SECONDARY,
        lw=BEAM_WIDTH,
        solid_capstyle="round",
        zorder=3,
    )
    ax.add_patch(
        Polygon(
            [
                (0.0, -FULCRUM_GAP),
                (-FULCRUM_HALF_WIDTH, -FULCRUM_HEIGHT),
                (FULCRUM_HALF_WIDTH, -FULCRUM_HEIGHT),
            ],
            closed=True,
            facecolor=GRID,
            edgecolor=INK_SECONDARY,
            lw=LINE_WIDTH,
            zorder=2,
        )
    )
    ax.plot(
        [-2 * FULCRUM_HALF_WIDTH, 2 * FULCRUM_HALF_WIDTH],
        [-FULCRUM_HEIGHT] * 2,
        color=INK_SECONDARY,
        lw=LINE_WIDTH,
    )

    # One circle per side, resting on the beam's ends.
    rich_centre = (-BEAM_HALF_LENGTH, BEAM_CLEARANCE + rich_radius)
    poor_centre = (BEAM_HALF_LENGTH, BEAM_CLEARANCE + DISC_RADIUS)
    ax.add_patch(Circle(rich_centre, rich_radius, color=VIOLET, zorder=4))
    ax.add_patch(Circle(poor_centre, DISC_RADIUS, color=MAGENTA, zorder=4))
    ax.add_patch(
        Circle(
            rich_centre,
            RICH_RING_RADIUS,
            fill=False,
            edgecolor=VIOLET,
            lw=LINE_WIDTH,
            zorder=4,
        )
    )

    ax.annotate(
        f"Richest {RICH_PCT:g}%\n{n_rich:,.0f} adults\n{rich_share:.1f}% of all wealth",
        xy=(rich_centre[0], rich_centre[1] + RICH_RING_RADIUS),
        xytext=(rich_centre[0], rich_centre[1] + 0.95),
        ha="center",
        va="bottom",
        fontsize=TEXT_SIZE,
        color=VIOLET,
        arrowprops={"arrowstyle": "-", "color": VIOLET, "lw": LINE_WIDTH, "shrinkB": 0},
    )
    ax.text(
        poor_centre[0],
        poor_centre[1] + DISC_RADIUS + 0.1,
        f"Poorest {POOR_PCT:g}%\n{n_poor / 1e6:.1f} million adults\n"
        f"{poor_share:.1f}% of all wealth",
        ha="center",
        va="bottom",
        fontsize=TEXT_SIZE,
        color=MAGENTA,
    )

    ax.set_xlim(-BEAM_HALF_LENGTH - 0.75, BEAM_HALF_LENGTH + DISC_RADIUS + 0.1)
    ax.set_ylim(-FULCRUM_HEIGHT - 0.1, 2 * DISC_RADIUS + 0.75)
    # The equal aspect shrinks the axes inside the figure; centre the text on
    # the drawing rather than on the (wider) canvas.
    fig.canvas.draw()
    box = ax.get_position()
    centre_x = (box.x0 + box.x1) / 2
    fig.suptitle(
        f"Germany {year}: the richest {RICH_PCT:g}% own about as much as the "
        f"poorest {POOR_PCT:g}%",
        color=INK_SECONDARY,
        fontsize=TITLE_SIZE,
        x=centre_x,
        y=0.97,
    )
    fig.text(
        centre_x,
        0.915,
        f"Circle areas are proportional to the number of adults "
        f"(1 : {n_poor / n_rich:,.0f}).",
        ha="center",
        fontsize=TEXT_SIZE,
        color=INK_SECONDARY,
    )
    fig.text(
        box.x1,
        0.01,
        SOURCE_NOTE,
        ha="right",
        va="bottom",
        fontsize=FOOTER_SIZE,
        color=INK_SECONDARY,
    )
    fig.savefig(out_path, dpi=DPI, facecolor=SURFACE, bbox_inches="tight")
    print(f"Saved {out_path}")
