"""Shared chart styling."""

BLUE = "#2a78d6"
RED = "#e34948"
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
GRID = "#e4e3df"
SURFACE = "#fcfcfb"

LABEL_FONTSIZE = 9

# Footer of every chart: what "wealth" means here (WID's definition of net
# personal wealth), then the data source and author.
WEALTH_NOTE = (
    "Wealth: net personal wealth, i.e. households' assets (housing, land, "
    "deposits, bonds, equities, …) minus their debts."
)
WEALTH_NOTE_DE = (
    "Vermögen: Nettovermögen, d. h. Vermögenswerte der Haushalte (Immobilien, "
    "Grundstücke, Einlagen, Anleihen, Aktien, …) abzüglich Schulden."
)
SOURCE_NOTE = (
    f"{WEALTH_NOTE}\n"
    "Data: WID.world (net personal wealth, equal-split adults 20+)"
    " · Chart: Thomas Camminady"
)
SOURCE_NOTE_DE = (
    f"{WEALTH_NOTE_DE}\n"
    "Daten: WID.world (Nettovermögen, Erwachsene ab 20, Paarvermögen hälftig geteilt)"
    " · Grafik: Thomas Camminady"
)
