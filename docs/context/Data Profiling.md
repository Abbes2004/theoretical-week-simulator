# Data Profiling

## 1. Purpose

This document defines the data profiling activities required before implementing the theoretical production week simulator.

The objective is to understand the actual characteristics of the available data:

- volume;
- completeness;
- null values;
- uniqueness;
- cardinality;
- distributions;
- date ranges;
- duplicate records;
- relationships between tables;
- consistency of component availability fields.

Profiling is an analysis step. It must not modify the raw SQL source files.

---

# 2. Source Tables

The main profiling scope covers:

```text id="4h7m3n"
plan_t_simplanif
plan_t_simplanifpoi
plan_t_simplanifstock
```

Additional sources may be profiled later when they are confirmed to participate in the simulator:

```text id="n8yq4s"
plan_t_simplaniffourniture
cde.xls
consommation tissu par type.xlsx
PO documents
```

---

# 3. Profiling Principles

The profiling process must distinguish between:

```text id="z7qk6p"
Raw observation
      ↓
Data quality finding
      ↓
Possible explanation
      ↓
Business validation
```

A statistical observation must not automatically be interpreted as a business rule.

Example:

```text id="e4f5kn"
80% of DateTissu values are NULL
```

This does not automatically mean:

```text id="8q2z0j"
80% of POIs do not require fabric
```

The meaning must be investigated.

---

# 4. Basic Table Statistics

For every main table, calculate:

- number of rows;
- number of columns;
- minimum and maximum primary key;
- number of distinct simulations;
- number of distinct POIs where applicable;
- date range;
- duplicate count.

Expected output:

| Table | Rows | Columns | Distinct `Id_Sim` | Date range |
|---|---:|---:|---:|---|
| `plan_t_simplanif` | To calculate | To calculate | To calculate | To calculate |
| `plan_t_simplanifpoi` | To calculate | To calculate | To calculate | To calculate |
| `plan_t_simplanifstock` | To calculate | To calculate | To calculate | To calculate |

Actual values must be generated from the raw data and must not be guessed.

---

# 5. Null Analysis

Null analysis is particularly important for the component availability fields.

The following fields must be profiled:

```text id="i0p8w4"
DateTissu
DateTissuSec
DateFourniture
DateFil
DateOKProduction
DateMax
SemTheorique
```

For each field calculate:

```text id="5p3q9r"
Total rows
NULL count
NULL percentage
Non-NULL count
Non-NULL percentage
```

Example format:

| Field | Total | NULL | NULL % | Non-NULL | Non-NULL % |
|---|---:|---:|---:|---:|---:|
| `DateTissu` | To calculate | To calculate | To calculate | To calculate | To calculate |
| `DateTissuSec` | To calculate | To calculate | To calculate | To calculate | To calculate |
| `DateFourniture` | To calculate | To calculate | To calculate | To calculate | To calculate |
| `DateFil` | To calculate | To calculate | To calculate | To calculate | To calculate |
| `DateOKProduction` | To calculate | To calculate | To calculate | To calculate | To calculate |

---

# 6. Combined Availability Completeness

For each POI, determine how many of the five component dates are available.

Conceptually:

```text id="g6l9q1"
POI
 │
 ├── DateTissu
 ├── DateTissuSec
 ├── DateFourniture
 ├── DateFil
 └── DateOKProduction
```

Create a distribution:

| Number of available component dates | Number of POIs |
|---:|---:|
| 0 | To calculate |
| 1 | To calculate |
| 2 | To calculate |
| 3 | To calculate |
| 4 | To calculate |
| 5 | To calculate |

This helps determine how complete the historical data is.

---

# 7. `SemTheorique` Profiling

The historical result field:

```text id="0q6j3c"
SemTheorique
```

must be profiled.

Analyze:

- NULL percentage;
- minimum value;
- maximum value;
- distinct values;
- frequency distribution;
- values outside the expected study period;
- relationship with component dates.

Important:

> `SemTheorique` is treated as a historical/reference result, not as proof of the calculation formula.

---

# 8. Date Profiling

For every component date, calculate:

```text id="5k3z4j"
MIN(date)
MAX(date)
NULL count
distinct dates
```

Fields:

```text id="8m1qvh"
DateTissu
DateTissuSec
DateFourniture
DateFil
DateOKProduction
DateMax
```

The objective is to identify:

- impossible dates;
- suspicious dates;
- dates outside the expected study period;
- abnormal concentrations;
- inconsistent ordering.

---

# 9. Date Consistency

Check whether:

```text id="x5l7z2"
DateMax >= each applicable component date
```

For example:

```text id="4k7xq1"
DateMax >= DateTissu
DateMax >= DateTissuSec
DateMax >= DateFourniture
DateMax >= DateFil
DateMax >= DateOKProduction
```

This check should only consider component dates that are applicable and non-null.

Violations should be reported rather than silently corrected.

---

# 10. Theoretical Week Consistency

A first consistency test is:

```text id="4xj2t8"
SemTheorique
```

should correspond to the week represented by the latest applicable component availability date.

However, this is a **validation hypothesis**, not an assumption that can be used to overwrite historical data.

For each POI, compare:

```text id="p5y7d1"
Historical SemTheorique
        vs
Week(max(component dates))
```

Then calculate:

```text id="v6r3n2"
Exact matches
Non-matches
Historical SemTheorique missing
Component dates incomplete
```

This is one of the most important profiling analyses.

---

# 11. Blocking Component Analysis

For POIs where all applicable component dates are available, identify the component corresponding to the latest date.

Example:

```text id="a3w6c8"
DateTissu        = 2025-08-04
DateTissuSec     = 2025-08-05
DateFourniture   = 2025-08-02
DateFil          = 2025-08-03
DateOKProduction = 2025-08-06
```

Result:

```text id="8p0j5m"
Blocking component = OK Production
```

Profile the frequency of each blocking component.

| Component | Number of POIs | Percentage |
|---|---:|---:|
| Tissu | To calculate | To calculate |
| Tissu secondaire | To calculate | To calculate |
| Fourniture | To calculate | To calculate |
| Fil | To calculate | To calculate |
| OK Production | To calculate | To calculate |
| Tie | To calculate | To calculate |

This analysis can later help identify the dominant business bottleneck.

---

# 12. Tie Analysis

Determine how frequently multiple components share the same maximum date.

Example:

```text id="0c3h8f"
DateTissu        = 2025-08-05
DateFourniture   = 2025-08-05
DateFil          = 2025-08-03
```

This should be classified as:

```text id="v7n3k9"
Tie on maximum availability date
```

The result is useful for determining whether a tie-breaking rule is necessary.

---

# 13. Simulation → POI Cardinality

For:

```text id="d6x1y5"
plan_t_simplanif
        ↓
plan_t_simplanifpoi
```

calculate:

```text id="2h9w4q"
Number of POIs per simulation
```

Produce statistics:

- minimum;
- maximum;
- mean;
- median;
- percentiles;
- frequency distribution.

This is important for understanding data volume and later performance optimization.

---

# 14. Simulation → Stock Cardinality

Similarly, calculate:

```text id="j2m7s5"
Number of stock records per simulation
```

This helps determine whether a simulation contains:

- a small number of stock records;
- hundreds of records;
- thousands of records;
- highly uneven distributions.

Large differences between simulations may affect algorithm design and Hadoop partitioning.

---

# 15. Duplicate Analysis

Check duplicates for:

### Simulation

```text
Id_Sim
```

### POI

```text
(Id_Sim, POI_Sim)
```

### Stock

```text
(Id_Sim, Code_Sim, Taille_Sim, Date_Sim, Client)
```

The expected result is:

```text id="9m8t3k"
No unexpected duplicates
```

according to the database constraints.

If duplicates appear in extracted/processed datasets, investigate whether they are:

- real duplicates;
- extraction artifacts;
- repeated INSERT statements;
- different versions of the same record.

---

# 16. Referential Integrity Checks

Check whether every POI has a valid simulation:

```text id="5x3q7n"
POI.Id_Sim
    →
Simulation.Id_Sim
```

Calculate:

```text
POIs with valid simulation
POIs without matching simulation
Match rate
```

Similarly:

```text id="3y7v9k"
Stock.Id_Sim
    →
Simulation.Id_Sim
```

Calculate the same metrics.

Unmatched records must be preserved in the profiling results for investigation.

---

# 17. POI/Stock Matching Investigation

Do not immediately create a POI-stock join.

Instead, test candidate keys independently.

Potential fields:

```text id="k9w2c4"
POI_Sim
Code_Sim
Taille_Sim
Client
NCde
```

For every candidate relationship, measure:

```text id="v5q8m1"
Matching records
Non-matching records
Duplicate matches
Match percentage
```

Only relationships with convincing structural and business evidence should be used later.

---

# 18. Status and Indicator Profiling

The following groups should be profiled:

### Fabric

```text
EtatTissu
StatutTissu
IndTissu
```

### Secondary fabric

```text
EtatTissuSec
StatutTissuSec
IndTissuSec
```

### Supplies

```text
EtatFourniture
StatutFourniture
IndFourniture
```

### Thread

```text
EtatFil
StatutFil
IndFil
```

### Production approval

```text
EtatOkProduction
StatutOkProduction
IndOkProd
```

For each field calculate:

- distinct values;
- frequency of each value;
- NULL count.

The objective is to understand whether these fields can explain the availability dates.

---

# 19. Quantity Profiling

Profile:

```text id="0z4s6j"
BesoinTissu
DispTissu
tauxDispTissu
```

and stock:

```text id="6y5t8q"
Qte
```

Analyze:

- minimum;
- maximum;
- mean;
- median;
- NULL count;
- zero values;
- negative values if any;
- distribution.

This can reveal possible relationships between requirement and availability.

---

# 20. Data Quality Flags

Profiling should produce explicit flags such as:

```text id="f8y2w4"
MISSING_COMPONENT_DATE
INVALID_DATE
MISSING_SEM_THEORIQUE
SEM_THEORIQUE_MISMATCH
DUPLICATE_POI
ORPHAN_POI
ORPHAN_STOCK
SUSPICIOUS_QUANTITY
DATE_INCONSISTENCY
```

These flags are diagnostic only.

They must not automatically modify source data.

---

# 21. Recommended Profiling Output

The profiling phase should produce at least:

```text id="p7k3v9"
data_documentation/
└── profiling/
    ├── database_statistics.md
    ├── null_analysis.md
    ├── cardinality_analysis.md
    ├── date_analysis.md
    ├── sem_theorique_analysis.md
    ├── data_quality.md
    └── relationship_analysis.md
```

These files may later be generated automatically by profiling scripts.

---

# 22. Profiling Before Optimization

Profiling is not only for data quality.

It is also required for performance analysis.

The profiling phase should identify:

- number of POIs;
- number of simulations;
- number of stock records;
- average POIs per simulation;
- average component records per POI;
- largest simulation;
- potential many-to-many relationships.

These measurements will later help explain why the baseline implementation has a given execution time.

---

# 23. Profiling Rules

The working implementation must follow these rules:

1. Never modify raw SQL data during profiling.
2. Never silently remove invalid records.
3. Report NULLs explicitly.
4. Report duplicates explicitly.
5. Report unmatched relationships.
6. Separate statistical observations from business interpretations.
7. Do not infer business rules only from frequencies.
8. Keep profiling reproducible through scripts/notebooks.
9. Store generated profiling results separately from raw data.

---

# 24. Expected Outcome

At the end of profiling, the project should be able to answer:

```text id="e6k2m8"
How much data do we have?
        ↓
How complete is it?
        ↓
How are simulations and POIs distributed?
        ↓
How are component dates distributed?
        ↓
Can historical SemTheorique be reproduced?
        ↓
Which component is usually blocking?
        ↓
Which relationships are reliable?
        ↓
Which data-quality problems must be handled?
```

These answers are prerequisites for the next stages:

```text
Business Logic
      ↓
Baseline Simulator
      ↓
Benchmarking
      ↓
Optimization
      ↓
Hadoop MapReduce
```