# Simulator Specification

## Goal
Create a small, understandable simulator that calculates the theoretical production week for each POI.

## Input
The simulator consumes the canonical dataset.

## Output
For each POI:

```text
POI
DateTheorique
SemTheorique
BlockingElement
CalculationStatus
QualityFlags
```

## Calculation Contract

```text
determine_required_components(poi)
        |
determine_component_availability(poi)
        |
validate required components
        |
        +--> incomplete / invalid
        |
MAX(applicable availability dates)
        |
DateTheorique
        |
week conversion
        |
SemTheorique
```

## Missing Data
Never replace NULL with an arbitrary date.

- Not required → ignore.
- Required but unavailable → incomplete/unavailable.
- Applicability unknown → unknown state.
- Invalid date → invalid/quality flag.

## Blocking Element
Return all components whose availability date equals `DateTheorique` unless a company-confirmed tie-break rule exists.

## Week Representation
Internally retain `iso_year`, `iso_week`, and `week_key`. The company-specific week convention must be validated before claiming historical equivalence.

## Explainability
The result should expose the component dates used in the calculation.

## Implementation Order
1. Pure calculation functions
2. Unit tests
3. Canonical-data adapter
4. Local batch simulator
5. Simple API/UI
6. Benchmark
7. Optimization
8. Hadoop prototype

## Current Limitation
The supplied POI extract cannot validate the final simulator because its historical target and several core input dates are entirely NULL.
