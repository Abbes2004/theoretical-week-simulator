# 10 — Open Questions & Business Validation

## 1. Purpose

This document lists the business and technical questions that remain unresolved before implementing the final theoretical-week simulator.

The objective is to prevent the implementation from silently inventing business rules.

Every unresolved point must be classified as one of:

- **Confirmed** — explicitly validated by the project specification or company representative.
- **Observed** — directly observed in the available data.
- **Inferred** — logically suspected from the structure of the data.
- **Open Question** — requires validation.
- **Recommendation** — proposed implementation approach, not a confirmed business rule.

---

# 2. Priority 1 — Critical Questions

These questions must be answered before finalizing the simulator's calculation logic.

## Q1 — How is `DateTissu` determined?

The POI table contains:

```text
DateTissu
```

We need to know exactly how this date is calculated.

Questions:

- Does it come from fabric purchase orders?
- Does it come from expected reception dates?
- Does it depend on stock availability?
- Is it calculated from quantity requirements?
- Are several fabric orders/receptions considered?
- Does the latest reception date or the first sufficient quantity determine availability?

---

## Q2 — How is `DateTissuSec` determined?

The POI table contains:

```text
DateTissuSec
```

We need to determine:

- What qualifies as secondary fabric?
- Which source table contains its information?
- How is its availability calculated?
- Is quantity considered?
- Is stock considered?
- Can secondary fabric be optional for a POI?

---

## Q3 — How is `DateFourniture` determined?

The POI table contains:

```text
DateFourniture
```

The available data also contains a supply-related table with fields such as:

```text
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

We need to validate:

- Which fields are actually used?
- How is the required quantity determined?
- How is stock considered?
- How are purchase-order receptions considered?
- How are several supply records aggregated?
- Does every POI require accessories?

---

## Q4 — How is `DateFil` determined?

We need to understand the exact business process for sewing thread.

Questions:

- Which source contains thread information?
- Is thread linked directly to the POI?
- Is availability based on stock?
- Is availability based on purchase orders?
- Is a required quantity calculated?
- How are multiple thread records handled?

---

## Q5 — How is `DateOKProduction` determined?

This field is particularly important because it represents a technical production condition.

We need to know:

- What exactly does **OK Production** mean?
- Who/what generates this status?
- Which source determines it?
- Is `DateOKProduction` manually entered?
- Is it automatically calculated?
- What conditions must be satisfied before OK Production is obtained?

---

# 3. Priority 1 — Component Requirement

## Q6 — How do we know whether a component is required?

This is one of the most important unresolved questions.

For each POI, how do we determine:

```text
Tissu required?
Tissu secondaire required?
Fourniture required?
Fil required?
OK Production required?
```

Potential candidate fields exist, but their semantics are not yet validated.

For example:

```text
IndTissu
IndTissuSec
IndFourniture
IndFil
IndOkProd
```

We need confirmation of what each indicator means.

---

# 4. Priority 1 — Missing Values

## Q7 — What does `NULL` mean for a component date?

For example:

```text
DateFil = NULL
```

Could mean:

1. Fil is not required.
2. Fil is required but unavailable.
3. Data is missing.
4. Calculation was not performed.
5. Another business state.

The exact interpretation must be validated.

---

## Q8 — What happens when a required component is unavailable?

Example:

```text
Tissu        → available
Fourniture   → available
Fil          → unavailable
OK Production → available
```

Should the simulator:

```text
A. return no theoretical week?
B. return the next known week?
C. return NULL?
D. return a special status?
E. use another business rule?
```

This must be explicitly confirmed.

---

# 5. Priority 1 — Theoretical Date and Week

## Q9 — Does `DateMax` represent the maximum component availability date?

We currently have:

```text
DateMax
```

and the logical rule:

```text
MAX(
    DateTissu,
    DateTissuSec,
    DateFourniture,
    DateFil,
    DateOKProduction
)
```

We need to verify whether:

```text
DateMax
=
MAX(required component dates)
```

for historical records.

This should be tested empirically as well as confirmed with the engineer.

---

## Q10 — How exactly is `SemTheorique` calculated?

We need to determine whether:

```text
SemTheorique = calendar week(DateMax)
```

or whether the company uses a specific production-week convention.

Questions:

- ISO week?
- Company production week?
- Week number only?
- Year + week?
- Special handling of week 52/53?

---

## Q11 — What happens when several components have the same maximum date?

Example:

```text
Tissu        = 2025-08-08
TissuSec     = 2025-08-08
OK Production = 2025-08-08
```

The theoretical date is unambiguous.

But which component is considered the blocker?

We need to know whether:

- all tied components are blockers,
- one component has priority,
- a predefined order is used,
- or the blocking component is not important in case of a tie.

---

# 6. Priority 2 — Statuses and Indicators

## Q12 — What do the `Etat*` fields mean?

Fields include:

```text
EtatTissu
EtatTissuSec
EtatFourniture
EtatFil
EtatOkProduction
```

We need a dictionary for their possible values.

For example:

```text
0
1
2
...
```

or textual statuses.

For every possible value, we need:

```text
Value
Meaning
Business consequence
```

---

## Q13 — What do the `Statut*` fields mean?

Relevant fields include:

```text
StatutTissuSec
StatutFourniture
StatutFil
StatutOkProduction
StatutDateTheo
```

We need to understand their exact role and whether they influence the theoretical-week calculation.

---

## Q14 — What do the `Ind*` fields mean?

Relevant fields:

```text
IndTissu
IndTissuSec
IndFourniture
IndFil
IndOkProd
IndSemPiq
```

Important question:

> Are these indicators describing component requirement, component availability, validation status, or something else?

They should not become implementation rules until validated.

---

# 7. Priority 2 — Quantity and Stock

## Q15 — Is quantity part of availability calculation?

The stock table contains:

```text
Qte
```

and other data sources contain quantities such as:

```text
Besoin
QteResev
PrevStock
```

We need to determine whether availability means:

```text
quantity exists
```

or:

```text
sufficient quantity exists
```

For example:

```text
Required quantity = 1000
Available quantity = 500
```

Is the component considered available?

Probably not, but this must be confirmed.

---

## Q16 — How are several stock records aggregated?

A POI/component may potentially correspond to several stock movements or records.

We need to know whether availability is determined using:

```text
SUM(Qte)
```

or another aggregation rule.

---

## Q17 — How are partial receptions handled?

Example:

```text
Required = 1000

Reception 1 = 400
Reception 2 = 600
```

Does availability become:

```text
date of reception 2
```

because total quantity reaches 1000?

If yes, this is a major part of the availability algorithm.

---

# 8. Priority 2 — Orders and Receptions

## Q18 — How are purchase orders linked to POIs?

Potential identifiers include:

```text
POI_Sim
NCde
Code_Sim
POIntern
```

The exact join path must be validated.

We must avoid creating joins based only on similar-looking identifiers.

---

## Q19 — Which date represents actual availability?

Possible candidates include:

```text
DateCde
DateLivr
DateAccesoire
reception dates
availability dates
```

We need to distinguish:

```text
Order date
Expected delivery date
Actual reception date
Availability date
Production-ready date
```

These are not necessarily equivalent.

---

# 9. Priority 2 — Historical and Manual Values

## Q20 — Can historical theoretical dates be manually modified?

The POI table contains fields such as:

```text
DateMaxMan
DateTissuMan
DateTissuSecMan
DateFournitureMan
DateFilMan
DateOkProdMan
```

We need to know:

- Are these fields actively used?
- Who modifies them?
- Do manual values override calculated values?
- Should the new simulator reproduce manual corrections?

---

## Q21 — Is `SemTheorique` always an automatically calculated value?

If manual intervention exists, historical `SemTheorique` may not represent a purely algorithmic result.

We therefore need to know:

```text
automatic result
        vs
manual correction
```

This distinction is important when validating the new simulator.

---

# 10. Priority 2 — Scope and Filtering

## Q22 — What POIs should the simulator process?

Should it process:

```text
all historical POIs
```

or only:

```text
POIs belonging to selected simulations?
POIs within a study period?
POIs with specific statuses?
POIs with specific categories?
```

The filtering criteria must be explicit.

---

## Q23 — What is the study period?

The simulator should have a clearly defined input period:

```text
START_DATE
END_DATE
```

The source of these dates must be documented.

---

# 11. Priority 3 — Data Model

## Q24 — What is the official relationship between POI and stock?

We know:

```text
plan_t_simplanif
        1
        │
        │ Id_Sim
        │
        N
plan_t_simplanifpoi
```

and:

```text
plan_t_simplanif
        1
        │
        │ Id_Sim
        │
        N
plan_t_simplanifstock
```

But the exact business relationship:

```text
POI ↔ Stock
```

still needs validation.

---

## Q25 — Are there additional source tables required?

The currently available data may not contain everything needed to independently reproduce the component availability dates.

We need to determine whether the company has additional sources for:

- fabric orders,
- fabric receptions,
- accessories,
- thread,
- production approval,
- stock,
- POI/product information.

---

# 12. Priority 3 — Performance

## Q26 — What is the actual performance problem?

The project objective is to minimize simulation calculation time.

We need to identify whether the current or expected bottleneck comes from:

```text
data loading
joins
database queries
aggregation
availability calculations
simulation logic
file I/O
network access
```

The first implementation should measure these components rather than assuming the bottleneck.

---

## Q27 — What is the expected dataset scale?

We need approximate values for:

```text
Number of simulations
Number of POIs
Number of stock records
Number of orders/receptions
Total data size
```

This will determine whether local processing is sufficient and where Hadoop MapReduce could provide value.

---

# 13. Priority 3 — Hadoop

## Q28 — What exactly must be distributed?

The project requires Hadoop MapReduce.

However, we should identify which processing stage is suitable for MapReduce.

Potential candidate:

```text
POI-level availability calculation
```

but this must be determined after profiling the baseline.

The project should not distribute processing simply because Hadoop is mandatory.

---

## Q29 — What performance metric should be compared?

At minimum:

```text
Baseline execution time
Optimized execution time
MapReduce execution time
```

Potential additional metrics:

```text
Speedup
Throughput
CPU usage
Memory usage
Data volume
```

The comparison methodology should be defined before benchmarking.

---

# 14. Questions to Ask the Engineer First

Not every question needs to be asked simultaneously.

The recommended first discussion should focus on these **10 critical questions**:

1. How is `DateTissu` calculated?
2. How is `DateTissuSec` calculated?
3. How is `DateFourniture` calculated?
4. How is `DateFil` calculated?
5. How is `DateOKProduction` calculated?
6. How do we determine whether each component is required?
7. What does `NULL` mean for a required component?
8. Does `DateMax` correspond to the maximum required availability date?
9. How exactly is `SemTheorique` derived from the theoretical date?
10. Are historical/manual values able to modify the automatically calculated result?

These answers unlock most of the core business logic.

---

# 15. Information Required From the Engineer

Ideally, the engineer should provide:

### Business rules

```text
Component requirement rules
Availability rules
Quantity rules
Blocking rules
Week calculation rules
Missing-data rules
Manual override rules
```

### Data mapping

```text
Business concept
        ↓
Source table
        ↓
Column
        ↓
Transformation
```

### Examples

At least 3–5 real POIs showing:

```text
Input data
        ↓
Component availability
        ↓
DateMax
        ↓
SemTheorique
```

Including:

- one normal case,
- one missing-component case,
- one multi-reception case,
- one manual/corrected case if applicable,
- one case with multiple blockers.

---

# 16. Validation Record

Every answer received from the engineer should be documented.

Recommended format:

| Question | Answer | Source | Confidence | Impact |
|---|---|---|---|---|
| Q1 | ... | Engineer | Confirmed | High |
| Q2 | ... | Engineer | Confirmed | High |
| Q3 | ... | Engineer | Confirmed | High |

Possible confidence levels:

```text
CONFIRMED
OBSERVED
INFERRED
UNRESOLVED
```

This creates a traceable link between business discussions and implementation decisions.

---

# 17. Rule-Change Principle

If a future discussion contradicts an existing assumption, the implementation must follow the newly validated business rule.

The documentation should then be updated.

For example:

```text
Initial hypothesis:
SemTheorique = ISO week(DateMax)

Engineer clarification:
Company uses production week.

Action:
Update business rule documentation
Update implementation
Update tests
Update report
```

This prevents undocumented business logic from accumulating inside the code.

---

# 18. Final Decision Gate

The simulator should not move from **business analysis** to **final implementation** until the following are sufficiently understood:

```text
✓ Required components
✓ Component availability logic
✓ Quantity rules
✓ Missing-data behavior
✓ DateMax logic
✓ SemTheorique conversion
✓ Blocking-element rule
✓ Historical/manual override behavior
✓ Required source tables
✓ Valid POI scope
```

Once these points are validated, the project can proceed to:

```text
Data Preparation
        ↓
Baseline Simulator
        ↓
Validation
        ↓
Benchmark
        ↓
Optimization
        ↓
Hadoop MapReduce
```

---

# 19. Working LLM Constraint

The working/developer LLM must not invent answers to the questions in this document.

For every unresolved point, it must explicitly state:

```text
OPEN QUESTION
```

and continue only with logic that is independent of the unresolved rule.

If a hypothesis is necessary for experimentation, it must be labeled:

```text
HYPOTHESIS
```

and must not be presented as confirmed business logic.

This separation is mandatory for maintaining the correctness and credibility of the final internship project.