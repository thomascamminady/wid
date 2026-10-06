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
from wid.plotting.style import INK_SECONDARY, SOURCE_NOTE, SURFACE

RICH_PCT = 0.001  # richest x% of adults
POOR_PCT = 50.0  # poorest x% of adults

# Geometry in data units; the big circle sets the scale.
DISC_RADIUS = 1.0
BEAM_HALF_LENGTH = 1.75
FULCRUM_HALF_WIDTH = 0.28
FULCRUM_HEIGHT = 0.7
BEAM_CLEARANCE = 0.006  # circles rest on top of the beam's line width

# The drawing is large so that the small circle (1/224 of the big one's radius)
# stays visible; text and line widths scale with it.
FIGSIZE: tuple[float, float] = (30.0, 20.0)
DPI = 130
TITLE_SIZE = 40
TEXT_SIZE = 28
FOOTER_SIZE = 18
BEAM_WIDTH = 5.0
LINE_WIDTH = 2.5
SCALE_GREY = "#8c8a85"  # beam and wedge: lighter than the text grey
TITLE_GAP = 0.32  # data units above the big circle
SUBTITLE_GAP = 0.12


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

    # Level beam resting on a wedge.
    ax.plot(
        [-BEAM_HALF_LENGTH, BEAM_HALF_LENGTH],
        [0.0, 0.0],
        color=SCALE_GREY,
        lw=BEAM_WIDTH,
        solid_capstyle="round",
        zorder=3,
    )
    ax.add_patch(
        Polygon(
            [
                (0.0, 0.0),
                (-FULCRUM_HALF_WIDTH, -FULCRUM_HEIGHT),
                (FULCRUM_HALF_WIDTH, -FULCRUM_HEIGHT),
            ],
            closed=True,
            facecolor=SCALE_GREY,
            edgecolor="none",
            zorder=2,
        )
    )

    # One circle per side, resting on the beam's ends.
    rich_centre = (-BEAM_HALF_LENGTH, BEAM_CLEARANCE + rich_radius)
    poor_centre = (BEAM_HALF_LENGTH, BEAM_CLEARANCE + DISC_RADIUS)
    ax.add_patch(Circle(rich_centre, rich_radius, color=VIOLET, zorder=4))
    ax.add_patch(Circle(poor_centre, DISC_RADIUS, color=MAGENTA, zorder=4))

    ax.annotate(
        f"Richest {RICH_PCT:g}%\n{n_rich:,.0f} adults\n{rich_share:.1f}% of all wealth",
        xy=(rich_centre[0], rich_centre[1] + rich_radius),
        xytext=(rich_centre[0], rich_centre[1] + 0.95),
        ha="center",
        va="bottom",
        fontsize=TEXT_SIZE,
        color=VIOLET,
        arrowprops={"arrowstyle": "-", "color": VIOLET, "lw": LINE_WIDTH, "shrinkB": 4},
    )
    ax.text(
        *poor_centre,
        f"Poorest {POOR_PCT:g}%\n{n_poor / 1e6:.1f} million adults\n"
        f"{poor_share:.1f}% of all wealth",
        ha="center",
        va="center",
        fontsize=TEXT_SIZE,
        color="white",
        zorder=5,
    )

    # Small margins so the big circle (which rests on the beam's line width)
    # is not clipped at the top or right.
    x_min, x_max = -BEAM_HALF_LENGTH - 0.75, BEAM_HALF_LENGTH + DISC_RADIUS + 0.02
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(-FULCRUM_HEIGHT, 2 * DISC_RADIUS + 0.02)
    # Title and subtitle sit just above the drawing, centred on it.
    centre_x = (x_min + x_max) / 2
    ax.text(
        centre_x,
        2 * DISC_RADIUS + TITLE_GAP,
        f"Germany {year}: the richest {RICH_PCT:g}% own about as much as the "
        f"poorest {POOR_PCT:g}%",
        ha="center",
        va="bottom",
        fontsize=TITLE_SIZE,
        color=INK_SECONDARY,
    )
    ratio = f"{n_poor / n_rich:,.0f}".replace(",", " ")  # 50 000
    ax.text(
        centre_x,
        2 * DISC_RADIUS + SUBTITLE_GAP,
        f"Circle areas are proportional to the number of adults (1 : {ratio}).",
        ha="center",
        va="bottom",
        fontsize=TEXT_SIZE,
        color=INK_SECONDARY,
    )
    # Footer in two lines, its last line level with the wedge's base.
    ax.text(
        x_max,
        -FULCRUM_HEIGHT,
        SOURCE_NOTE.replace(" · ", "\n"),
        ha="right",
        va="bottom",
        fontsize=FOOTER_SIZE,
        color=INK_SECONDARY,
    )
    fig.savefig(out_path, dpi=DPI, facecolor=SURFACE, bbox_inches="tight")
    print(f"Saved {out_path}")
