# Pipeline Architecture

## Objective
Build a reproducible pipeline from raw archive/company data to a validated theoretical production-week result.

## High-Level Flow

```text
RAW SQL / EXCEL / PDF
        |
        v
INGESTION
        |
        v
SCHEMA + DATA QUALITY VALIDATION
        |
        v
NORMALIZATION
        |
        v
DATA INTEGRATION / MAPPING
        |
        v
CANONICAL POI DATASET
        |
        v
COMPONENT APPLICABILITY
        |
        v
AVAILABILITY CALCULATION
        |
        v
SEM THEORIQUE CALCULATION
        |
        v
VALIDATION
        |
        v
LOCAL BASELINE
        |
        v
BENCHMARK + BOTTLENECK
        |
        v
OPTIMIZATION
        |
        v
HADOOP MAPREDUCE
        |
        v
LOCAL VS DISTRIBUTED COMPARISON
```

## Stages

### 1. Ingestion
Load raw files without modifying them.

### 2. Schema Validation
Validate columns, keys, types, row counts, and constraints.

### 3. Data Quality
Detect NULLs, invalid dates, duplicates, inconsistent identifiers, suspicious quantities, and suspicious weeks.

### 4. Normalization
Standardize representations only when technically justified. Do not silently change business meaning.

### 5. Integration
Only implement joins supported by evidence.

Current evidence:
- Simulation → Stock through `Id_Sim`: strongly supported where ranges overlap.
- Simulation → POI through `Id_Sim`: not demonstrated in the supplied extract.
- POI → Stock: no direct valid key demonstrated.

### 6. Canonical Dataset
Create one row per POI with provenance.

### 7. Business Calculation
Determine required components, availability, theoretical date/week, and blocker.

### 8. Validation
Compare calculated results against historical `SemTheorique` when populated.

### 9. Baseline and Performance
Implement local baseline first, then measure before optimizing.

### 10. Hadoop
Use MapReduce only after the local bottleneck is measured.

## Principles
1. Raw data is immutable.
2. Transformations are reproducible.
3. Business rules are separate from technical code.
4. Unknown relationships remain explicit.
5. Synthetic data is clearly labelled.
6. Benchmark before optimization.
