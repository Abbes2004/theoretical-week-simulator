"""Enumerations shared by the business-rule engine.

Values are deliberately explicit strings (not bare ints) so canonical
datasets and JSON/CLI output remain self-describing.
"""

from __future__ import annotations

from enum import Enum


class Applicability(str, Enum):
    """Whether a component is required for a given POI, per
    docs/execution/08_canonical_dataset_specification.md ("Applicability").
    """

    NOT_REQUIRED = "NOT_REQUIRED"
    REQUIRED_AND_AVAILABLE = "REQUIRED_AND_AVAILABLE"
    REQUIRED_BUT_UNAVAILABLE = "REQUIRED_BUT_UNAVAILABLE"
    UNKNOWN = "UNKNOWN"


class CalculationStatus(str, Enum):
    """Overall outcome of the theoretical-week calculation for one POI.

    Vocabulary taken from docs/context/Edge Cases & Data Quality Handling.md
    ("Recommended Output Status Model"), explicitly marked there as "a
    proposal, to be adapted if the company has official statuses."
    """

    CALCULATED = "CALCULATED"
    INCOMPLETE_DATA = "INCOMPLETE_DATA"
    INVALID_DATA = "INVALID_DATA"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class DataOrigin(str, Enum):
    """MASTER_PROMPT.md section 2.3: real and synthetic data must never be
    silently mixed."""

    REAL = "REAL"
    DERIVED = "DERIVED"
    SYNTHETIC = "SYNTHETIC"


class QualityFlag(str, Enum):
    """Data-quality flags, taken from docs/context/Data Profiling.md
    ("Data Quality Flags to be produced") and extended with flags needed by
    docs/context/Edge Cases & Data Quality Handling.md.
    """

    MISSING_COMPONENT_DATE = "MISSING_COMPONENT_DATE"
    INVALID_DATE = "INVALID_DATE"
    SUSPICIOUS_DATE = "SUSPICIOUS_DATE"
    MISSING_SEM_THEORIQUE = "MISSING_SEM_THEORIQUE"
    SEM_THEORIQUE_MISMATCH = "SEM_THEORIQUE_MISMATCH"
    DUPLICATE_POI = "DUPLICATE_POI"
    ORPHAN_POI = "ORPHAN_POI"
    ORPHAN_STOCK = "ORPHAN_STOCK"
    SUSPICIOUS_QUANTITY = "SUSPICIOUS_QUANTITY"
    DATE_INCONSISTENCY = "DATE_INCONSISTENCY"
    MISSING_IDENTIFIER = "MISSING_IDENTIFIER"
    NO_APPLICABLE_COMPONENTS = "NO_APPLICABLE_COMPONENTS"
