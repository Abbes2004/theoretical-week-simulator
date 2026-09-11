"""Pure date parsing/validation helpers used by the business-rule engine and
by the cleaning stage.

No function here silently substitutes an arbitrary date for a missing or
invalid one (MASTER_PROMPT.md section 9). Every parse either returns a
concrete ``date`` or ``None`` plus an explicit reason.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

# MySQL "zero dates" are a known artifact of legacy dumps; they are not a
# real calendar date and must never be parsed as one.
_ZERO_DATE_PREFIXES = ("0000-00-00", "0000-00-00 00:00:00")

_KNOWN_FORMATS = (
    "%Y-%m-%d",
    "%Y-%m-%d %H:%M:%S",
    "%d/%m/%Y",
    "%d-%m-%Y",
)


@dataclass(frozen=True)
class ParsedDate:
    value: date | None
    is_valid: bool
    reason: str | None = None  # populated when is_valid is False or value is None


def parse_date(raw: object) -> ParsedDate:
    """Parse a raw value (str, date, datetime, or NaN/None) into a ParsedDate.

    - ``None`` / empty string / NaN -> valid "no date" (``value=None,
      is_valid=True``): a missing value is not, by itself, an invalid value.
    - MySQL zero-dates (e.g. '0000-00-00') -> invalid.
    - Unparseable strings (e.g. 'ABC', '2025-99-40', '31/31/2025') -> invalid.
    - Anything else matching a known format -> valid concrete date.
    """
    if raw is None:
        return ParsedDate(value=None, is_valid=True)

    if isinstance(raw, datetime):
        return ParsedDate(value=raw.date(), is_valid=True)
    if isinstance(raw, date):
        return ParsedDate(value=raw, is_valid=True)

    # pandas may hand us a float NaN for empty cells.
    try:
        import math

        if isinstance(raw, float) and math.isnan(raw):
            return ParsedDate(value=None, is_valid=True)
    except TypeError:
        pass

    text = str(raw).strip()
    if text == "":
        return ParsedDate(value=None, is_valid=True)

    if text.startswith(_ZERO_DATE_PREFIXES):
        return ParsedDate(value=None, is_valid=False, reason=f"zero_date:{text!r}")

    for fmt in _KNOWN_FORMATS:
        try:
            return ParsedDate(value=datetime.strptime(text, fmt).date(), is_valid=True)
        except ValueError:
            continue

    return ParsedDate(value=None, is_valid=False, reason=f"unparseable:{text!r}")


def is_suspicious(value: date, plausible_min: date, plausible_max: date) -> bool:
    """A syntactically valid date can still be operationally implausible.

    See docs/context/Edge Cases & Data Quality Handling.md item 5
    ("Future or Unexpected Dates"): a suspicious date is NOT deleted, only
    flagged.
    """
    return value < plausible_min or value > plausible_max
