# 09 — Edge Cases & Data Quality Handling

## 1. Purpose

This document defines the edge cases that must be considered when calculating the theoretical production date and week for each POI.

The objective is to prevent the simulator from producing misleading results when the source data is incomplete, inconsistent, invalid, or ambiguous.

The rules below distinguish between:

- confirmed business behavior,
- data-quality observations,
- cases requiring validation,
- implementation recommendations.

---

## 2. General Principle

The simulator must never silently transform a problematic input into a valid-looking result.

For every POI, the calculation should lead to one of the following outcomes:

```text
VALID_RESULT
INCOMPLETE_DATA
INVALID_DATA
NOT_APPLICABLE
AMBIGUOUS
```

The exact final status vocabulary can be adapted during implementation.

---

## 3. Missing Component Date

A component availability date may be `NULL`.

Example:

```text
DateTissu = 2025-08-04
DateFil = NULL
```

A missing date must not automatically be interpreted as:

```text
DateFil = 0
```

or:

```text
DateFil = today
```

or any other artificial value.

The simulator must first determine whether the component is:

```text
NOT_REQUIRED
```

or:

```text
REQUIRED_BUT_UNAVAILABLE
```

before calculating the theoretical date.

---

## 4. Component Not Required

Some POIs may not require every possible production element.

For example, a POI may not require secondary fabric.

In that situation:

```text
DateTissuSec = NULL
```

may be a legitimate value.

The simulator must therefore avoid treating every `NULL` as an error.

The requirement status of each component should ideally be determined from validated business rules or reliable source indicators.

---

## 5. Required Component Without Availability

A more critical situation is:

```text
Component = REQUIRED
Availability Date = NULL
```

This means the POI cannot be considered fully available until the business rule confirms otherwise.

The simulator should flag this case rather than calculating a normal theoretical week from the other components.

Example:

```text
Tissu        = available
Fourniture   = available
Fil          = unavailable
OK Production = available
```

Expected logical status:

```text
INCOMPLETE_DATA
```

unless the company's validated rules define another behavior.

---

## 6. Invalid Date Format

Source data may contain malformed or unexpected date values.

Examples:

```text
2025-99-40
31/31/2025
ABC
empty string
```

The simulator must validate dates during preprocessing.

Invalid dates should be recorded as data-quality errors and should not participate in the `MAX()` calculation.

---

## 7. Future or Unexpected Dates

A date may technically be valid but still be suspicious from a business perspective.

For example:

```text
DateTissu = 2099-01-01
```

The date is syntactically valid but may indicate:

- data-entry error,
- incorrect source transformation,
- placeholder value,
- corrupted data.

The simulator should distinguish:

```text
VALID_DATE
```

from:

```text
SUSPICIOUS_DATE
```

rather than automatically deleting suspicious records.

The acceptable date range should be defined from the project study period and validated with the company.

---

## 8. Date Ordering Inconsistency

Some component-related dates may have logical ordering constraints.

For example, depending on the business process:

```text
Order Date
    ≤
Reception Date
    ≤
Availability Date
```

If the source data contains:

```text
Reception Date < Order Date
```

this should be flagged for investigation.

The exact ordering constraints cannot be assumed until the corresponding business process is validated.

---

## 9. Historical `SemTheorique` Missing

A POI may have:

```text
SemTheorique = NULL
```

This does not necessarily mean that the simulator cannot calculate a theoretical week.

The historical field is primarily used as a reference for validation.

Therefore:

```text
Historical result missing
        ↓
Still potentially calculable
        ↓
No historical comparison possible
```

Such POIs can still be used to test the simulator's forward calculation.

---

## 10. Historical Result vs Calculated Result Mismatch

A calculated result may differ from the historical `SemTheorique`.

Example:

```text
Calculated = Week 32
Historical = Week 33
```

This should not immediately be classified as a simulator bug.

Possible explanations include:

- missing business rules,
- different component requirement logic,
- different date calculation,
- manual modification,
- historical correction,
- different week convention,
- incomplete source data.

Therefore every mismatch should be considered a **validation case requiring investigation**.

---

## 11. Multiple Components With the Same Maximum Date

Several components can have the same latest availability date.

Example:

```text
DateTissu        = 2025-08-08
DateTissuSec     = 2025-08-08
DateFourniture   = 2025-08-06
DateFil          = 2025-08-07
DateOKProduction = 2025-08-08
```

The theoretical date is:

```text
2025-08-08
```

However, the blocking element is not uniquely determined.

The simulator should preserve all tied elements until the business rule is validated.

Example:

```text
BlockingElements =
[
    "Tissu",
    "TissuSec",
    "OK Production"
]
```

---

## 12. No Required Elements

An unexpected POI may contain no identified required production elements.

The simulator should not calculate:

```text
MAX(empty set)
```

and generate an artificial result.

Instead:

```text
Status = INVALID_DATA
```

or another validated business status should be returned.

---

## 13. Duplicate POI Records

The POI table has a uniqueness constraint involving:

```text
Id_Sim + POI_Sim
```

Nevertheless, duplicate or duplicated-looking records may appear during data extraction or joins.

The simulator must verify the expected grain before calculation:

```text
One Simulation + One POI
        ↓
One logical POI record
```

Duplicate records created by joins must not cause duplicated results or incorrect aggregations.

---

## 14. Duplicate Rows Introduced by Joins

This is particularly important when joining:

```text
plan_t_simplanif
        +
plan_t_simplanifpoi
        +
plan_t_simplanifstock
```

A one-to-many relationship can multiply rows.

Example:

```text
1 POI
  ├── 3 stock rows
  └── 2 supply rows

Naive join
    ↓
3 × 2 = 6 rows
```

This can corrupt calculations.

The simulator must therefore aggregate or reduce one-to-many sources to the appropriate grain before joining them.

---

## 15. Missing Simulation Reference

A POI contains:

```text
Id_Sim
```

which should reference a simulation.

If a POI has no corresponding simulation record, the relationship should be flagged.

This is a referential-integrity issue.

The simulator should not silently attach the POI to another simulation.

---

## 16. Missing POI Identifier

A POI without a valid identifier cannot reliably be tracked.

Example:

```text
Id_Sim = 5601
POI_Sim = NULL
```

Such a record should be excluded from the normal simulation calculation and recorded as a data-quality issue.

---

## 17. Missing Simulation Identifier

Similarly:

```text
Id_Sim = NULL
```

prevents reliable association with the simulation context.

The record should be flagged rather than arbitrarily assigned to a simulation.

---

## 18. Invalid or Unknown Component Status

Status fields such as:

```text
EtatTissu
EtatTissuSec
EtatFourniture
EtatFil
EtatOkProduction
```

and:

```text
StatutTissuSec
StatutFourniture
StatutFil
StatutOkProduction
```

must not be interpreted based only on their names.

If an unexpected status value is encountered:

```text
UNKNOWN_STATUS
```

should be recorded.

The meaning of each status value must be documented from the source/business validation before becoming a hard filtering rule.

---

## 19. Indicator Inconsistency

The POI table contains indicators such as:

```text
IndTissu
IndTissuSec
IndFourniture
IndFil
IndOkProd
```

A possible inconsistency could be:

```text
IndFil = 1
DateFil = NULL
```

or:

```text
IndFil = 0
DateFil = valid date
```

These situations should be identified during profiling.

However, the simulator must not assume what the indicator means until its semantics are confirmed.

---

## 20. Week Boundary Cases

The conversion from date to week requires special attention around the end and beginning of a year.

Example:

```text
December 2025
        ↓
January 2026
```

The simulator must use the validated company convention.

It should specifically test:

- last days of December,
- first days of January,
- dates belonging to ISO week 52,
- dates belonging to ISO week 53,
- first ISO week of a year.

---

## 21. Empty Dataset

If the input dataset contains no valid POIs:

```text
Input = 0 records
```

the simulator should return an empty result with a clear execution status.

It must not fail because a reduction operation such as `MAX()` has no input.

---

## 22. Partial Dataset

The simulator may receive only part of the source data.

For example:

```text
POI data available
Stock data unavailable
```

If the missing dataset is required to calculate component availability, the result should be marked as incomplete.

The simulator should report which required source is missing.

Example:

```text
Missing source:
plan_t_simplanifstock
```

---

## 23. Out-of-Scope POIs

A POI may fall outside the study period or project scope.

Such records should be filtered according to a documented rule.

The filtering criterion must be explicit, for example:

```text
Study period = [START_DATE, END_DATE]
```

The dates themselves must be defined from the project scope and not invented by the simulator.

---

## 24. Manual or Historical Fields

The POI table contains fields suggesting historical or manual intervention, including:

```text
DateMaxMan
DateTissuMan
DateTissuSecMan
DateFournitureMan
DateFilMan
DateOkProdMan
```

These fields are potentially important when explaining discrepancies between calculated and historical results.

However, their exact precedence over automatically calculated dates must be validated.

The simulator must not automatically override calculated values with manual fields without an explicit business rule.

---

## 25. Error Traceability

Every problematic record should ideally contain enough information to understand why it was not calculated.

Recommended fields:

```text
Id_Sim
POI_Sim
Status
ErrorType
MissingComponent
InvalidField
Source
```

Example:

```text
Id_Sim = 5601
POI_Sim = 01028122582CD
Status = INCOMPLETE_DATA
ErrorType = MISSING_AVAILABILITY
MissingComponent = Fil
```

This is particularly useful during validation and debugging.

---

## 26. Recommended Output Status Model

A possible baseline status model is:

| Status | Meaning |
|---|---|
| `CALCULATED` | All required information available and result calculated |
| `INCOMPLETE_DATA` | Required information is missing |
| `INVALID_DATA` | Source data contains invalid values |
| `NOT_APPLICABLE` | POI does not require the relevant component/process |
| `AMBIGUOUS` | Multiple interpretations/results require business validation |
| `VALIDATION_MISMATCH` | Calculated result differs from historical reference |

This status model is a proposal and should be adapted if the company already has official statuses.

---

## 27. Edge-Case Processing Strategy

The recommended processing order is:

```text
Raw data
   ↓
Schema validation
   ↓
Identifier validation
   ↓
Date validation
   ↓
Component requirement determination
   ↓
Availability validation
   ↓
Business calculation
   ↓
Week conversion
   ↓
Historical comparison
   ↓
Quality/status classification
```

This prevents invalid data from contaminating the business calculation.

---

## 28. Testing Strategy

Each edge case should eventually have at least one automated test.

Examples:

```text
test_missing_component_date()
test_not_required_component()
test_invalid_date()
test_duplicate_poi()
test_missing_simulation()
test_tied_maximum_dates()
test_week_boundary()
test_empty_dataset()
test_historical_mismatch()
```

The objective is to make the simulator deterministic and reproducible.

---

## 29. Important Implementation Principle

The simulator should separate:

```text
Data Quality
```

from:

```text
Business Logic
```

For example:

```text
DateFil = NULL
```

is a data observation.

Whether that means:

```text
"Fil not required"
```

or:

```text
"Fil required but unavailable"
```

is a business-rule question.

The implementation must not silently decide between these interpretations.

---

## 30. Summary

The most important edge cases are:

1. Missing component availability
2. Component not required
3. Required component unavailable
4. Invalid dates
5. Suspicious dates
6. Historical result missing
7. Historical/calculated mismatch
8. Multiple blocking components
9. Duplicate POIs
10. Join-induced duplication
11. Missing simulation references
12. Invalid component statuses
13. Indicator/date inconsistencies
14. Week boundary cases
15. Partial source datasets
16. Manual/historical date overrides

These cases must be addressed before considering the simulator production-ready.

The objective is not to hide problematic data, but to make every calculation **transparent, reproducible, and explainable**.