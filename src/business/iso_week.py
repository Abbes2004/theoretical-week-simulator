"""ISO-8601 (year, week) conversion.

Evidence: docs/analysis/TASK2_Supporting_Sources_Business_Mapping.md
confirms that ``plan_t_simplaniffourniture.EtatAccessoire`` stores the
ISO-8601 (year, week) of ``DateAccesoire`` in ``YYYYWW`` form (13/13 exact
matches recomputed in this session, e.g. 2025-07-30 -> '202531', which is
ISO week 31 of ISO year 2025). Using ISO-8601 for ``SemTheorique`` itself is
a RECOMMENDATION built on that adjacent evidence, not a fact confirmed for
SemTheorique directly (SemTheorique is 100% NULL in every available POI
extract, so it cannot be checked directly). See configs/settings.py
(WEEK_CONVENTION) and docs/execution/08_canonical_dataset_specification.md.

Python's ``date.isocalendar()`` already implements ISO-8601 week numbering,
including year-boundary behaviour (a late-December date can belong to ISO
week 1 of the *next* year, and an early-January date can belong to ISO week
52/53 of the *previous* year) and the existence of a 53rd week in some
years. We rely on the standard library rather than re-implementing this.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class IsoWeek:
    iso_year: int
    iso_week: int
    week_key: str  # "YYYYWW", zero-padded, e.g. "202531"
    label: str  # "S31" style display label used in the cahier des charges

    @staticmethod
    def from_date(d: date) -> "IsoWeek":
        iso_year, iso_week, _ = d.isocalendar()
        return IsoWeek(
            iso_year=iso_year,
            iso_week=iso_week,
            week_key=f"{iso_year}{iso_week:02d}",
            label=f"S{iso_week:02d}",
        )
