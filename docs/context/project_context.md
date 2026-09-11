# Project Context — Theoretical Production Week Simulator

## 1. Project Overview

This project aims to develop a new simulator for determining the theoretical production week of a Production Order (PO) in a textile manufacturing context, particularly for jeans production.

The simulator must determine the earliest theoretical week at which a PO can be considered ready to enter production, based on the availability or validation of all required production components.

The project is based on historical/archive company data. The data is not real-time.

The project must start with a simple and understandable local implementation. Hadoop/MapReduce will be introduced later as a distributed-processing prototype and performance comparison.

---

## 2. Main Objective

The main objective is to calculate automatically:

- the theoretical production week (`SemTheorique`);
- the component that blocks production when one component is later than the others;
- the availability status of the required components;
- anomalies or incomplete data that prevent a reliable calculation.

The fundamental business principle is:

> Production cannot theoretically start until all required components are available or validated.

Therefore:

`SemTheorique = latest availability week among the required components`

The components explicitly identified in the project documentation are:

1. Main fabric
2. Secondary fabric
3. Accessories / supplies
4. Sewing thread
5. OK Production technical validation

---

## 3. Business Example

Example:

| Component | Availability |
|---|---|
| Main fabric | Week 35 |
| Secondary fabric | Week 34 |
| Accessories | Week 36 |
| Thread | Week 35 |
| OK Production | Week 33 |

The theoretical production week is:

`SemTheorique = Week 36`

The blocking component is:

`Accessories`

Even though the other components are available earlier, production cannot theoretically start before all required components are available.

---

## 4. Project Scope

The simulator should progressively cover the following workflow:

1. Understand the available historical data.
2. Understand the relationships between simulations, POIs and stock.
3. Identify the business fields required for availability calculation.
4. Define and validate the calculation logic.
5. Implement a local baseline simulator.
6. Build a simple web interface.
7. Measure the baseline execution time.
8. Identify the real computational bottleneck.
9. Optimize the processing.
10. Introduce Hadoop MapReduce where distributed processing is technically justified.
11. Compare local and distributed execution.
12. Document the complete approach in the final internship report.

---

## 5. Data Sources

The main SQL sources currently available are:

### 5.1 `plan_t_simplanif`

This table represents simulation-level information.

It contains information such as:

- simulation identifier (`Id_Sim`);
- simulation type;
- simulation category;
- simulation date;
- user;
- simulation week;
- client;
- division;
- season;
- model;
- fabric-related simulation information;
- simulation status and validation information.

The table must be studied to understand how a simulation is identified and how it relates to POIs.

---

### 5.2 `plan_t_simplanifpoi`

This table represents POI-level information inside a simulation.

It is particularly important because it contains fields directly related to component availability and the theoretical week.

Important fields include:

- `Id_SimPoi`
- `Id_Sim`
- `POI_Sim`
- `BesoinTissu`
- `DateTissu`
- `DispTissu`
- `EtatTissu`
- `tauxDispTissu`
- `DateTissuSec`
- `StatutTissuSec`
- `EtatTissuSec`
- `tauxDispTissuSec`
- `DateFourniture`
- `LastFourniture`
- `StatutFourniture`
- `EtatFourniture`
- `DateFil`
- `LastFil`
- `StatutFil`
- `EtatFil`
- `DateOKProduction`
- `EtatOkProduction`
- `StatutOkProduction`
- `DateMax`
- `StatutDateTheo`
- `SemTheorique`
- `SemTheoriqueCoupe`

It also contains indicator fields such as:

- `IndTissu`
- `IndTissuSec`
- `IndFourniture`
- `IndFil`
- `IndOkProd`

This table is currently considered the central candidate table for reconstructing the theoretical-week calculation.

This does NOT mean that the exact calculation formula has already been completely reconstructed.

---

### 5.3 `plan_t_simplanifstock`

This table represents stock information associated with simulations.

Important fields include:

- `Id_stock`
- `Id_Sim`
- `Code_Sim`
- `Taille_Sim`
- `Date_Sim`
- `Client`
- `Qte`
- `NCde`
- `CrtDateAuto`

The stock table may be necessary to understand how fabric/accessory availability is determined.

The exact relationship between stock records and POI component requirements must be validated before implementing the final business logic.

---

## 6. Other Available Data Sources

Additional files are available and may contribute to understanding the business logic:

- `table.xlsx`
- `consommation tissu par type.xlsx`
- `cde.xls`
- purchase-order PDF documents
- project/cahier des charges documentation

These sources must be analyzed before assuming that a particular field or relationship represents a business rule.

---

## 7. Important Methodological Principle

The implementation must distinguish between:

### Confirmed facts

Information explicitly supported by the project documentation or data.

### Observations

Patterns observed in the datasets.

### Hypotheses

Relationships or rules that appear plausible but have not yet been confirmed.

### Recommendations

Technical choices proposed for the implementation.

The developer/LLM must NOT silently transform a hypothesis into a confirmed business rule.

When the available data is insufficient to determine a rule, the issue must be documented as an open question.

---

## 8. Development Strategy

The project should NOT start directly with Hadoop.

The recommended progression is:

`Data Understanding`
→ `Data Model`
→ `Business Logic`
→ `Baseline Simulator`
→ `Web Interface`
→ `Benchmark`
→ `Bottleneck Identification`
→ `Optimization`
→ `Hadoop MapReduce`
→ `Performance Comparison`

The baseline implementation is important because it provides a reference against which optimized and distributed versions can be compared.

---

## 9. Hadoop Objective

Hadoop/MapReduce is a later stage of the project.

Its purpose is to explore distributed processing of a large number of PO simulations and compare its execution with the local implementation.

The project documentation describes the conceptual flow as:

`PO Data → HDFS → Hadoop Processing → MAX Calculation → Result`

The distributed implementation must only be designed after the business calculation and baseline implementation are understood.

---

## 10. User Interface

The interface should remain simple.

Its purpose is to allow a user to:

- select or enter a PO/POI;
- consult component availability;
- see the calculated theoretical week;
- identify the blocking component;
- detect missing or invalid information.

A simple web interface is sufficient.

The project documentation explicitly recommends simple technologies such as Python with Flask or Streamlit.

---

## 11. Current State of Knowledge

At this stage, the following principle is confirmed:

`SemTheorique = MAX(availability of required components)`

However, the exact process used to obtain each availability value is not yet completely established.

The following questions still require investigation:

- How exactly is `DateTissu` calculated?
- How exactly is `DateTissuSec` calculated?
- How exactly is `DateFourniture` calculated?
- How exactly is `DateFil` calculated?
- How exactly is `DateOKProduction` determined?
- When is a component considered required?
- How are missing dates handled?
- How are stock quantities used?
- How are purchase orders and receptions linked to POIs?
- How are weeks derived from dates?
- How is the blocking component determined in case of ties?
- How should invalid or incomplete POIs be treated?

These questions must be resolved before considering the business logic complete.

---

## 12. Important Constraint

The raw SQL files are source-of-truth data files.

They should not be replaced by the documentation files.

Because the raw SQL datasets are large, lightweight documentation files should be created to make the data understandable and usable by an LLM without loading the entire SQL dumps into project knowledge.

The documentation layer should contain:

- schemas;
- data dictionaries;
- statistics;
- null analysis;
- cardinality;
- representative samples;
- candidate relationships;
- business-rule mappings;
- unresolved questions.

The raw data remains available separately for actual processing and validation.