"""Charts of the German wealth distribution."""

from wid.plotting.bar_of_donut import plot_bar_of_donut, plot_wealth_donut_shaded
from wid.plotting.donut_chart import plot_donuts
from wid.plotting.line_chart import plot_line_chart
from wid.plotting.percentile_bars import plot_percentile_bars

__all__ = [
    "plot_bar_of_donut",
    "plot_donuts",
    "plot_line_chart",
    "plot_percentile_bars",
    "plot_wealth_donut_shaded",
]
