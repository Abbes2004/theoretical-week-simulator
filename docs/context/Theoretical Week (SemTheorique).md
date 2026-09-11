# 08 — Theoretical Week (`SemTheorique`)

## 1. Purpose

This document defines the role of `SemTheorique` in the theoretical production-week simulator.

`SemTheorique` represents the theoretical production week calculated for a Production Order Item (POI), based on the availability of all required production elements.

The simulator must reproduce this business concept using the available historical data while keeping the calculation efficient and auditable.

---

## 2. Target Grain

The expected calculation grain is:

> **One theoretical result per POI.**

A POI is identified in the simulation data by the combination:

```text
Id_Sim + POI_Sim
```

The main source table for this target is:

```text
plan_t_simplanifpoi
```

because it already contains:

```text
SemTheorique
```

as a historical/reference result.

---

## 3. Required Production Elements

According to the project specification, production can only start when all required elements are available.

The main elements are:

1. Main fabric (`Tissu`)
2. Secondary fabric (`Tissu secondaire`)
3. Accessories / supplies (`Fourniture`)
4. Sewing thread (`Fil`)
5. Production approval (`OK Production`)

Conceptually:

```text
             Main Fabric
                  │
         Secondary Fabric
                  │
             Fourniture
                  │
                 Fil
                  │
             OK Production
                  │
                  ▼
        Theoretical Production Date
                  │
                  ▼
        Theoretical Production Week
```

---

## 4. Core Business Rule

The confirmed business rule is:

> The theoretical production date is determined by the latest availability date among all required elements.

Therefore:

```text
DateTheorique =
MAX(
    DateTissu,
    DateTissuSec,
    DateFourniture,
    DateFil,
    DateOKProduction
)
```

The corresponding theoretical week is then derived from this theoretical date.

Conceptually:

```text
SemTheorique = Week(DateTheorique)
```

The exact week-numbering convention must still be validated against the company's historical data.

---

## 5. Blocking Element

The element associated with the latest availability date is the **blocking element**.

Example:

```text
DateTissu        = 2025-08-04
DateTissuSec     = 2025-08-05
DateFourniture   = 2025-08-03
DateFil          = 2025-08-04
DateOKProduction = 2025-08-08
```

Then:

```text
DateTheorique = 2025-08-08
SemTheorique  = week corresponding to 2025-08-08
```

The blocking element is:

```text
OK Production
```

because it has the latest availability date.

---

## 6. Mapping to Available Columns

The POI table contains the following candidate date fields:

| Business element | POI column | Role |
|---|---|---|
| Main fabric | `DateTissu` | Candidate availability date |
| Secondary fabric | `DateTissuSec` | Candidate availability date |
| Accessories | `DateFourniture` | Candidate availability date |
| Sewing thread | `DateFil` | Candidate availability date |
| Production approval | `DateOKProduction` | Candidate availability date |
| Theoretical date | `DateMax` | Historical/calculated candidate |
| Theoretical week | `SemTheorique` | Historical/reference result |

The following fields may help interpret the state of each component:

```text
EtatTissu
EtatTissuSec
EtatFourniture
EtatFil
EtatOkProduction

StatutTissuSec
StatutFourniture
StatutFil
StatutOkProduction
```

There are also indicators:

```text
IndTissu
IndTissuSec
IndFourniture
IndFil
IndOkProd
```

These fields must be investigated before using them as filtering rules in the simulator.

---

## 7. Important Distinction: Historical Result vs Calculation Rule

The existing value:

```text
SemTheorique
```

must initially be considered a **historical/reference result**.

Its existence does not by itself prove how the original system calculated it.

Similarly:

```text
DateMax
```

should not automatically be assumed to be equivalent to:

```text
MAX(DateTissu, DateTissuSec, DateFourniture, DateFil, DateOKProduction)
```

without validation.

The project should therefore distinguish between:

### Confirmed

- `SemTheorique` is a relevant historical target.
- Production depends on the availability of the required elements.
- The latest required availability determines the theoretical production date/week.

### Observed in the dataset

- The POI table contains component-specific dates.
- The POI table contains `DateMax`.
- The POI table contains `SemTheorique`.
- The POI table contains component status and indicator fields.

### Still to validate

- Whether every component date is directly usable in the formula.
- Whether component indicators determine whether a component is required.
- How missing dates are treated.
- How invalid dates are treated.
- How weeks are calculated.
- How ties between blocking elements are handled.
- Whether `DateMax` corresponds exactly to the calculated maximum.

---

## 8. Missing Availability

A POI may contain missing values for one or more component dates.

The simulator must **not silently convert missing availability into an arbitrary date**.

For example:

```text
DateTissu        = 2025-08-04
DateTissuSec     = NULL
DateFourniture   = 2025-08-03
DateFil          = 2025-08-04
DateOKProduction = 2025-08-05
```

It is not yet confirmed whether:

```text
NULL
```

means:

- the component is not required,
- the component is required but not yet available,
- the information is missing,
- the component calculation failed,
- or another business state.

Therefore, this case must be explicitly investigated before implementation.

---

## 9. Component Requirement vs Component Availability

A critical distinction must be maintained:

```text
Component required
        ≠
Component available
```

For example, a POI may not require secondary fabric.

In that case:

```text
DateTissuSec = NULL
```

may be perfectly valid.

Conversely, if secondary fabric is required but its availability date is missing, the POI may not be ready for production.

The simulator must therefore determine, from validated business rules, whether a component is:

```text
NOT_REQUIRED
```

or:

```text
REQUIRED_BUT_UNAVAILABLE
```

before applying the `MAX()` operation.

---

## 10. Proposed Logical Calculation

After the requirement rules are validated, the calculation can conceptually follow:

```text
For each POI:

    required_elements = determine_required_elements(POI)

    availability_dates = []

    for each required element:
        date = determine_availability(element)

        if date is unavailable:
            mark POI as incomplete/unavailable

        else:
            availability_dates.append(date)

    if all required elements are available:

        DateTheorique = MAX(availability_dates)

        SemTheorique = convert_to_week(DateTheorique)

        BlockingElement =
            element corresponding to DateTheorique
```

This is the logical baseline.

The exact implementation should only be finalized after validating the underlying business rules.

---

## 11. Validation Against Historical Data

The historical `SemTheorique` provides an important validation target.

For each POI where the necessary information is available:

```text
Calculated SemTheorique
            vs
Historical SemTheorique
```

can be compared.

A validation dataset can contain:

| Id_Sim | POI_Sim | Calculated Week | Historical Week | Match |
|---:|---|---:|---:|---|
| ... | ... | ... | ... | TRUE/FALSE |

The objective is not initially to force a 100% match.

If discrepancies appear, they should be investigated.

Possible explanations include:

- missing business rules,
- component requirement rules,
- different week conventions,
- manual modifications,
- historical corrections,
- incomplete source data,
- dates calculated by another process.

---

## 12. Validation Metrics

The baseline simulator should measure at least:

```text
Number of POIs evaluated
Number of POIs with complete information
Number of POIs with missing information
Number of valid calculated results
Number of discrepancies
Number of exact matches
Match rate
```

The main validation indicator can be:

```text
Match Rate =
Number of matching historical results
-------------------------------------
Number of comparable POIs
```

This gives an objective measure of how closely the reconstructed logic reproduces historical results.

---

## 13. Blocking Element Analysis

The simulator should ideally return not only:

```text
SemTheorique
```

but also:

```text
DateTheorique
BlockingElement
```

Example output:

```text
POI = 01028122582CD

DateTheorique = 2025-08-11
SemTheorique = 2025-W32
BlockingElement = Tissu
```

This makes the simulator explainable.

It also enables later performance/business analysis such as:

```text
Tissu          → 42%
Fourniture     → 27%
Fil            → 15%
TissuSec       → 10%
OK Production  → 6%
```

These percentages are only examples; actual values must be calculated from the data.

---

## 14. Tie Handling

A special case occurs when two or more elements have the same latest availability date.

Example:

```text
DateTissu        = 2025-08-08
DateTissuSec     = 2025-08-08
DateFourniture   = 2025-08-06
DateFil          = 2025-08-07
DateOKProduction = 2025-08-08
```

The theoretical date is clearly:

```text
2025-08-08
```

but the blocking element is ambiguous.

The business rule for this case is not yet confirmed.

The simulator should therefore preserve all tied blocking elements until the business rule is validated, rather than arbitrarily selecting one.

Possible representation:

```text
BlockingElement = ["Tissu", "TissuSec", "OK Production"]
```

---

## 15. Week Conversion

The conversion:

```text
DateTheorique → SemTheorique
```

must be treated as a separate business rule.

The project should validate:

- ISO week or company-specific week numbering
- year boundary behavior
- first/last week of the year
- whether the company uses calendar week or production week
- whether `SemTheorique` stores only a week number or a year-week representation

This is particularly important around:

```text
December → January
```

because a calendar date can belong to an ISO week associated with a different year.

---

## 16. Performance Considerations

The theoretical-week calculation itself should remain simple:

```text
read data
    ↓
join required information
    ↓
determine required components
    ↓
calculate component availability
    ↓
MAX()
    ↓
week conversion
    ↓
result
```

The likely performance bottlenecks should therefore be investigated around:

- reading large datasets,
- joins,
- repeated lookups,
- aggregation,
- unnecessary data movement,
- repeated calculations,
- Python loops,
- database access patterns.

The project should benchmark the complete pipeline rather than assuming that the `MAX()` calculation itself is expensive.

---

## 17. Baseline Before Optimization

The first implementation should prioritize:

1. Correctness
2. Traceability
3. Validation
4. Measurement

Only after the baseline is validated should optimization begin.

The baseline will later provide the reference for:

```text
Baseline
   ↓
Optimized local version
   ↓
Hadoop MapReduce version
```

This allows the project to demonstrate whether distributed processing actually improves execution time.

---

## 18. Current Open Questions

Before finalizing the simulator, the following questions must be answered:

1. How is `DateTissu` calculated?
2. How is `DateTissuSec` calculated?
3. How is `DateFourniture` calculated?
4. How is `DateFil` calculated?
5. How is `DateOKProduction` calculated?
6. How is it determined that a component is required?
7. What do the `Ind*` fields represent?
8. What do the `Etat*` and `Statut*` fields represent?
9. How should a required component with no availability date be handled?
10. Does `DateMax` equal the maximum of the component dates?
11. How is `SemTheorique` derived from `DateMax`?
12. What is the official company week-numbering convention?
13. What is the business rule when several components have the same maximum date?
14. Are historical `SemTheorique` values sometimes manually modified?
15. Which source tables are required to independently reconstruct each component availability date?

---

## 19. Final Principle

The simulator should not be designed around the assumption:

```text
SemTheorique = simply MAX(all date columns)
```

Instead, the correct conceptual model is:

```text
Business requirements
        ↓
Determine required components
        ↓
Determine availability of each required component
        ↓
Find latest availability
        ↓
Determine theoretical production date
        ↓
Convert date to production week
        ↓
Identify blocking element
        ↓
Validate against historical SemTheorique
```

This separation is essential because the project objective is not only to calculate a number, but to reconstruct a **correct, explainable, measurable, and efficient simulation process**.