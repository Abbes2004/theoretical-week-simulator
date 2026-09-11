# Business Rules

## 1. Purpose

This document defines the business rules relevant to the theoretical production week simulator.

The purpose is to distinguish:

- **Confirmed business rules**: explicitly supported by the project specification.
- **Data observations**: information observed in the available database structure.
- **Hypotheses**: possible interpretations that still require validation.
- **Open points**: rules that must be clarified before being implemented.

No unvalidated business rule must be silently introduced into the simulator.

---

## 2. Main Business Objective

The simulator must determine the **theoretical production week (`SemTheorique`)** for a Production Order Item (POI).

Production can theoretically start only when all required production elements are available.

The main elements identified in the project specification are:

1. Main fabric (`Tissu`)
2. Secondary fabric (`Tissu secondaire`)
3. Accessories / supplies (`Fourniture`)
4. Sewing thread (`Fil`)
5. Production technical approval (`OK Production`)

The simulator must therefore determine the latest availability among these elements.

---

## 3. Main Business Rule

The confirmed conceptual rule is:

```text
SemTheorique =
    max(
        Week(Tissu principal),
        Week(Tissu secondaire),
        Week(Fourniture),
        Week(Fil),
        Week(OK Production)
    )
```

In other words:

> The theoretical production week is determined by the latest required element to become available.

Example:

| Element | Availability week |
|---|---:|
| Main fabric | 32 |
| Secondary fabric | 33 |
| Accessories | 31 |
| Thread | 32 |
| OK Production | 34 |

Therefore:

```text
SemTheorique = 34
```

The blocking element is:

```text
OK Production
```

---

## 4. Blocking Element

The simulator should identify the element responsible for the theoretical production date.

Conceptually:

```text
Blocking element = element with the latest availability
```

Example:

```text
Tissu          → Week 32
Tissu secondaire → Week 33
Fourniture     → Week 31
Fil            → Week 32
OK Production  → Week 34

Blocking element → OK Production
```

### Tie case

If several elements have exactly the same latest availability week, they may all be considered blocking elements.

Example:

```text
Tissu        → Week 34
Fourniture   → Week 34
Fil          → Week 32
OK Production → Week 33
```

Possible result:

```text
SemTheorique = 34
Blocking elements = Tissu + Fourniture
```

The official tie-breaking rule, if one exists, has not yet been validated.

The implementation must therefore **not invent a priority between tied elements** without confirmation.

---

## 5. Production Cannot Start Before All Required Elements Are Available

The business logic implies:

```text
Production start
        ↓
All required elements available
        ↓
Theoretical production week
```

A POI cannot theoretically be considered ready if one required element is still unavailable.

Therefore:

```text
If at least one required element
has an availability later than the others:

    SemTheorique = latest availability
```

---

## 6. Component Availability Dates

The POI dataset contains fields corresponding to the different production elements.

Observed fields include:

```text
DateTissu
DateTissuSec
DateFourniture
DateFil
DateOKProduction
```

These fields are candidates for representing the availability date of the corresponding elements.

The conceptual mapping is:

| Business element | Observed POI field |
|---|---|
| Main fabric | `DateTissu` |
| Secondary fabric | `DateTissuSec` |
| Accessories | `DateFourniture` |
| Thread | `DateFil` |
| OK Production | `DateOKProduction` |

### Important

The presence of these columns does **not yet prove** exactly how each date is calculated.

The following points still require validation:

- source of each date;
- calculation method;
- relationship with stock;
- relationship with purchase orders;
- relationship with receptions;
- quantity requirements;
- substitutions;
- whether the date represents availability, reception, validation, or another business event.

Until validated, these mechanisms must be treated as **hypotheses**.

---

## 7. Historical `SemTheorique`

The field:

```text
SemTheorique
```

exists in the POI dataset.

It can be used as a historical/reference result for validation.

However:

> A historical `SemTheorique` value is an observed output and must not automatically be considered proof of the exact formula used to calculate it.

The new simulator must reconstruct and validate the business logic independently.

Validation should compare:

```text
Simulator result
        vs
Historical/reference result
```

whenever the historical result is reliable and applicable.

---

## 8. Date-to-Week Conversion

The final business output is a **theoretical week**, while the component information is represented by dates.

Therefore, the simulator must convert component availability dates into production weeks.

Conceptually:

```text
Availability dates
        ↓
Date → Week conversion
        ↓
Latest week
        ↓
SemTheorique
```

The exact calendar convention must be validated before implementation, especially regarding:

- ISO week numbering;
- year transitions;
- dates around the beginning/end of a year;
- whether the company uses a custom production-week calendar.

The simulator must not assume a custom calendar without evidence.

---

## 9. Missing Availability

The project specification explicitly considers incomplete or unavailable data as an important case.

Examples:

```text
DateTissu = NULL
DateTissuSec = valid
DateFourniture = valid
DateFil = valid
DateOKProduction = valid
```

The simulator must detect that the POI is incomplete rather than silently producing an incorrect result.

However, the exact operational behavior for every missing component still needs validation.

Possible business outcomes that must be clarified include:

- mark the POI as unavailable;
- return an error/status;
- exclude the POI from simulation;
- use another source of information;
- consider the missing element as blocking.

The implementation must follow the confirmed company rule once validated.

---

## 10. Invalid or Corrupted Data

The project specification also identifies problematic data cases such as:

- invalid dates;
- incomplete PO/POI information;
- missing availability information;
- data outside the study period.

The simulator should therefore include a validation layer before applying the business calculation.

Conceptually:

```text
Raw data
   ↓
Data validation
   ↓
Valid data → Business calculation
Invalid data → Error / status / exclusion
```

The exact treatment of each invalid-data case must be documented before implementation.

---

## 11. POI Scope

The calculation is fundamentally performed at the **POI level**.

The POI table contains:

```text
Id_SimPoi
Id_Sim
POI_Sim
```

There is also a uniqueness constraint on:

```text
(Id_Sim, POI_Sim)
```

This indicates that a POI belongs to a simulation and can be identified within that simulation.

The exact business definition of a POI and its relationship with the production order must still be validated.

---

## 12. Required Elements vs Optional Elements

The specification identifies the following five elements as relevant to theoretical production availability:

```text
Tissu
Tissu secondaire
Fourniture
Fil
OK Production
```

However, the simulator must distinguish between:

- an element that is genuinely **required** for a particular POI;
- an element that is not applicable to that POI.

This distinction is important.

For example, if a POI does not require a secondary fabric, the absence of `DateTissuSec` should not automatically mean that the POI is blocked.

The exact applicability rules for each component must therefore be validated.

---

## 13. Stock and Quantity

The dataset contains stock information, including:

```text
Qte
Code_Sim
Taille_Sim
Date_Sim
Client
```

The POI dataset also contains fields such as:

```text
BesoinTissu
DispTissu
tauxDispTissu
```

These fields suggest that quantities and availability levels may participate in determining component availability.

However:

> The exact stock-consumption and quantity-allocation rules are not yet confirmed.

Therefore, the simulator must not assume a simple rule such as:

```text
Qte >= BesoinTissu
```

without validating how the company actually determines availability.

---

## 14. Business Logic Pipeline

The business logic can currently be represented as:

```text
POI
 │
 ├── Determine required components
 │
 ├── Determine availability of each component
 │
 ├── Validate dates and data
 │
 ├── Convert availability dates to weeks
 │
 ├── Find latest required week
 │
 └── Identify blocking component(s)
          │
          ▼
     SemTheorique
```

---

## 15. Confirmed vs Unconfirmed Rules

### Confirmed

- The simulator concerns theoretical production availability.
- The calculation involves the main fabric, secondary fabric, accessories, sewing thread and OK Production.
- Production requires the necessary elements to be available.
- The theoretical result is determined by the latest required availability.
- `SemTheorique` is the theoretical production week.
- Missing/incomplete/invalid data are relevant cases that must be handled.
- The system should identify the blocking element.

### Observed in the data

- `DateTissu`
- `DateTissuSec`
- `DateFourniture`
- `DateFil`
- `DateOKProduction`
- `SemTheorique`
- `Etat*` fields
- `Statut*` fields
- `Ind*` indicators
- stock and quantity-related fields

### Not yet confirmed

- Exact calculation of every component availability date.
- Exact POI ↔ stock relationship.
- Exact POI ↔ purchase-order relationship.
- Quantity allocation rules.
- Treatment of substitutions.
- Applicability of each component to each POI.
- Exact date-to-week calendar convention.
- Exact treatment of missing component dates.
- Exact tie-breaking rule for multiple blocking components.
- Exact interpretation of every `Etat*`, `Statut*`, and `Ind*` field.

---

## 16. Rule for Implementation

The development team must follow this principle:

> **Never convert an assumption into a business rule without validation.**

Every business rule used in the simulator must be classified as one of:

```text
CONFIRMED
OBSERVED
INFERRED
HYPOTHESIS
RECOMMENDATION
```

The source and justification of important rules should be documented.

---

## 17. Current Business Logic Target

The first validated version of the simulator should aim to implement:

```text
For each POI:

1. Identify required components.
2. Obtain their validated availability dates.
3. Validate the dates and component applicability.
4. Convert valid dates to production weeks.
5. Compute the maximum week.
6. Identify the blocking component(s).
7. Return SemTheorique and its status.
```

The exact implementation of steps 1–3 depends on the remaining business/data validation work.