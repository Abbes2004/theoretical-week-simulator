# SQL Reference — `plan_t_simplanifstock`

## 1. Document Purpose

This document is a technical reference for:

`plan_t_simplanifstock.sql`

It documents the table structure, grain, constraints, important fields, and directly observable characteristics of the stock data.

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
| Table | `plan_t_simplanifstock` |
| Storage engine | InnoDB |
| Primary key | `Id_stock` |
| Unique constraint | `(Id_Sim, Code_Sim, Taille_Sim, Date_Sim, Client)` |
| Main role | Simulation-related stock information |

The SQL dump originates from the `production` database.

**CONFIRMED BY SQL.**

---

# 3. Table Role

`plan_t_simplanifstock` stores stock information associated with simulations.

The table contains information about:

- simulation;
- stock/article code;
- size;
- stock date;
- client;
- quantity;
- order/reference number;
- automatic creation timestamp.

The table is potentially important for reconstructing availability dates used by the theoretical-week calculation.

However:

> The existence of stock information does not by itself prove that every stock record participates in the `SemTheorique` calculation.

The exact usage must be reconstructed from the data and business/application logic.

---

# 4. Table Grain

The technical primary key is:

```text id="k2h6qa"
Id_stock
```

The table also defines a unique combination:

```text id="m4ph2s"
(Id_Sim, Code_Sim, Taille_Sim, Date_Sim, Client)
```

Therefore, the logical uniqueness of a stock record is represented by:

```text id="8i9j5n"
Simulation
+
Stock/article code
+
Size
+
Stock date
+
Client
```

**CONFIRMED BY SQL.**

---

# 5. Constraints

## Primary Key

```text id="f8xj2c"
PRIMARY KEY (Id_stock)
```

## Unique Key

```text id="c1j5p4"
UNIQUE (
    Id_Sim,
    Code_Sim,
    Taille_Sim,
    Date_Sim,
    Client
)
```

**CONFIRMED BY SQL.**

---

# 6. Indexes

The table contains indexes supporting access through:

```text id="8qz6du"
(Code_Sim, Client, Date_Sim)
```

and:

```text id="6qvl8s"
Id_Sim
```

These indexes are potentially useful for:

- retrieving stock for a simulation;
- searching stock by article/code;
- filtering by client;
- filtering by stock date.

**CONFIRMED BY SQL.**

---

# 7. Complete Column Reference

| Column | SQL Type | Role |
|---|---|---|
| `Id_stock` | `int(11)` | Technical stock-record identifier |
| `Id_Sim` | `int(11)` | Simulation identifier |
| `Code_Sim` | `varchar(50)` | Stock/article code |
| `Taille_Sim` | `varchar(50)` | Size |
| `Date_Sim` | `date` | Stock date |
| `Client` | `varchar(50)` | Client |
| `Qte` | `decimal(10,3)` | Quantity |
| `NCde` | `varchar(50)` | Order/reference number |
| `CrtDateAuto` | `timestamp` | Automatic creation/update timestamp |

**CONFIRMED BY SQL.**

---

# 8. Identification Fields

The main identifiers are:

```text id="n2v2hr"
Id_stock
Id_Sim
Code_Sim
Taille_Sim
```

### `Id_stock`

Technical identifier of the stock row.

### `Id_Sim`

Simulation identifier.

This is the main candidate relationship with:

```text id="4h3i5k"
plan_t_simplanif.Id_Sim
plan_t_simplanifpoi.Id_Sim
```

### `Code_Sim`

Code identifying the stock/article/material represented by the row.

The exact semantic meaning of the code depends on the business context.

### `Taille_Sim`

Size associated with the stock record.

This field is potentially important because availability can depend on size.

---

# 9. Stock Date

The field:

```text id="f5z1rx"
Date_Sim
```

is defined as:

```text id="j4p7qm"
DATE
```

It represents a date associated with the stock record.

**IMPORTANT:**

The name `Date_Sim` alone does not prove that it is:

- reception date;
- availability date;
- stock-entry date;
- simulation date.

Its exact business meaning must be validated.

---

# 10. Quantity

The quantity field is:

```text id="u7n3pc"
Qte
```

with SQL type:

```text id="x1t8vb"
DECIMAL(10,3)
```

Therefore fractional quantities are technically supported.

Example conceptually:

```text id="j9r2ab"
Qte = 100.000
```

or:

```text id="d6q5vn"
Qte = 1.500
```

The exact unit of the quantity is **NOT established by the SQL schema alone**.

---

# 11. Client

The field:

```text id="f4a8zq"
Client
```

is defined as:

```text id="v2x6km"
varchar(50)
```

Stock records are therefore associated with a client.

This is potentially important when the same material/code exists for multiple clients.

---

# 12. Order Reference

The field:

```text id="p6k3wa"
NCde
```

is defined as:

```text id="e5d1ru"
varchar(50)
```

It appears to contain an order/reference number.

**OBSERVED:** sample records contain order-like/reference values.

**UNKNOWN:** whether `NCde` corresponds to a purchase order, customer order, internal order, or another business reference.

This must be validated before using it as a join key.

---

# 13. Relationship With the Simulation Table

Candidate relationship:

```text id="x8b5te"
plan_t_simplanif.Id_Sim
              |
              v
plan_t_simplanifstock.Id_Sim
```

Conceptually:

```text id="q1z9mw"
Simulation
    |
    +---- Stock record 1
    +---- Stock record 2
    +---- Stock record 3
    ...
```

There is no explicit foreign-key constraint establishing this relationship.

Therefore:

> `Id_Sim` is a strong data-model candidate, but the relationship must be verified using actual records.

---

# 14. Relationship With the POI Table

A possible relationship is:

```text id="s4d8yk"
plan_t_simplanifpoi
        |
        | Id_Sim
        v
plan_t_simplanifstock
```

However, `Id_Sim` alone may not identify the correct stock record for a POI.

Other potentially relevant fields include:

```text id="w7c2hj"
POI/article information
Code_Sim
Taille_Sim
Client
NCde
Date_Sim
```

The exact mapping is **UNKNOWN**.

This is a critical point for the simulator.

---

# 15. Potential Role in Availability Calculation

The stock table could potentially be used to determine whether a required material is available.

A generic conceptual process could be:

```text id="v3m8qa"
Required material
        ↓
Find corresponding stock records
        ↓
Filter by relevant client / size / code
        ↓
Evaluate quantity
        ↓
Determine availability date
```

However, this is only an analytical hypothesis.

The SQL schema does **NOT** establish this algorithm.

The working LLM must investigate the raw records and supporting files before implementing it.

---

# 16. Important Fields for the Simulator

The first fields to investigate are:

```text id="r8k1fy"
Id_Sim
Code_Sim
Taille_Sim
Date_Sim
Client
Qte
NCde
```

Particularly:

### `Code_Sim`

Potential material/article identification.

### `Taille_Sim`

Potential size-specific availability.

### `Date_Sim`

Potential temporal dimension of stock.

### `Qte`

Potential quantity availability.

### `Client`

Potential client-specific stock allocation.

### `NCde`

Potential order linkage.

---

# 17. Stock and `SemTheorique`

The table does **not** contain:

```text id="p4x7md"
SemTheorique
```

It also does not directly contain:

```text id="v9c3la"
DateTissu
DateTissuSec
DateFourniture
DateFil
DateOKProduction
```

Instead, it contains raw stock-level information that may potentially contribute to the calculation of these dates.

Therefore the expected architecture is:

```text id="h6q2ws"
Raw Stock
   ↓
Availability determination
   ↓
Component availability date
   ↓
POI theoretical date
   ↓
SemTheorique
```

The exact transformation must be reconstructed.

---

# 18. Important Distinction: Stock Date vs Availability Date

Do not automatically assume:

```text id="c8r5zn"
Date_Sim = DateTissu
```

or:

```text id="e1m7kp"
Date_Sim = DateFourniture
```

A stock record can represent a quantity/date record, while the final component availability date may depend on:

- required quantity;
- accumulated stock;
- reservations;
- orders;
- receptions;
- client;
- size;
- material;
- multiple stock records.

This must be validated from the actual data.

---

# 19. Quantity Aggregation Hypothesis

One possible analytical mechanism is cumulative quantity over dates:

```text id="a3k9pd"
For a required quantity Q:

Sort stock by Date_Sim
        ↓
Accumulate available quantities
        ↓
Find the first date where
cumulative quantity >= required quantity
        ↓
Availability date
```

This is a **HYPOTHESIS**, not a confirmed company rule.

It should only be implemented if supported by:

- business documentation;
- existing application logic;
- sample cases;
- comparison against historical `DateTissu` / `DateFourniture`;
- validation by the project owner/company.

---

# 20. Reservations and Allocation

The existence of:

```text id="j2w6cq"
Qte
Client
NCde
```

suggests that simply summing all stock records may be incorrect.

Stock may need to be interpreted according to business allocation rules.

For example, theoretically:

```text id="y6h1sr"
Total physical stock
        ≠
Stock available for this POI
```

This distinction must be investigated.

---

# 21. Data Quality Considerations

The simulator should investigate:

- `NULL` values;
- zero quantities;
- negative quantities if present;
- duplicated logical stock records;
- multiple dates for the same code;
- multiple clients;
- multiple sizes;
- missing order references;
- inconsistent codes;
- records outside the simulation period.

Do not silently remove such records.

Every filtering rule should be documented and justified.

---

# 22. Historical Data

The SQL dump contains historical simulation/stock records.

The data therefore appears suitable for:

```text id="k3v7mn"
Historical analysis
+
Algorithm reconstruction
+
Validation
+
Benchmarking
```

However, the exact period and completeness of the historical data must be established by profiling the entire dataset.

---

# 23. Performance Relevance

The table is substantially larger than the simulation-level table.

For the future performance work, the important questions are:

1. How many stock rows correspond to one simulation?
2. How many distinct `Code_Sim` values exist?
3. How many rows exist per `(Code_Sim, Client)`?
4. How many rows exist per `(Code_Sim, Taille_Sim, Client)`?
5. How many dates exist for the same material?
6. How much data is actually required for one simulation?
7. Can the required stock subset be filtered before computation?
8. Which operations dominate local execution time?

These questions should be answered before implementing MapReduce.

---

# 24. Recommended Analytical Subset

For the first reconstruction phase, the working dataset should at minimum contain:

```text id="u4c7nx"
Id_Sim
Code_Sim
Taille_Sim
Date_Sim
Client
Qte
NCde
```

Additional columns should only be introduced if required.

This helps keep the first analysis focused and makes performance measurements easier.

---

# 25. CONFIRMED / OBSERVED / INFERRED / UNKNOWN

## CONFIRMED BY SQL

- The table is `plan_t_simplanifstock`.
- `Id_stock` is the primary key.
- `(Id_Sim, Code_Sim, Taille_Sim, Date_Sim, Client)` is unique.
- `Id_Sim` exists.
- `Code_Sim` exists.
- `Taille_Sim` exists.
- `Date_Sim` exists.
- `Client` exists.
- `Qte` exists.
- `NCde` exists.
- The table contains an index on `Id_Sim`.
- The table contains an index involving `Code_Sim`, `Client`, and `Date_Sim`.

## OBSERVED

- The dataset contains historical stock records.
- Stock records can be associated with simulations.
- The data contains material/article codes, sizes, dates, clients and quantities.

## INFERRED

- The table is a potential input for availability calculations.
- `Id_Sim` is a candidate relationship with the simulation and POI tables.
- `Code_Sim`, `Taille_Sim`, and `Client` may be important dimensions when matching stock to a requirement.

## HYPOTHESIS

- Availability may be determined through cumulative quantities over dates.
- The earliest date satisfying a required quantity may represent availability.
- Stock may need to be filtered by client and size.

These hypotheses must be validated before implementation.

## UNKNOWN / TO VALIDATE

- Exact meaning of `Date_Sim`.
- Exact unit of `Qte`.
- Exact meaning of `Code_Sim`.
- Exact business meaning of `NCde`.
- Whether stock is physical, reserved, available, or projected.
- Reservation/allocation rules.
- Exact join between POI requirements and stock records.
- Whether client must always be part of the matching logic.
- Whether size must always be part of the matching logic.
- How multiple stock dates are aggregated.
- How stock shortages are represented.
- How stock contributes to `DateTissu` and/or `DateFourniture`.
- Whether stock records are complete for the entire study period.

---

# 26. Usage Rule for the Project

When using this table:

1. Treat the raw SQL dump as the source of truth.
2. Never modify the raw data.
3. Preserve quantities and dates exactly during ingestion.
4. Do not assume that every stock row is available stock.
5. Do not equate `Date_Sim` with a component availability date without validation.
6. Do not use `Id_Sim` alone for POI-to-stock matching until validated.
7. Investigate quantity, client, size, code and order relationships.
8. Build derived availability datasets separately.
9. Validate derived availability dates against historical POI results.
10. Only optimize after correctness has been established.

---

# 27. Role in the Overall Data Model

The three principal SQL sources can currently be viewed as:

```text
                    plan_t_simplanif
                    Simulation level
                           |
                         Id_Sim
                           |
              +------------+------------+
              |                         |
              v                         v
   plan_t_simplanifpoi        plan_t_simplanifstock
       POI level                  Stock level
              |                         |
              |                         |
              +----------+--------------+
                         |
                         v
              Availability calculation
                         |
                         v
                  Theoretical date
                         |
                         v
                    SemTheorique
```

This diagram represents the **current working data-model hypothesis**.

It must be validated against the raw data and business rules.

---

# 28. Primary Source

Raw source:

`plan_t_simplanifstock.sql`

This document is intended as a persistent navigation/reference layer for the project.

The raw SQL remains authoritative whenever exact evidence is required.