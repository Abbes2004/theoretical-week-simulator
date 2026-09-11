# Testing Strategy

## Objective
Ensure the simulator is correct, robust, reproducible, and explainable.

## Test Layers

### Unit
Test:
- week conversion
- maximum-date calculation
- blocker detection
- applicability
- missing-date handling

### Integration
Test:
- raw → canonical transformation
- joins
- canonical → simulator
- output schema

### End-to-End
Run the complete pipeline and verify expected output.

### Performance
Run equivalent workloads for each implementation.

## Core Cases

| Case | Expected |
|---|---|
| All components available | MAX of applicable dates |
| One latest component | That component is blocker |
| Multiple tied latest components | All tied components returned |
| Optional component missing | Ignore |
| Required component missing | Incomplete/unavailable |
| Invalid date | Invalid/quality flag |
| No applicable components | Explicit undefined state |
| Year boundary | Correct year-week |
| Duplicate POI | Validation failure |
| Historical result available | Compare calculated vs historical |

## Property Checks
- Theoretical date cannot be earlier than an included availability date.
- Every blocker has the theoretical date.
- Making a non-maximum date earlier cannot increase the result.
- Adding a later required component cannot decrease the result.

## Regression
Every confirmed business rule or discovered bug should become a regression test.

## Synthetic Data
Synthetic records may be used for edge cases. Mark them as `DATA_ORIGIN = SYNTHETIC` and never present them as company history.

## Historical Validation
When populated historical `SemTheorique` data is available:
- calculate row by row;
- compare;
- classify discrepancies;
- measure match rate;
- investigate systematic differences.

## Acceptance
Do not claim business correctness without automated tests, reproducible execution, documented assumptions, and historical validation where real reference results exist.
