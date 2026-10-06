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
from wid.plotting.style import (
    GRID,
    INK_SECONDARY,
    SOURCE_NOTE,
    SOURCE_NOTE_DE,
    SURFACE,
)


@dataclass(frozen=True)
class BarGroup:
    """A labelled run of bars from `x0` to `x1` (percent of adults, poorest first)."""

    name: str
    x0: float
    x1: float
    color: str
    text_color: str | None = None  # for bar colours too light to read as text

    @property
    def label_color(self) -> str:
        return self.text_color or self.color


ALL_ADULTS_GROUPS: tuple[BarGroup, ...] = tuple(
    BarGroup(spec.name, 100 - spec.upper, 100 - spec.lower, spec.color)
    for spec in DONUT_GROUPS
)
# Inside the top 1%: the purple shades of the bar-of-donut chart, lightest first.
TOP_PERCENT_GROUPS: tuple[BarGroup, ...] = (
    # Same hue, darker (OKLCH L 0.56): 4.7:1 contrast instead of 2.3:1.
    BarGroup("Top 1–0.1%", 99.0, 99.9, TOP_PARTS[0].color, text_color="#6c69b8"),
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
Y_HEADROOM = 1.08  # y range = tallest bar * this

# Font sizes relative to matplotlib's base size (rcParams["font.size"], 10 by
# default), so a figure can scale all its text with one rc setting.
LABEL_SCALE = 0.9
ZOOM_LABEL_SCALE = 1.0
PANEL_TITLE_SCALE = 1.2
TITLE_SCALE = 1.6
FOOTER_SCALE = 0.8
STAIRCASE_FONT_SIZE = 12.0  # 20% above the default, for phone screens
MULTI_PANEL_TITLE = (
    "average net wealth per adult, from the poorest to the richest 0.001%"
)

# Staircase layout (figure fractions): wide panels, each stepping right by a
# fixed amount. That keeps the next panel left of centre under the zoomed bar
# (which sits at the right edge), so the chart uses the width with little
# white space.
STAIRCASE_FIGSIZE: tuple[float, float] = (13.0, 14.0)
STAIRCASE_PANEL_WIDTH = 0.6
STAIRCASE_PANEL_HEIGHT = 0.22
STAIRCASE_LEFTS: tuple[float, ...] = (0.07, 0.22, 0.37)
STAIRCASE_BOTTOMS: tuple[float, ...] = (0.71, 0.395, 0.08)
STAIRCASE_TITLE_GAP = 0.015  # figure fraction between top panel and title
# Zoom lines start from one point this far below the x axis (axes fraction),
# just under the "100%" tick label. Their label sits this far right of the
# right-hand line's midpoint (points).
ZOOM_LINE_START_Y = -0.12
ZOOM_LABEL_OFFSET = 8.0
ZOOM_LINE_WIDTH = 0.6


Lang = Literal["en", "de"]

# User-facing text of the staircase figure (and the shared bar labels).
TEXTS: dict[Lang, dict[str, str]] = {
    "en": {
        "of_all_wealth": "of all wealth",
        "ylabel": "Average net wealth per adult",
        "title": "Germany {year}: " + MULTI_PANEL_TITLE,
        "x_all": "All adults, sorted from poorest (left) to richest (right)",
        "x_top1": "The richest 1% of adults",
        "x_top001": "The richest 0.01% of adults",
        "zoom_top1": "Zoom into\nthe top 1%",
        "zoom_top001": "Zoom into\nthe top 0.01%",
        "footer": SOURCE_NOTE,
    },
    "de": {
        "of_all_wealth": "des Gesamtvermögens",
        "ylabel": "Ø Nettovermögen pro Erwachsenem",
        "title": "Deutschland {year}: durchschnittliches Nettovermögen pro "
        "Erwachsenem,\nvon den Ärmsten bis zu den reichsten 0,001 %",
        "x_all": "Alle Erwachsenen, sortiert von den Ärmsten (links) bis zu den "
        "Reichsten (rechts)",
        "x_top1": "Die reichsten 1 % der Erwachsenen",
        "x_top001": "Die reichsten 0,01 % der Erwachsenen",
        "zoom_top1": "Zoom auf die\nreichsten 1 %",
        "zoom_top001": "Zoom auf die\nreichsten 0,01 %",
        "footer": SOURCE_NOTE_DE,
    },
}


def german_number(text: str) -> str:
    """Decimal comma: 99.2 -> 99,2."""
    return text.replace(".", ",")


def format_pct(fraction: float, lang: Lang) -> str:
    """0.279 -> "27.9%" (en) or "27,9 %" (de)."""
    if lang == "de":
        return f"{german_number(f'{100 * fraction:.1f}')} %"
    return f"{fraction:.1%}"


def format_pct_tick(value: float, lang: Lang) -> str:
    """Axis ticks in percent of adults: 99.2 -> "99.2%" (en) or "99,2 %" (de)."""
    return f"{german_number(f'{value:g}')} %" if lang == "de" else f"{value:g}%"


def format_eur(value: float, _pos: int | None = None, lang: Lang = "en") -> str:
    """€8M, €1.2bn (en) or 8 Mio. €, 1,2 Mrd. € (de)."""
    units = (
        ((1e9, "Mrd. €"), (1e6, "Mio. €"), (1e3, "Tsd. €"))
        if lang == "de"
        else ((1e9, "bn"), (1e6, "M"), (1e3, "k"))
    )
    for scale, unit in units:
        if abs(value) >= scale:
            number = f"{value / scale:g}"
            break
    else:
        number, unit = f"{value:g}", ("€" if lang == "de" else "")
    if lang == "de":
        return f"{german_number(number)} {unit}"
    return f"€{number}{unit}"


def group_label(name: str, lang: Lang) -> str:
    """Group names in German: "Top 1–0.1%" -> "Top 1–0,1 %"."""
    if lang == "en":
        return name
    name = name.replace("Bottom", "Untere").replace("Middle", "Mittlere")
    return german_number(name).replace("%", " %")


def font_size(scale: float) -> float:
    return plt.rcParams["font.size"] * scale


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
    lang: Lang = "en",
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
        group_share = format_pct(sum(share[i] for i in idx), lang)
        text = (
            f"{group_label(group.name, lang)}\n"
            f"{group_share} {TEXTS[lang]['of_all_wealth']}"
        )
        tallest = max(max(avg[i] for i in idx), 0.0)
        if len(idx) == 1:
            # A single bar: label to its left, top-aligned with the bar.
            ax.text(
                group.x0 - NARROW_LABEL_INSET * x_range,
                tallest,
                text,
                ha="right",
                va="top",
                fontsize=font_size(LABEL_SCALE),
                color=group.label_color,
            )
            continue
        # Several bars: a bracket over them with the label above it.
        y = tallest + lift
        pad = 0.003 * x_range
        ax.plot([group.x0 + pad, group.x1 - pad], [y, y], color=group.color, lw=1.2)
        wide = (group.x1 - group.x0) / x_range >= CENTRED_LABEL_MIN_FRACTION
        ax.text(
            (group.x0 + group.x1) / 2
            if wide
            else group.x1 - NARROW_LABEL_INSET * x_range,
            y + lift / 2,
            text,
            ha="center" if wide else "right",
            va="bottom",
            fontsize=font_size(LABEL_SCALE),
            color=group.label_color,
        )

    ax.set_xlim(x_min, x_max)
    ax.set_ylim(bottom=0.0 if clip_at_zero else None, top=y_top)
    ax.xaxis.set_major_locator(MultipleLocator(tick_step))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: format_pct_tick(v, lang)))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: format_eur(v, lang=lang)))
    # No gridline above the tallest bar. Keep ticks inside the current limits
    # too: set_yticks would otherwise stretch the axis to an out-of-view tick.
    y_bottom = ax.get_ylim()[0]
    ax.set_yticks([t for t in ax.get_yticks() if y_bottom <= t <= max(avg)])
    ax.set_xlabel(xlabel, color=INK_SECONDARY, loc=xlabel_loc)
    ax.set_ylabel(TEXTS[lang]["ylabel"], color=INK_SECONDARY)

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


def save(fig: Figure, out_path: Path, footer: str = SOURCE_NOTE) -> None:
    fig.text(
        0.99,
        0.005,
        footer,
        fontsize=font_size(FOOTER_SCALE),
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
        fontsize=font_size(TITLE_SCALE),
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
        f"Germany {year}: {MULTI_PANEL_TITLE}",
        color=INK_SECONDARY,
        fontsize=font_size(TITLE_SCALE),
    )
    for ax, title in (
        (ax_top1, "Zoom into the top 1%"),
        (ax_top001, "Zoom into the top 0.01%"),
    ):
        ax.set_title(
            title, color=INK_SECONDARY, fontsize=font_size(PANEL_TITLE_SCALE), pad=10
        )
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
                linewidth=ZOOM_LINE_WIDTH,
            )
        )

    # Label just right of the right-hand line's midpoint, kept horizontal. Its
    # bottom-left corner sits above the line, and the line falls away to the
    # right, so the text never touches it.
    start_px = below_axis.transform(start)
    end_px = ax_to.transData.transform((x1, y_top))
    mid = fig.transFigure.inverted().transform((start_px + end_px) / 2)
    fig.text(
        mid[0],
        mid[1],
        label,
        ha="left",
        va="bottom",
        fontsize=font_size(ZOOM_LABEL_SCALE),
        color=INK_SECONDARY,
        transform=offset_copy(
            fig.transFigure,
            fig=fig,
            x=ZOOM_LABEL_OFFSET,
            y=ZOOM_LABEL_OFFSET / 2,
            units="points",
        ),
    )


def plot_percentile_bars_staircase(
    df_pct: pl.DataFrame,
    df_top1: pl.DataFrame,
    df_top001: pl.DataFrame,
    year: int,
    out_path: Path,
    lang: Lang = "en",
) -> None:
    """The three panels of `plot_percentile_bars_zoom` as a staircase of zooms.

    All text is drawn 20% larger than in the other charts, for phone screens.
    `lang="de"` draws the figure in German.
    """
    # Saving happens inside the context too: tick labels pick up their size
    # when they are drawn.
    with plt.rc_context({"font.size": STAIRCASE_FONT_SIZE}):
        _plot_staircase(df_pct, df_top1, df_top001, year, out_path, lang)


def _plot_staircase(
    df_pct: pl.DataFrame,
    df_top1: pl.DataFrame,
    df_top001: pl.DataFrame,
    year: int,
    out_path: Path,
    lang: Lang,
) -> None:
    text = TEXTS[lang]
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
        xlabel=text["x_all"],
        xlabel_loc="left",
        clip_at_zero=True,
        lang=lang,
    )
    draw_bars(
        ax_top1,
        df_top1,
        TOP_PERCENT_GROUPS,
        tick_step=0.2,
        xlabel=text["x_top1"],
        xlabel_loc="left",
        lang=lang,
    )
    draw_bars(
        ax_top001,
        df_top001,
        TOP_BASIS_POINT_GROUPS,
        tick_step=0.002,
        xlabel=text["x_top001"],
        xlabel_loc="left",
        lang=lang,
    )
    # Anchor the title by its bottom edge just above the top panel, so a
    # two-line title (German) grows upwards instead of into the panel.
    fig.suptitle(
        text["title"].format(year=year),
        color=INK_SECONDARY,
        fontsize=font_size(TITLE_SCALE),
        y=STAIRCASE_BOTTOMS[0] + STAIRCASE_PANEL_HEIGHT + STAIRCASE_TITLE_GAP,
        va="bottom",
    )
    link_zoom(
        fig,
        ax_all,
        ax_top1,
        99.0,
        100.0,
        df_pct["avg_eur"][-1],
        text["zoom_top1"],
    )
    link_zoom(
        fig,
        ax_top1,
        ax_top001,
        99.99,
        100.0,
        df_top1["avg_eur"][-1],
        text["zoom_top001"],
    )
    save(fig, out_path, text["footer"])
