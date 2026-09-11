# Data Relationships

## 1. Purpose

This document describes the relationships identified between the available data sources for the theoretical production week simulator.

The objective is to determine:

- how simulations are connected to POIs;
- how stock is connected to simulations;
- which relationships are safe to use;
- which joins still require validation;
- which relationships may be required to reconstruct component availability.

The principle is:

> A column with the same name does not automatically prove a valid business relationship.

---

# 2. Main Relationship Overview

The current model can be represented as:

```text
plan_t_simplanif
        │
        │ Id_Sim
        │
        ▼
plan_t_simplanifpoi
        │
        │ ?
        │
        ▼
plan_t_simplanifstock
```

The first relationship is strongly supported.

The second relationship is currently only a candidate relationship.

---

# 3. Simulation → POI

## 3.1 Join Candidate

The main relationship is:

```text
plan_t_simplanif.Id_Sim
        =
plan_t_simplanifpoi.Id_Sim
```

Conceptually:

```text
One simulation
      │
      ├── POI 1
      ├── POI 2
      ├── POI 3
      └── POI N
```

Expected cardinality:

```text
1 Simulation → N POIs
```

---

## 3.2 POI Identification

The POI table has:

```text
Id_SimPoi
Id_Sim
POI_Sim
```

with a uniqueness constraint on:

```text
(Id_Sim, POI_Sim)
```

Therefore:

```text
(Id_Sim, POI_Sim)
```

is the relevant business/database identification of a POI inside a simulation.

---

# 4. Simulation → Stock

The stock table contains:

```text
Id_Sim
```

and therefore supports a candidate relationship:

```text
plan_t_simplanif.Id_Sim
        =
plan_t_simplanifstock.Id_Sim
```

Expected conceptual cardinality:

```text
1 Simulation → N Stock records
```

This relationship is structurally supported.

However, it does not yet prove that all stock records associated with a simulation are relevant to every POI in that simulation.

---

# 5. POI → Stock

This is one of the most important relationships to investigate.

Currently:

```text
POI:
    Id_Sim
    POI_Sim

Stock:
    Id_Sim
    Code_Sim
    Taille_Sim
    Date_Sim
    Client
    Qte
    NCde
```

There is no clearly established direct key:

```text
POI → Stock
```

Therefore the following join must **not** be assumed:

```text
plan_t_simplanifpoi.Id_Sim
=
plan_t_simplanifstock.Id_Sim
```

as a complete POI-stock relationship.

That join only identifies records belonging to the same simulation.

---

# 6. Candidate Stock Matching Keys

Possible fields that could participate in a more precise relationship include:

```text
POI_Sim
Code_Sim
Taille_Sim
Client
NCde
```

But their exact semantic relationship is not yet confirmed.

The following questions must be answered:

### Question 1 — POI and `Code_Sim`

Is:

```text
POI_Sim
```

directly related to:

```text
Code_Sim
```

?

If yes, what is the transformation or mapping?

---

### Question 2 — Size

Does:

```text
Taille_Sim
```

correspond to a size requirement of the POI?

If yes:

- Is size part of the POI identity?
- Is size relevant only for stock?
- Can one POI consume several sizes?

---

### Question 3 — Client

Does:

```text
Client
```

participate in identifying the correct stock?

If yes, it may be required in the join.

---

### Question 4 — Order Reference

What does:

```text
NCde
```

represent?

If it is a purchase-order identifier, it may provide a bridge between stock/reception information and the material required by a POI.

---

# 7. Component Availability Relationships

The simulator requires availability information for:

```text
Tissu
Tissu secondaire
Fourniture
Fil
OK Production
```

The POI table already contains candidate resulting dates:

```text
DateTissu
DateTissuSec
DateFourniture
DateFil
DateOKProduction
```

The critical question is:

> Can these dates be reproduced from the underlying source data?

If yes, the simulator can reconstruct the business process rather than simply copying historical results.

---

# 8. Fabric Availability

The POI table contains:

```text
BesoinTissu
DateTissu
DispTissu
tauxDispTissu
EtatTissu
```

The presence of these fields suggests a relationship between:

```text
Required fabric
        ↓
Fabric availability
        ↓
DateTissu
```

However, the source of `DateTissu` is not yet established.

Possible source data may include:

- stock;
- fabric purchase orders;
- receptions;
- quantities;
- client/model information;
- another operational table.

These are hypotheses and must be validated.

---

# 9. Secondary Fabric Availability

The POI table contains:

```text
DateTissuSec
StatutTissuSec
EtatTissuSec
tauxDispTissuSec
```

The simulator must determine:

```text
Is secondary fabric applicable?
        ↓
If yes:
    determine availability date
        ↓
DateTissuSec
```

If secondary fabric is not applicable to a POI, a missing date should not automatically be interpreted as an error.

The applicability rule is therefore important.

---

# 10. Supply / Accessory Availability

The POI table contains:

```text
DateFourniture
LastFourniture
StatutFourniture
EtatFourniture
```

An additional source file contains a table related to supplies:

```text
plan_t_simplaniffourniture
```

with fields including:

```text
Id_fourniture
Id_Sim
POI
CI
CISibstitue
AutoSubstitue
Taille
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

This source may be important for reconstructing:

```text
POI
  ↓
Required supplies
  ↓
Supply availability
  ↓
DateFourniture
```

However, the exact join and calculation must be validated before implementation.

---

# 11. Purchase Orders and Receptions

Additional files are available containing purchase-order and reception information, including:

```text
cde.xls
```

and purchase-order documents.

These sources may provide information needed to reconstruct:

```text
Order
   ↓
Expected delivery
   ↓
Reception
   ↓
Available quantity/date
   ↓
Component availability
```

However, no join should be implemented until the relevant identifiers are established.

Potential identifiers include:

```text
NCde
POIntern
POCl
OC
CodeT
CodeQualit
CodeColoris
```

Their exact meanings and relationships require validation.

---

# 12. Stock Quantity Relationship

The stock table contains:

```text
Qte
```

while the POI table contains:

```text
BesoinTissu
```

A possible relationship is:

```text
Required quantity
        ↓
Available stock
        ↓
Availability decision
```

But the exact calculation may involve:

- reservations;
- receptions;
- partial quantities;
- multiple stock records;
- substitutions;
- different sizes;
- different dates.

Therefore, a simple direct comparison must not be implemented without validation.

---

# 13. Potential Many-to-Many Relationships

The business process may involve relationships where:

```text
One POI
    → multiple material records

One material/order
    → multiple POIs
```

This is especially plausible for:

- fabric;
- accessories;
- purchase orders;
- stock;
- receptions.

If this is confirmed, aggregation will be required before calculating component availability.

Example:

```text
POI
 │
 ├── Fabric record 1
 ├── Fabric record 2
 └── Fabric record 3
          │
          ▼
   Aggregate availability
          │
          ▼
      DateTissu
```

The exact aggregation rule remains to be determined.

---

# 14. Relationship Validation Strategy

Before using a relationship in the simulator, perform the following checks.

## Step 1 — Key existence

Check whether the candidate key exists in both datasets.

## Step 2 — Null analysis

Determine how often the key is null.

## Step 3 — Uniqueness

Check whether the key is unique on each side.

## Step 4 — Cardinality

Determine whether the relationship is:

```text
1 → 1
1 → N
N → 1
N → N
```

## Step 5 — Coverage

Measure how many records successfully match.

Example:

```text
POIs with matching stock
------------------------ × 100
Total POIs
```

## Step 6 — Business validation

A technically valid join is not necessarily a business-valid join.

The relationship must make sense from the company's process.

---

# 15. Join Quality Checks

For every important join, calculate at least:

```text
Total records
Matched records
Unmatched records
Null keys
Duplicate keys
Match rate
```

Example:

```text
POI records                = 100,000
POIs matched to source     = 96,500
POIs unmatched             = 3,500
Match rate                 = 96.5%
```

An unexpected low match rate must be investigated before the join is used in production logic.

---

# 16. Avoiding Duplicate Explosion

A critical implementation risk is joining several one-to-many datasets directly.

For example:

```text
POI
 ├── 5 fabric records
 └── 4 supply records
```

A naive join can produce:

```text
5 × 4 = 20 rows
```

instead of the expected POI-level result.

Therefore, component-level data should generally be aggregated before joining back to the POI.

Conceptually:

```text
Raw component data
        ↓
Component-level aggregation
        ↓
One result per POI/component
        ↓
Join to POI
```

This is particularly important for simulator performance.

---

# 17. Recommended Logical Processing

Instead of one large SQL-style join:

```text
POI
 + Stock
 + Orders
 + Receptions
 + Supplies
 + ...
```

the preferred architecture is:

```text
Source data
    ↓
Validate
    ↓
Transform each component independently
    ↓
Aggregate by business key
    ↓
Produce one availability result per POI/component
    ↓
Merge component results
    ↓
Calculate SemTheorique
```

This structure will also make the later Hadoop MapReduce implementation easier.

---

# 18. Relationship Confidence Table

| Relationship | Status |
|---|---|
| Simulation → POI via `Id_Sim` | Strongly supported |
| Simulation → Stock via `Id_Sim` | Structurally supported |
| `(Id_Sim, POI_Sim)` identifies POI | Confirmed |
| POI → Stock directly | Not validated |
| POI → Supply table | Candidate / requires validation |
| POI → Purchase order | Candidate / requires validation |
| Stock → Fabric availability | Not validated |
| Purchase order → Fabric availability | Not validated |
| Reception → Availability date | Not validated |
| Quantity → Availability decision | Not validated |

---

# 19. Relationship Rules for Implementation

The working implementation must follow these rules:

1. Do not join tables only because they contain a column with the same name.
2. Validate cardinality before implementing a join.
3. Measure match coverage.
4. Investigate unmatched records.
5. Aggregate one-to-many component data before POI-level merging when necessary.
6. Preserve POI-level grain for the final simulator output.
7. Document every important join.
8. Separate confirmed relationships from hypotheses.

---

# 20. Target Output Grain

The final simulator result should remain at:

```text
1 row = 1 POI in 1 simulation
```

with at least:

```text
Id_Sim
POI_Sim

DateTissu
DateTissuSec
DateFourniture
DateFil
DateOKProduction

DateMax
SemTheorique
BlockingElement
Status
```

Additional diagnostic fields may be added later.

The final output must not contain duplicated POIs as a consequence of intermediate joins.