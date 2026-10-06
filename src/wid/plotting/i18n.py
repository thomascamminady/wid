"""Language-dependent formatting for chart text (English and German)."""

from typing import Literal

from wid.plotting.style import SOURCE_NOTE, SOURCE_NOTE_DE

Lang = Literal["en", "de"]

FOOTER: dict[Lang, str] = {"en": SOURCE_NOTE, "de": SOURCE_NOTE_DE}


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


def format_percent(value: float, lang: Lang) -> str:
    """A value already in percent: 27.9 -> "27.9%" (en) or "27,9 %" (de)."""
    return format_pct(value / 100, lang)
