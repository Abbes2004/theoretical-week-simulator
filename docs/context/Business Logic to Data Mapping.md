# Business Logic to Data Mapping

## 1. Purpose

This document maps the business concepts required by the theoretical production week simulator to the data fields currently available in the project datasets.

The objective is to answer:

> Where can each business concept be found in the available data?

The mapping distinguishes between:

- **Confirmed mapping**
- **Observed mapping**
- **Candidate mapping**
- **Unknown / requires validation**

No field should be used as a business rule solely because its name appears relevant.

---

# 2. Business Process

The target business process is:

```text
POI
 │
 ├── Main fabric
 ├── Secondary fabric
 ├── Supplies
 ├── Thread
 └── OK Production
        │
        ▼
 Component availability
        │
        ▼
 Latest availability
        │
        ▼
 Theoretical production week
```

The main output is:

```text
SemTheorique
```

---

# 3. Business Concept Mapping

| Business concept | Candidate data | Confidence |
|---|---|---|
| Simulation | `plan_t_simplanif` | Confirmed |
| POI | `plan_t_simplanifpoi` | Confirmed |
| Main fabric availability | `DateTissu` | Observed / candidate |
| Secondary fabric availability | `DateTissuSec` | Observed / candidate |
| Supply availability | `DateFourniture` | Observed / candidate |
| Thread availability | `DateFil` | Observed / candidate |
| Production approval | `DateOKProduction` | Observed / candidate |
| Latest component date | `DateMax` | Strong candidate |
| Theoretical production week | `SemTheorique` | Confirmed |
| Component status | `Etat*`, `Statut*` | To validate |
| Availability indicator | `Ind*` | To validate |
| Required fabric quantity | `BesoinTissu` | Strong candidate |
| Stock quantity | `Qte` | Strong candidate |
| Blocking component | Not explicitly stored as a single field | Must be derived |

---

# 4. Simulation

## Business concept

A simulation represents a planning/calculation context in which POIs are evaluated.

## Data mapping

Primary table:

```text id="x7qk1m"
plan_t_simplanif
```

Identifier:

```text id="q5s2e8"
Id_Sim
```

## Usage

`Id_Sim` can be used to:

- identify a simulation;
- group POIs;
- group simulation-related stock records;
- preserve simulation context in outputs.

---

# 5. POI

## Business concept

The POI is the main unit for the theoretical availability calculation.

## Data mapping

Table:

```text id="f5m9z2"
plan_t_simplanifpoi
```

Identifiers:

```text id="u8k3q1"
Id_SimPoi
Id_Sim
POI_Sim
```

The final simulator should preserve:

```text id="2v7p4x"
(Id_Sim, POI_Sim)
```

as the business-level identification of the simulated POI.

---

# 6. Main Fabric

## Business concept

The production order requires a main fabric.

The simulator needs to determine when this fabric is available.

## Candidate fields

```text id="5z8m1k"
BesoinTissu
DateTissu
DispTissu
EtatTissu
tauxDispTissu
IndTissu
```

## Current interpretation

```text id="6c4q9v"
BesoinTissu
    ↓
Fabric requirement

DispTissu / tauxDispTissu / EtatTissu
    ↓
Fabric availability information

DateTissu
    ↓
Candidate final availability date
```

## Status

The existence of these fields is confirmed.

The exact calculation of `DateTissu` is **not yet confirmed**.

---

# 7. Secondary Fabric

## Business concept

Some POIs may require a secondary fabric.

## Candidate fields

```text id="8r2n5j"
DateTissuSec
StatutTissuSec
EtatTissuSec
tauxDispTissuSec
IndTissuSec
```

## Required validation

The simulator must determine:

1. whether the POI requires secondary fabric;
2. how its availability is calculated;
3. whether a missing `DateTissuSec` means:
   - not applicable;
   - unavailable;
   - missing data;
   - another status.

Therefore:

```text id="j3x6w8"
DateTissuSec
```

cannot be interpreted independently from the applicability/status information.

---

# 8. Supplies / Accessories

## Business concept

Accessories or supplies required by the POI must be available before production.

## Candidate fields

In the POI table:

```text id="p8y2m4"
DateFourniture
LastFourniture
StatutFourniture
EtatFourniture
IndFourniture
```

There is also a separate source:

```text id="n6k4q9"
plan_t_simplaniffourniture
```

with fields including:

```text id="3s8v1x"
POI
TypeFourniture
Besoin
DateAccesoire
EtatAccessoire
tauxDisp
PrevStock
QteResev
NCde
DateBesoin
```

## Candidate process

```text id="h2m7z5"
POI
   ↓
Required accessories
   ↓
Availability calculation
   ↓
DateFourniture
```

The exact aggregation and join logic must be validated.

---

# 9. Sewing Thread

## Business concept

Sewing thread must be available before production.

## Candidate fields

```text id="t7v3p1"
DateFil
LastFil
StatutFil
EtatFil
IndFil
```

The main candidate output is:

```text id="m9q4x6"
DateFil
```

The exact source and calculation of this date remain unknown.

---

# 10. OK Production

## Business concept

The production process has a technical/business approval represented as:

```text id="a6k2w9"
OK Production
```

## Candidate fields

```text id="c3n8r5"
DateOKProduction
EtatOkProduction
StatutOkProduction
IndOkProd
```

The candidate availability date is:

```text id="p4z7y2"
DateOKProduction
```

The exact meaning and triggering event of this date must be confirmed with the company process.

---

# 11. Latest Availability

The business rule states that the theoretical production availability is determined by the latest required component.

Candidate fields:

```text id="v6m2q8"
DateMax
SemTheorique
```

Conceptually:

```text id="r4x9k1"
DateTissu
DateTissuSec
DateFourniture
DateFil
DateOKProduction
          │
          ▼
       MAX date
          │
          ▼
       DateMax
          │
          ▼
      SemTheorique
```

This is the target logic to validate.

---

# 12. Theoretical Week

## Business concept

The final output is:

```text id="d7w3p5"
SemTheorique
```

It represents the theoretical production week.

The expected calculation is:

```text id="m5k8q2"
SemTheorique =
Week(
    max(
        applicable component availability dates
    )
)
```

The exact date-to-week convention remains to be validated.

---

# 13. Blocking Component

There is no confirmed dedicated field representing the blocking component.

Therefore, it should initially be derived.

Example:

```text id="k9p3v6"
DateTissu        = 2025-08-04
DateTissuSec     = 2025-08-05
DateFourniture   = 2025-08-03
DateFil          = 2025-08-02
DateOKProduction = 2025-08-06
```

Then:

```text id="w2x7m4"
DateMax = 2025-08-06
BlockingElement = OK Production
```

If several elements have the same maximum date:

```text id="n5q8z1"
BlockingElement =
    all components with Date = DateMax
```

unless the company confirms another tie-breaking rule.

---

# 14. Availability Status

The POI table contains several status/state fields:

```text id="b8m2x5"
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

These may explain whether a component is:

- available;
- unavailable;
- pending;
- validated;
- blocked;
- not applicable.

However, their exact allowed values and business meaning must be profiled and validated.

---

# 15. Availability Indicators

The dataset also contains:

```text id="q6v9p3"
IndTissu
IndTissuSec
IndFourniture
IndFil
IndOkProd
IndSemPiq
```

These fields may represent binary or categorical indicators.

Before using them in the simulator, determine:

- possible values;
- meaning of each value;
- whether `1` means available;
- whether `0` means unavailable;
- whether NULL has a specific meaning;
- whether the indicator is derived from the date/status.

No assumption should be made from the numeric value alone.

---

# 16. Quantity → Availability

Potential data:

```text id="c7x4m9"
POI
 │
 ├── BesoinTissu
 │
 └── Qte from stock
```

Possible conceptual relationship:

```text id="z2p6v8"
Requirement
    +
Available quantity
    ↓
Availability
    ↓
Availability date
```

But this remains a hypothesis.

The simulator must not use:

```text id="a9k3w5"
Qte >= BesoinTissu
```

as the final business rule until validated.

---

# 17. Historical Result Validation

The following fields can be compared:

```text id="u5m8q2"
Historical:
    SemTheorique

Derived:
    Week(max(component dates))
```

For each valid POI:

```text id="n4x7p1"
Historical SemTheorique
          vs
Calculated SemTheorique
```

Possible outcomes:

```text id="j8c3v6"
MATCH
MISMATCH
INSUFFICIENT_DATA
NOT_APPLICABLE
```

This validation will help determine whether the reconstructed business logic matches the historical system behavior.

---

# 18. Data Mapping Matrix

The current mapping can be summarized as:

| Business rule | Data fields | Status |
|---|---|---|
| Identify simulation | `Id_Sim` | Confirmed |
| Identify POI | `Id_Sim`, `POI_Sim` | Confirmed |
| Main fabric availability | `DateTissu` | Candidate |
| Secondary fabric availability | `DateTissuSec` | Candidate |
| Supply availability | `DateFourniture` | Candidate |
| Thread availability | `DateFil` | Candidate |
| Production approval | `DateOKProduction` | Candidate |
| Latest availability | `DateMax` | Strong candidate |
| Theoretical week | `SemTheorique` | Confirmed |
| Blocking component | Derived | Candidate |
| Quantity requirement | `BesoinTissu` | Candidate |
| Stock quantity | `Qte` | Candidate |
| Component status | `Etat*`, `Statut*` | To validate |
| Component indicators | `Ind*` | To validate |

---

# 19. Minimum Data Required for a Baseline

Before attempting to reconstruct all underlying business calculations, a minimal baseline can operate on:

```text id="r7m2x9"
Id_Sim
POI_Sim

DateTissu
DateTissuSec
DateFourniture
DateFil
DateOKProduction
```

with:

```text id="v3q8k5"
SemTheorique
```

used as a historical reference.

This baseline is useful for validating the theoretical-week formula independently.

It does **not** replace the later investigation of how each component date is generated.

---

# 20. Full Reconstruction Target

The long-term target is:

```text id="w5n8q3"
Raw operational data
        ↓
Component-specific processing
        ↓
DateTissu
DateTissuSec
DateFourniture
DateFil
DateOKProduction
        ↓
DateMax
        ↓
SemTheorique
```

The project should progressively move from the minimal baseline toward this reconstructed pipeline.

---

# 21. Implementation Principle

The simulator should separate:

### Input data

```text
POI
Component source data
Stock
Orders
Receptions
Statuses
Quantities
```

### Derived data

```text
Component availability dates
DateMax
BlockingElement
SemTheorique
```

This separation is important for:

- debugging;
- validation;
- benchmarking;
- explaining results;
- comparing the baseline with the Hadoop implementation.

---

# 22. Open Mapping Questions

Before finalizing the business implementation, answer:

1. How exactly is `DateTissu` calculated?
2. How exactly is `DateTissuSec` calculated?
3. How exactly is `DateFourniture` calculated?
4. How exactly is `DateFil` calculated?
5. How exactly is `DateOKProduction` calculated?
6. Which components are mandatory for each POI?
7. How are stock quantities allocated?
8. How are purchase orders linked to POIs?
9. How are receptions linked to availability?
10. How are substitutions handled?
11. What is the precedence between automatic and manual dates?
12. What calendar convention is used for `SemTheorique`?
13. What happens when a required component has no valid date?
14. How are ties between blocking components handled?

These questions should be resolved before considering the business logic fully reconstructed.