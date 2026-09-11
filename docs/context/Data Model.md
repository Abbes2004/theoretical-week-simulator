# Data Model

## 1. Purpose

This document describes the data model currently identified for the theoretical production week simulator.

The objective is to understand:

- the role of each main table;
- the grain of each table;
- primary keys;
- uniqueness constraints;
- observed relationships;
- candidate relationships requiring validation.

The raw SQL files remain the source of truth for the database structure.

---

## 2. Main Tables

The current simulator data model is centered around three SQL tables:

```text
plan_t_simplanif
        │
        │ 1 → N
        ▼
plan_t_simplanifpoi
        │
        │ candidate relationship
        ▼
plan_t_simplanifstock
```

The three tables have different purposes.

| Table | Main role |
|---|---|
| `plan_t_simplanif` | Simulation-level information |
| `plan_t_simplanifpoi` | POI-level simulation information and theoretical availability results |
| `plan_t_simplanifstock` | Stock information associated with simulations |

---

# 3. `plan_t_simplanif`

## 3.1 Role

`plan_t_simplanif` represents the **simulation-level** entity.

It contains information describing a simulation, including:

- simulation identifier;
- simulation type/category;
- simulation date;
- client;
- division;
- season;
- model;
- fabric;
- program;
- production step;
- simulation week;
- priority;
- status/validation information.

---

## 3.2 Primary Key

The primary key is:

```text
Id_Sim
```

Therefore:

```text
plan_t_simplanif.Id_Sim
```

uniquely identifies a simulation.

---

## 3.3 Important Fields

Examples of fields relevant to the project include:

```text
Id_Sim
Type_Sim
Categ_Sim
Date_Sim
Client_Sim
Division_Sim
Saison_Sim
Model_Sim
Tissu_Sim
Prog_Sim
Etape_Sim
Sem_Sim
Priorite_Sim
Etat_Element
Type_POI
```

Several other technical, validation and date fields are also present.

---

## 3.4 Grain

The expected grain is:

```text
1 row = 1 simulation
```

The exact business meaning of multiple simulation types/categories must be validated if they become relevant to the simulator.

---

# 4. `plan_t_simplanifpoi`

## 4.1 Role

`plan_t_simplanifpoi` represents the **POI-level information inside a simulation**.

This is currently the most important table for the theoretical-week calculation.

It contains:

- POI identification;
- priority and planning information;
- component availability dates;
- component states/statuses;
- availability indicators;
- theoretical dates/weeks;
- validation and decision information.

---

## 4.2 Primary Key

The primary key is:

```text
Id_SimPoi
```

Therefore:

```text
plan_t_simplanifpoi.Id_SimPoi
```

uniquely identifies a POI record.

---

## 4.3 Business Identification

The table has:

```text
Id_Sim
POI_Sim
```

and a uniqueness constraint on:

```text
(Id_Sim, POI_Sim)
```

This means that, at the database level, a POI is uniquely identified within a simulation by:

```text
(Id_Sim, POI_Sim)
```

---

## 4.4 Important Fields

Fields directly relevant to the simulator include:

```text
Id_SimPoi
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
StatutTraitementSP

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

The table also contains validation, decision, root-simulation and technical fields.

---

# 5. Component Availability Model

At the POI level, the current data structure contains explicit date fields for the five main business elements.

Conceptually:

```text
POI
 │
 ├── DateTissu
 ├── DateTissuSec
 ├── DateFourniture
 ├── DateFil
 └── DateOKProduction
```

These fields can therefore serve as candidate inputs for the theoretical-week calculation.

However, their exact derivation must still be validated.

---

# 6. `plan_t_simplanifstock`

## 6.1 Role

`plan_t_simplanifstock` represents stock information associated with simulations.

It contains information such as:

```text
Id_stock
Id_Sim
Code_Sim
Taille_Sim
Date_Sim
Client
Qte
NCde
CrtDateAuto
```

---

## 6.2 Primary Key

The primary key is:

```text
Id_stock
```

---

## 6.3 Uniqueness

The table has a uniqueness constraint involving:

```text
(Id_Sim, Code_Sim, Taille_Sim, Date_Sim, Client)
```

This indicates that this combination is intended to uniquely identify a stock record within the database model.

---

## 6.4 Grain

The expected grain is approximately:

```text
1 row = 1 stock record for a simulation,
          code, size, date and client
```

The exact business interpretation of each stock record must be validated.

---

# 7. Relationship: Simulation → POI

The strongest relationship currently identified is:

```text
plan_t_simplanif
        │
        │ Id_Sim
        ▼
plan_t_simplanifpoi
```

Conceptually:

```text
One Simulation
      │
      ├── POI 1
      ├── POI 2
      ├── POI 3
      └── ...
```

Therefore:

```text
plan_t_simplanif.Id_Sim
```

is the candidate parent key for:

```text
plan_t_simplanifpoi.Id_Sim
```

This relationship is strongly supported by the schema structure and indexes.

### Important

The SQL structure does not necessarily mean that a formal database `FOREIGN KEY` constraint exists.

The relationship should therefore be treated as a **logical/data relationship** unless the actual database constraints confirm a physical foreign key.

---

# 8. Relationship: Simulation → Stock

The stock table also contains:

```text
Id_Sim
```

Therefore the candidate relationship is:

```text
plan_t_simplanif.Id_Sim
             │
             ▼
plan_t_simplanifstock.Id_Sim
```

Conceptually:

```text
One Simulation
      │
      ├── Stock record 1
      ├── Stock record 2
      ├── Stock record 3
      └── ...
```

This is an observed structural relationship.

However, the exact business meaning of the join must be validated before using it for availability calculations.

---

# 9. POI ↔ Stock Relationship

A direct relationship between:

```text
plan_t_simplanifpoi
```

and:

```text
plan_t_simplanifstock
```

has **not yet been formally established**.

Both tables contain `Id_Sim`, but this alone does not prove that stock can be joined directly to a POI.

The following questions must be answered before implementing such a join:

- How is a POI associated with a stock code?
- Is `POI_Sim` related to `Code_Sim`?
- Is `Taille_Sim` related to the POI?
- Is `Client` required for the join?
- Does `NCde` identify a purchase/order relationship?
- Is stock consumed at POI level?
- Are stock records aggregated before availability is calculated?

Until these questions are validated:

```text
POI ↔ Stock
```

must be considered a **candidate relationship**, not a confirmed business rule.

---

# 10. Candidate Data Model

The current logical model can therefore be represented as:

```text
┌──────────────────────────┐
│   plan_t_simplanif       │
│──────────────────────────│
│ PK Id_Sim                │
│ Type_Sim                 │
│ Categ_Sim                │
│ Date_Sim                 │
│ Client_Sim               │
│ Saison_Sim               │
│ Model_Sim                │
│ ...                      │
└────────────┬─────────────┘
             │
             │ Id_Sim
             │
             ▼
┌──────────────────────────┐
│ plan_t_simplanifpoi      │
│──────────────────────────│
│ PK Id_SimPoi             │
│ Id_Sim                   │
│ POI_Sim                  │
│ DateTissu                │
│ DateTissuSec             │
│ DateFourniture           │
│ DateFil                  │
│ DateOKProduction         │
│ SemTheorique             │
│ ...                      │
└──────────────────────────┘

             │
             │ candidate relationship
             │
             ▼

┌──────────────────────────┐
│ plan_t_simplanifstock    │
│──────────────────────────│
│ PK Id_stock              │
│ Id_Sim                   │
│ Code_Sim                 │
│ Taille_Sim               │
│ Date_Sim                 │
│ Client                   │
│ Qte                      │
│ NCde                     │
│ ...                      │
└──────────────────────────┘
```

---

# 11. Data Model and Simulator Logic

The data model supports the following high-level processing flow:

```text
Simulation
    │
    ▼
POIs belonging to simulation
    │
    ▼
Component availability information
    │
    ├── Tissu
    ├── Tissu secondaire
    ├── Fourniture
    ├── Fil
    └── OK Production
    │
    ▼
Theoretical week
```

Stock data may contribute to the calculation of component availability, but this mechanism has not yet been validated.

---

# 12. Important Distinction: Data Structure vs Business Logic

The existence of a column does not automatically define a business rule.

For example:

```text
DateTissu
```

exists in the POI table.

This confirms that a fabric-related date is stored.

It does **not** by itself confirm:

- how the date was calculated;
- whether it represents complete availability;
- whether stock was considered;
- whether purchase orders were considered;
- whether substitutions were considered.

The simulator must reconstruct these rules from validated business knowledge and data relationships.

---

# 13. Current Confidence Level

| Relationship / concept | Status |
|---|---|
| `plan_t_simplanif` → `plan_t_simplanifpoi` through `Id_Sim` | Strongly supported |
| `(Id_Sim, POI_Sim)` identifies POI within simulation | Confirmed by unique constraint |
| `plan_t_simplanif` → `plan_t_simplanifstock` through `Id_Sim` | Structurally supported |
| POI → component availability fields | Observed |
| POI → stock direct relationship | Not validated |
| Stock → component availability calculation | Not validated |
| Purchase order → component availability | Not validated |
| Exact calculation of `DateTissu` etc. | Not validated |

---

# 14. Rules for Further Data Analysis

Before implementing joins involving stock or other source files, the following must be investigated:

1. Cardinality of `Id_Sim` between tables.
2. Whether every POI has a valid parent simulation.
3. Whether every stock record has a valid simulation.
4. Distribution of POIs per simulation.
5. Distribution of stock records per simulation.
6. Possible identifiers linking POIs to stock.
7. Relationship between POI fields and purchase-order information.
8. Whether component dates can be reproduced from source data.

These analyses belong to the data profiling and relationship-validation stages.

---

# 15. Final Model Principle

The current data model should be considered a **logical model under validation**, not a fully reconstructed production database model.

The implementation should therefore:

- use confirmed keys and relationships;
- document candidate relationships;
- validate joins with real data;
- avoid unnecessary joins;
- avoid assuming undocumented business logic;
- preserve the original raw data;
- maintain a clear distinction between source data and derived simulator outputs.