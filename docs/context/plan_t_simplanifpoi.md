# SQL Reference — `plan_t_simplanifpoi`

## 1. Document Purpose

This document is a technical reference for:

`plan_t_simplanifpoi.sql`

It documents the structure, grain, constraints, important fields, and directly observable characteristics of the `plan_t_simplanifpoi` table.

> **IMPORTANT**
>
> This document is derived documentation of the raw SQL source.
>
> The raw SQL file remains the authoritative source whenever exact schema, values, relationships, or data-level evidence are required.

---

# 2. Source Information

| Property | Value |
|---|---|
| Database | `production` |
| Table | `plan_t_simplanifpoi` |
| Storage engine | InnoDB |
| Primary key | `Id_SimPoi` |
| Unique constraint | `(Id_Sim, POI_Sim)` |
| Auto-increment | Present |
| Main role | POI / simulation-detail information |

The SQL dump was generated from the `production` database.

**CONFIRMED BY SQL.**

---

# 3. Table Role

`plan_t_simplanifpoi` is the **POI-level/detail table** associated with simulations.

It contains information about:

- POIs;
- simulation priority;
- fabric requirements and availability;
- secondary fabric;
- supplies/accessories;
- sewing thread;
- treatment / finishing information;
- technical production validation;
- theoretical dates;
- theoretical weeks;
- component indicators;
- POI decisions and validation;
- various historical/manual dates.

Most importantly, the table contains:

```text
SemTheorique
```

which makes this table central to the theoretical-week simulator.

---

# 4. Table Grain

The table has the following uniqueness constraint:

```text
UNIQUE (Id_Sim, POI_Sim)
```

Therefore, the intended logical grain is:

```text
One POI within one simulation
```

A POI is identified by the combination:

```text
(Id_Sim, POI_Sim)
```

The technical primary key is:

```text
Id_SimPoi
```

**CONFIRMED BY SQL.**

---

# 5. Constraints and Indexes

## Primary Key

```text
PRIMARY KEY (Id_SimPoi)
```

## Unique Key

```text
UNIQUE KEY (Id_Sim, POI_Sim)
```

## Indexes

The table contains indexes supporting access through fields including:

```text
Id_Sim
POI_Sim
(Id_Sim, Priorite_Sim, NonPlanif_Sim)
DateTissu
```

These indexes are relevant when querying POIs by simulation, priority, planning state, or fabric date.

**CONFIRMED BY SQL.**

---

# 6. Complete Column Reference

## 6.1 Identification and Planning

| Column | Role |
|---|---|
| `Id_SimPoi` | Technical row identifier |
| `Id_Sim` | Simulation identifier |
| `POI_Sim` | POI identifier |
| `Priorite_Sim` | POI priority |
| `NonPlanif_Sim` | Non-planned indicator/state |

---

## 6.2 Main Fabric

| Column | Role |
|---|---|
| `BesoinTissu` | Fabric requirement |
| `DateTissu` | Fabric availability/date |
| `DispTissu` | Fabric availability quantity/state |
| `EtatTissu` | Fabric status |
| `tauxDispTissu` | Fabric availability rate |

These fields describe the fabric-related availability information associated with the POI.

**CONFIRMED BY SQL as column names and stored fields.**

The exact calculation of `DateTissu` must be validated from the application/business logic.

---

# 7. Secondary Fabric

| Column | Role |
|---|---|
| `DateTissuSec` | Secondary-fabric date |
| `StatutTissuSec` | Secondary-fabric status |
| `EtatTissuSec` | Secondary-fabric state |
| `tauxDispTissuSec` | Secondary-fabric availability rate |

The presence of these fields confirms that secondary-fabric information is stored separately from the main fabric.

**UNKNOWN:** the exact algorithm used to calculate `DateTissuSec`.

---

# 8. Supplies / Accessories

| Column | Role |
|---|---|
| `DateFourniture` | Supply/accessory availability date |
| `LastFourniture` | Last supply/accessory date |
| `StatutFourniture` | Supply/accessory status |
| `EtatFourniture` | Supply/accessory state |

These fields are explicitly stored in the POI table.

**UNKNOWN:** whether `DateFourniture` is calculated directly from stock, purchase orders, receptions, or another process.

---

# 9. Sewing Thread

| Column | Role |
|---|---|
| `DateFil` | Thread availability date |
| `LastFil` | Last thread date |
| `StatutFil` | Thread status |
| `EtatFil` | Thread state |

The table therefore explicitly models sewing-thread availability separately.

The exact calculation of `DateFil` is **NOT confirmed by the schema alone**.

---

# 10. Treatment / Production Process

The table contains:

```text
DateTraitementSP
LastTraitementSP
EtapeFH
```

These fields indicate that treatment/process information is represented at POI level.

The exact business meaning and contribution of these fields to `SemTheorique` must be validated.

---

# 11. OK Production

The table contains:

```text
DateOKProduction
EtatOkProduction
StatutOkProduction
```

These fields represent the technical production approval/status information stored for the POI.

For the simulator, `DateOKProduction` is particularly important because the project business logic identifies technical production approval as one of the required elements.

**CONFIRMED:** the field exists.

**NOT YET CONFIRMED:** the precise business rule used to calculate or assign this date.

---

# 12. Theoretical Date and Week

The most important fields for the project are:

```text
DateMax
StatutDateTheo
SemTheorique
SemTheoriqueCoupe
```

### `DateMax`

A date field associated with the theoretical calculation.

### `StatutDateTheo`

Status associated with the theoretical date.

### `SemTheorique`

Stored theoretical production week.

### `SemTheoriqueCoupe`

Stored theoretical cutting week.

The presence of these fields makes `plan_t_simplanifpoi` the primary source for studying the existing theoretical-week result.

---

# 13. Component Indicators

The table contains:

```text
IndTissu
IndTissuSec
IndFourniture
IndFil
IndOkProd
IndSemPiq
```

These indicators correspond to the different availability/production components represented in the table.

A conceptual mapping is:

```text
IndTissu        → Main fabric
IndTissuSec     → Secondary fabric
IndFourniture   → Supplies/accessories
IndFil          → Thread
IndOkProd       → Production approval
IndSemPiq       → Sewing/production week indicator
```

This mapping is based on the field names and project context.

The exact numerical semantics of each indicator must be validated from actual records and/or application logic.

---

# 14. Other Important Fields

## Root / Simulation Relationship

```text
IdSim_Racine
Priorite_Racine
```

These fields indicate that simulations/POIs may have a relationship with a root simulation or root priority.

The exact business rule is not established from the schema alone.

---

## Decision Fields

```text
DecisionPOI
SrvFautifRet
MotifDecision
CommentaireDecision
```

These fields contain decision and diagnostic information associated with a POI.

They may be useful for understanding exceptional or manually corrected cases.

---

## Validation

```text
ValidationPOI
Dat_Valid
User_Valid
```

These fields represent POI validation information.

---

## Quantity / Order References

The table also contains:

```text
NCdeTU
NCdeTSec
NCdeFN
```

These appear to reference order-related information for:

```text
TU
TSec
FN
```

However, their exact business meaning and relationship with the stock/purchase-order datasets must be validated.

---

# 15. Additional Dates

The table contains historical/manual date fields including:

```text
AncDateTissu
AncDateTissuSec
AncDateFourniture
AncDateFil
AncDateOKProduction
```

and validation-related dates such as:

```text
LastDateValid_CF
LastDateValid_FH
```

These fields suggest that the table preserves historical or manually maintained values.

**IMPORTANT:** these fields must not automatically be used by the new simulator.

Their role must first be validated.

---

# 16. Main Fields Relevant to the Simulator

The first fields to investigate for the theoretical-week algorithm are:

```text
DateTissu
DateTissuSec
DateFourniture
DateFil
DateOKProduction
DateMax
SemTheorique
```

and their associated status/indicator fields:

```text
EtatTissu
EtatTissuSec
EtatFourniture
EtatFil
EtatOkProduction

IndTissu
IndTissuSec
IndFourniture
IndFil
IndOkProd
```

These fields should form the initial basis for reconstructing the existing business result.

---

# 17. Relationship With `plan_t_simplanif`

The strongest candidate relationship is:

```text
plan_t_simplanif.Id_Sim
              |
              v
plan_t_simplanifpoi.Id_Sim
```

This means:

```text
One simulation
      |
      +---- POI 1
      +---- POI 2
      +---- POI 3
      ...
```

The database does not define an explicit foreign-key constraint.

Therefore this relationship is a **data-model relationship inferred from the schema**, not a formal SQL FK.

---

# 18. Relationship With `plan_t_simplanifstock`

A second candidate relationship is:

```text
plan_t_simplanifpoi.Id_Sim
              |
              v
plan_t_simplanifstock.Id_Sim
```

The stock table contains:

```text
Id_Sim
Code_Sim
Taille_Sim
Date_Sim
Client
Qte
NCde
```

This suggests that stock records may be used as an input for availability calculations.

However:

> The exact join between a POI and its stock records is NOT confirmed by `Id_Sim` alone.

Potential additional keys such as article/code, size, client, order number, or other fields may be required.

This must be investigated from the actual data.

---

# 19. SemTheorique — Important Interpretation Rule

The existence of:

```text
SemTheorique
```

does **NOT** prove how it was calculated.

For the new simulator, the correct approach is:

```text
Historical SemTheorique
        =
Reference / observed result
```

not:

```text
Historical SemTheorique
        =
Proof of algorithm
```

The algorithm must be reconstructed by studying:

1. component dates;
2. component statuses;
3. indicators;
4. POI characteristics;
5. stock/order/reception data;
6. historical results;
7. business rules from the cahier des charges;
8. application behavior if available.

---

# 20. Expected Business Concept

The project specification identifies several required production elements:

```text
Main fabric
Secondary fabric
Supplies / accessories
Sewing thread
OK Production
```

A conceptual theoretical-date rule is:

```text
DateTheo =
MAX(
    DateTissu,
    DateTissuSec,
    DateFourniture,
    DateFil,
    DateOKProduction
)
```

and then:

```text
SemTheorique = Week(DateTheo)
```

However, this formula must be treated as a **business hypothesis until every component date and its applicability conditions are validated against the source data**.

Do not implement it blindly.

---

# 21. Blocking Element

If the maximum component date is used, the corresponding component can theoretically be identified as the blocking element.

Example:

```text
DateTissu       = 2026-08-03
DateTissuSec    = 2026-08-05
DateFourniture  = 2026-08-04
DateFil         = 2026-08-02
DateOKProduction= 2026-08-05
```

The theoretical date would be:

```text
2026-08-05
```

but the tie between `TissuSec` and `OKProduction` requires an explicit tie-breaking rule if the application must return exactly one blocking element.

**Tie-breaking is currently UNKNOWN.**

---

# 22. Missing Data

The table contains nullable fields.

Therefore the simulator must distinguish between:

```text
NULL
```

and:

```text
valid date
```

A missing component date cannot automatically be treated as:

```text
0
```

or:

```text
not required
```

without business validation.

The following cases must be investigated:

- missing fabric date;
- missing secondary-fabric date;
- missing accessory date;
- missing thread date;
- missing OK Production date;
- component not applicable;
- component required but unavailable;
- invalid date;
- inconsistent status/date combinations.

---

# 23. Data Quality and Validation

Important validation dimensions include:

### POI uniqueness

Check:

```text
(Id_Sim, POI_Sim)
```

for uniqueness.

### Date consistency

Check relationships between:

```text
DateTissu
DateTissuSec
DateFourniture
DateFil
DateOKProduction
DateMax
SemTheorique
```

### Indicator consistency

Check whether:

```text
IndTissu
IndTissuSec
IndFourniture
IndFil
IndOkProd
```

correspond consistently to the presence/status of their dates.

### Historical result consistency

For every valid POI:

```text
Recomputed result
        vs
Stored SemTheorique
```

This comparison will be essential during validation.

---

# 24. Recommended Analysis Dataset

For reconstructing the algorithm, the first analytical dataset should contain at least:

```text
Id_Sim
POI_Sim

BesoinTissu
DateTissu
DispTissu
EtatTissu
tauxDispTissu

DateTissuSec
StatutTissuSec
EtatTissuSec
tauxDispTissuSec

DateFourniture
LastFourniture
StatutFourniture
EtatFourniture

DateFil
LastFil
StatutFil
EtatFil

DateTraitementSP
LastTraitementSP
EtapeFH

DateOKProduction
EtatOkProduction
StatutOkProduction

DateMax
StatutDateTheo
SemTheorique
SemTheoriqueCoupe

IndTissu
IndTissuSec
IndFourniture
IndFil
IndOkProd
IndSemPiq
```

This subset is sufficient for an initial `SemTheorique` investigation without loading every column.

---

# 25. Confirmed / Observed / Unknown

## CONFIRMED BY SQL

- `plan_t_simplanifpoi` is the POI/detail table.
- `Id_SimPoi` is the primary key.
- `(Id_Sim, POI_Sim)` is unique.
- `Id_Sim` exists.
- `POI_Sim` exists.
- `DateTissu` exists.
- `DateTissuSec` exists.
- `DateFourniture` exists.
- `DateFil` exists.
- `DateOKProduction` exists.
- `DateMax` exists.
- `SemTheorique` exists.
- `SemTheoriqueCoupe` exists.
- Component indicators exist.
- Status/state fields exist for the different components.

## OBSERVED

- The table stores both component-level availability information and the resulting theoretical-week fields.
- Several component dates can be `NULL`.
- Historical/manual fields coexist with calculated-looking fields.
- POIs are associated with simulations through `Id_Sim`.

## INFERRED

- The table is the main analytical table for reconstructing the theoretical-week calculation.
- `Id_Sim` is a parent-level relationship to the simulation table.
- Stock information may contribute to the calculation.

## UNKNOWN / TO VALIDATE

- Exact formula used historically to calculate `SemTheorique`.
- Exact calculation of every component date.
- Conditions under which a component is considered required.
- Meaning of every status value.
- Meaning of every indicator value.
- Exact relationship between POI, article, size, stock, purchase order and reception.
- Exact date-to-week conversion rule.
- Tie-breaking rule for multiple blocking components.
- Treatment of missing/unavailable components.
- Whether historical/manual dates were used in the original calculation.

---

# 26. Usage Rule for the Project

When working on the simulator:

1. Use `plan_t_simplanifpoi` as the main POI-level analytical source.
2. Treat stored `SemTheorique` as the historical reference result.
3. Do not assume its calculation formula from the column name.
4. Reconstruct component availability progressively.
5. Validate every inferred relationship against raw data.
6. Preserve original values and never overwrite raw SQL data.
7. Create derived datasets separately.
8. Compare the new simulator against historical `SemTheorique`.
9. Record mismatches and investigate them before optimizing.
10. Only after correctness is established should performance optimization and Hadoop MapReduce be introduced.

---

# 27. Primary Source

Raw source:

`plan_t_simplanifpoi.sql`

This document is a navigation and documentation layer for the raw SQL source. The raw SQL remains authoritative for exact evidence.