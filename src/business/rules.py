"""Pure business-rule engine for the theoretical production week.

This module contains no I/O: it is deliberately independent from pandas,
file paths, and the SQL/Excel sources so it can be unit-tested in complete
isolation (docs/execution/10_simulator_specification.md, "Implementation
Order": "1. Pure calculation functions" before anything else).

Confirmed rule (docs/context/Business Rules.md, docs/execution/08):

    DateTheorique = MAX(applicable component availability dates)
    SemTheorique  = Week(DateTheorique)
    BlockingElement = every required component whose date == DateTheorique

Everything else here (how "applicable" is decided, what happens when a
required component is missing or invalid) is documented inline against the
specific edge case it implements, because none of it is a confirmed company
rule end-to-end -- see docs/context/Open Questions & Business Validation.md.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from .date_parsing import ParsedDate, is_suspicious, parse_date
from .enums import Applicability, CalculationStatus, QualityFlag
from .iso_week import IsoWeek

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from configs.settings import DEFAULT_APPLICABILITY_POLICY  # noqa: E402

if DEFAULT_APPLICABILITY_POLICY != "ALL_REQUIRED":
    raise NotImplementedError(
        f"configs.settings.DEFAULT_APPLICABILITY_POLICY={DEFAULT_APPLICABILITY_POLICY!r} "
        "has no implementation in src/business/rules.py yet; only 'ALL_REQUIRED' is supported "
        "in Phase 1 (see determine_applicability())."
    )

COMPONENTS: tuple[str, ...] = ("TISSU", "TISSU_SEC", "FOURNITURE", "FIL", "OK_PRODUCTION")

_DEFAULT_PLAUSIBLE_MIN = date(2000, 1, 1)
_DEFAULT_PLAUSIBLE_MAX = date(2035, 12, 31)


@dataclass(frozen=True)
class ComponentDetail:
    component: str
    raw_value: object
    parsed: ParsedDate
    applicability: Applicability
    is_suspicious: bool


@dataclass(frozen=True)
class CalculationResult:
    status: CalculationStatus
    date_theorique: date | None
    iso_week: IsoWeek | None
    sem_theorique: str | None  # week_key, e.g. "202531"; None unless CALCULATED
    blocking_elements: tuple[str, ...]  # populated only when status == CALCULATED
    missing_components: tuple[str, ...]  # required components with no date
    invalid_components: tuple[str, ...]  # required components with an unparseable date
    suspicious_components: tuple[str, ...]  # valid but out-of-plausible-range dates
    components: dict[str, ComponentDetail]
    quality_flags: tuple[QualityFlag, ...] = field(default_factory=tuple)


def determine_applicability(
    component: str,
    parsed: ParsedDate,
    *,
    applicability_overrides: dict[str, Applicability] | None = None,
) -> Applicability:
    """Decide whether a component is required for this POI.

    RECOMMENDATION (default policy, ``ALL_REQUIRED``): every one of the five
    documented components is treated as required unless the caller
    explicitly overrides it via ``applicability_overrides``. This is the
    conservative choice given that no confirmed rule exists yet for
    inferring "not required" from the real data (the candidate `Ind*`
    fields are unconfirmed and, in the only populated POI extract available,
    are 0 for every single row -- see
    docs/analysis/PHASE0_Initial_Project_Assessment.md). It never silently
    drops a component from the calculation.

    ``applicability_overrides`` is the extension point for callers (tests,
    or a future confirmed business rule) that already know a component is
    NOT_REQUIRED for a specific POI, independent of whether its date is
    populated -- see docs/context/Business Logic to Data Mapping.md section 7
    ("a POI may not require secondary fabric").
    """
    if applicability_overrides and component in applicability_overrides:
        return applicability_overrides[component]
    if not parsed.is_valid:
        return Applicability.UNKNOWN
    if parsed.value is None:
        return Applicability.REQUIRED_BUT_UNAVAILABLE
    return Applicability.REQUIRED_AND_AVAILABLE


def calculate_theoretical_week(
    component_raw_dates: dict[str, object],
    *,
    applicability_overrides: dict[str, Applicability] | None = None,
    plausible_min: date = _DEFAULT_PLAUSIBLE_MIN,
    plausible_max: date = _DEFAULT_PLAUSIBLE_MAX,
) -> CalculationResult:
    """Compute the theoretical production date/week for one POI.

    ``component_raw_dates`` must map every name in :data:`COMPONENTS` to a
    raw date value (``None``, a string, or a ``date``/``datetime``); missing
    keys are treated the same as ``None``.
    """
    quality_flags: list[QualityFlag] = []
    components: dict[str, ComponentDetail] = {}

    for name in COMPONENTS:
        raw = component_raw_dates.get(name)
        parsed = parse_date(raw)
        applicability = determine_applicability(
            name, parsed, applicability_overrides=applicability_overrides
        )
        suspicious = (
            parsed.is_valid
            and parsed.value is not None
            and is_suspicious(parsed.value, plausible_min, plausible_max)
        )
        components[name] = ComponentDetail(
            component=name,
            raw_value=raw,
            parsed=parsed,
            applicability=applicability,
            is_suspicious=suspicious,
        )
        if not parsed.is_valid:
            quality_flags.append(QualityFlag.INVALID_DATE)
        if suspicious:
            quality_flags.append(QualityFlag.SUSPICIOUS_DATE)

    required = [
        name
        for name, detail in components.items()
        if detail.applicability != Applicability.NOT_REQUIRED
    ]

    if not required:
        quality_flags.append(QualityFlag.NO_APPLICABLE_COMPONENTS)
        return CalculationResult(
            status=CalculationStatus.NOT_APPLICABLE,
            date_theorique=None,
            iso_week=None,
            sem_theorique=None,
            blocking_elements=(),
            missing_components=(),
            invalid_components=(),
            suspicious_components=tuple(n for n, d in components.items() if d.is_suspicious),
            components=components,
            quality_flags=tuple(quality_flags),
        )

    invalid_components = tuple(
        n for n in required if components[n].applicability == Applicability.UNKNOWN
    )
    missing_components = tuple(
        n
        for n in required
        if components[n].applicability == Applicability.REQUIRED_BUT_UNAVAILABLE
    )
    suspicious_components = tuple(n for n, d in components.items() if d.is_suspicious)

    if invalid_components:
        quality_flags.append(QualityFlag.INVALID_DATE)
        status = CalculationStatus.INVALID_DATA
    elif missing_components:
        quality_flags.append(QualityFlag.MISSING_COMPONENT_DATE)
        status = CalculationStatus.INCOMPLETE_DATA
    else:
        status = CalculationStatus.CALCULATED

    if status != CalculationStatus.CALCULATED:
        # Production cannot theoretically start until every required
        # component is available (docs/context/Business Rules.md section 5).
        # A partial MAX() over only the known dates would understate the
        # true theoretical date, so no date/week is produced here.
        return CalculationResult(
            status=status,
            date_theorique=None,
            iso_week=None,
            sem_theorique=None,
            blocking_elements=(),
            missing_components=missing_components,
            invalid_components=invalid_components,
            suspicious_components=suspicious_components,
            components=components,
            quality_flags=tuple(quality_flags),
        )

    dated = {n: components[n].parsed.value for n in required}
    date_theorique = max(dated.values())
    blocking_elements = tuple(n for n, d in dated.items() if d == date_theorique)
    iso_week = IsoWeek.from_date(date_theorique)

    return CalculationResult(
        status=CalculationStatus.CALCULATED,
        date_theorique=date_theorique,
        iso_week=iso_week,
        sem_theorique=iso_week.week_key,
        blocking_elements=blocking_elements,
        missing_components=(),
        invalid_components=(),
        suspicious_components=suspicious_components,
        components=components,
        quality_flags=tuple(quality_flags),
    )
