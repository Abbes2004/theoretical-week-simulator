# TASK 1 — Deep Analysis of the Three Raw SQL Sources

**Scope:** Phase 1 — Data Understanding only. No business logic implemented, no simulator, no Hadoop.
**Method:** The three raw SQL dumps were parsed directly (custom INSERT-tuple parser, not a guess) and loaded into a local SQLite database for real, reproducible querying. All numbers below come from actual query results, not from the MD documentation.

**Files analyzed:**
```
plan_t_simplanif.sql        (165 KB,  431 records)
plan_t_simplanifpoi.sql     (6.5 MB, 12,302 records)
plan_t_simplanifstock.sql   (18 MB, 116,200 records)
```

Row counts, schemas and every figure below are OBSERVED (directly queried), unless explicitly marked CONFIRMED (from project docs/spec), INFERRED, HYPOTHESIS, or UNKNOWN.

---

## A. Executive Summary

The three files are **not a consistent, joinable snapshot of the same period**. This is the single most important discovery of this task:

- `plan_t_simplanif` (431 rows) covers simulations `Id_Sim` **10775–12039**, created between **2025‑07‑30** and **2026‑03‑31**.
- `plan_t_simplanifpoi` (12,302 rows) contains **only one simulation, `Id_Sim = 5601`**, extracted **2021‑10‑14**. This `Id_Sim` does not exist anywhere in `plan_t_simplanif`.
- `plan_t_simplanifstock` (116,200 rows) spans `Id_Sim` **3322–10876** (34 distinct simulations) and dates from **2020‑07‑01** to **2025‑08‑29**.

Consequently:
- **0 of 12,302 POI rows** can be joined to `plan_t_simplanif` via `Id_Sim` (0% match rate).
- Only **105,895 of 116,200 stock rows** (91%) join to `plan_t_simplanif`, and that coverage is driven almost entirely by the 33 simulations in the 10775–10876 range; the rest (`Id_Sim` 3322, 4826, 5601, 6948, 7586 — 10,305 rows) are orphaned relative to `plan_t_simplanif`.
- The **one simulation that does exist in both POI and Stock (`Id_Sim = 5601`)** was usable to test the POI↔Stock relationship directly (see section E).

A second major discovery: in the POI table, the fields that are supposed to carry the core business result — `DateTissu`, `DateTissuSec`, `DateMax`, `SemTheorique`, `SemTheoriqueCoupe` — are **100% NULL across all 12,302 rows**. The `Ind*` indicator fields are **100% equal to 0** for every row. Only 18 of the 80 columns contain any non-null/non-zero data at all. This means **the provided POI extract cannot be used to validate the `SemTheorique` formula** — there is no historical reference value anywhere in this file to compare against.

This does not mean the business rule described in the specification is wrong. It means **this particular extract is the wrong instrument to validate it**, most likely because it captures a single simulation very early in its lifecycle (see section D.3) and/or a different extraction script/time window than the other two files.

---

## B. Data Model — What Is Actually Confirmed by Data

```
plan_t_simplanif   (431 rows,  Id_Sim 10775–12039, dates 2025-07-30 → 2026-03-31)
        |
        | Id_Sim  — 0/12,302 POI rows match  (NOT DEMONSTRATED in this extract)
        | Id_Sim  — 105,895/116,200 stock rows match (91%, DEMONSTRATED for overlapping Id_Sim only)
        ▼
plan_t_simplanifpoi     (12,302 rows, single Id_Sim = 5601, extracted 2021-10-14)
plan_t_simplanifstock   (116,200 rows, 34 distinct Id_Sim, 2020-07-01 → 2025-08-29)
```

- **Simulation → Stock via `Id_Sim`**: structurally demonstrated where the `Id_Sim` ranges overlap. STRONGLY SUPPORTED, not fully confirmed end-to-end because ~9% of stock still doesn't match.
- **Simulation → POI via `Id_Sim`**: **NOT DEMONSTRATED** in this dataset (0% match). This relationship remains a schema-level candidate only, unverifiable with the files as provided.
- **POI → Stock direct join**: tested explicitly for the one shared simulation (`Id_Sim = 5601`). Result: **0 matches** between `POI_Sim` and `Code_Sim`. See section E — this is real negative evidence, not an assumption.

---

## C. Table-by-Table Analysis

### C.1 `plan_t_simplanif` (431 rows)

- **Grain confirmed**: 431 distinct `Id_Sim`, no duplicates. PK `Id_Sim` holds.
- `Type_Sim`: `Globale` (251), `Partielle` (180). OBSERVED, matches doc.
- `Categ_Sim`: `Piquage` (341), `Devellopement B.W.` (34), `Repassage` (33), `Devellopement A.W.` (23). OBSERVED — dominant category is production stitching (`Piquage`), but a meaningful minority are "Development" simulations, which is important context for interpreting sparse POI data (see D.3).
- `Sem_Sim` format CONFIRMED as `YYYYWW` (e.g. `202531`, `202601`), continuous from `202520` to `202614`, **except for one outlier value `202651`** (week 51 of a year not otherwise present in the sequence) — flagged as **SUSPICIOUS_DATA**, not investigated further.
- Boolean-looking status fields (`Creat_Sim`, `Valid_Sim`, `Annul_Sim`, `Cloture_Sim`, `NewPOI_Sim`, `Regr_Sim`) only ever take values **`-1` or `0`** in this data — never `1`. This CONFIRMS the existing documentation's warning: `-1` is very likely the legacy "True" encoding (VB/Access-style boolean), `0` is "False". This is INFERRED from consistent pattern, not confirmed by an engineer.
- `Dat_Cal_Tissu` populated in 346/431 rows (80%), `Dat_Cal_Fourniture` in 390/431 (90%) — these are simulation-level "calculation run" timestamps, not POI-level availability dates. Their exact algorithmic meaning is UNKNOWN.
- `SemTheorique` is **confirmed absent** from this table (schema does not contain it) — matches documentation.

### C.2 `plan_t_simplanifpoi` (12,302 rows, single `Id_Sim = 5601`)

- **Schema**: 80 columns (vs. the ~55 explicitly listed in the data dictionary). The additional columns are mostly the `*_old` / `*_Manuel` pairs (`DateTissu_old/_Manuel`, `DateTissuSec_old/_Manuel`, `DateFourniture_old/_Manuel`, `DateFil_old/_Manuel`, `DateOKProduction_old/_Manuel`, `DateMax_old/_Manuel`), which **do exist as real columns** — CONFIRMED BY SQL, resolving previous "observed only" status in the documentation.
- **Grain confirmed**: `(Id_Sim, POI_Sim)` unique, 0 duplicates, 12,302 distinct `POI_Sim` values. `POI_Sim` values are 12–13 character alphanumeric codes ending in `CD` (e.g. `0133898091CD`).
- **Null / zero coverage across all 80 columns** (n = 12,302):

| Column | Populated rows | % |
|---|---:|---:|
| `Id_SimPoi`, `Id_Sim`, `POI_Sim`, `BesoinTissu`, `CrtDateAuto` | 12,302 | 100% |
| `EtapeFH` | 113 | 0.9% |
| `Priorite_Sim` / `Priorite_Racine` | 50 | 0.4% |
| `DateOKProduction` / `EtatOkProduction` / `StatutOkProduction` | 50 | 0.4% |
| `StatutFil` | 74 | 0.6% |
| `EtatFil` | 32 | 0.3% |
| `DateFil` | 29 | 0.2% |
| `LastFil` | 5 | 0.04% |
| `EtatFourniture` | 12 | 0.1% |
| `DateFourniture` / `StatutFourniture` | 9 | 0.07% |
| **`DateTissu`, `DateTissuSec`, `DateMax`, `SemTheorique`, `SemTheoriqueCoupe`, all `Ind*`, all `IdSim_Racine`, all manual/old date fields, `ValidationPOI`, `DecisionPOI`, `NCdeTU/TSec/FN`** | **0** | **0%** |

  **This is the central data-quality finding of this task**: the two fields the whole project is built around (`SemTheorique`, `DateMax`) are completely empty in this file, and the two "MAX-formula" inputs `DateTissu`/`DateTissuSec` are also completely empty. `BesoinTissu` (fabric requirement quantity) is fully populated and looks like real data (range 0–3,451.94, mean ≈ 18.9, only 91/12,302 rows at exactly zero).
- `Ind*` fields (`IndTissu`, `IndTissuSec`, `IndFourniture`, `IndFil`, `IndOkProd`, `IndSemPiq`) are **literally `0` for every single row** — this dataset gives **zero evidence** about what these indicators mean or how they behave; any interpretation of them would be pure speculation.
- `Etat*` fields do **not** behave as simple categorical state codes for every column. `EtatOkProduction` values observed (`'18/10/2021'`, `'16/10/2021'`, etc.) are **DD/MM/YYYY-formatted dates that exactly match the corresponding `DateOKProduction` value** (e.g., row with `DateOKProduction='2021-10-18'` has `EtatOkProduction='18/10/2021'`). This **contradicts** the documentation's assumption that `Etat*` fields are generic status codes — for `EtatOkProduction` at least, it appears to be a display/mirror of the date itself, not an independent status. `EtatFourniture`/`EtatFil` mix this same date-mirroring behavior with a small number of genuine textual states: `'Sortie'` and `'Manque FH'` (French: "issued/exit" and "missing/FH-shortage"). **CONTRADICTION flagged, requires engineer validation.**
- `StatutFourniture`, `StatutFil`, `StatutOkProduction` use **single-letter codes**: `'S'` (Fourniture: 9/9 rows, Fil: 74/74 rows) and `'R'` (OkProduction: 50/50 rows). Plausibly "Sorti" (issued) and "Réalisé"/"Reçu" (done/received) but this is **HYPOTHESIS only** — no confirmed dictionary exists for these letters.
- `LastFil` contains genuine thread specification strings (e.g. `"YT08654:1712 Tex 60 Epic"`) — CONFIRMED as a material reference, not a date or status.
- `EtapeFH` contains development-process stage labels: `Cotation(1)` (58), `Proto(1)` (45), `Collection(1)` (5), `Proto(2)` (2), `Manque FH` (3) — French apparel terms for **Costing/Quotation** and **Prototype/Sample** stages. This is a strong, previously undocumented clue (see D.3) that this particular simulation may be a **development/sampling** simulation rather than a full production `Piquage` simulation, which would explain the near-total absence of `Tissu`/`Fourniture`/`Fil`/`OKProduction`/`SemTheorique` data.
- **Ordering test of the MAX-date hypothesis**: 34 POI rows have at least two of `{DateFourniture, DateFil, DateOKProduction}` populated simultaneously (the only combination with enough co-occurring data to test). In 31/34 rows `DateOKProduction` is the latest of the populated dates, consistent with "OK Production is usually last." But in **3/34 rows, `DateOKProduction` is earlier** than `DateFourniture` (e.g. POI `01028121081CD`: `DateFourniture=2021-10-14`, `DateOKProduction=2021-08-22`). This is **direct evidence against always trusting `MAX()` == `DateOKProduction`**, and against assuming OK Production is inherently the last/blocking gate. We could **not** test the full 5-component MAX formula against `SemTheorique` because `SemTheorique` and `DateMax` are always NULL in this file.

### C.3 `plan_t_simplanifstock` (116,200 rows, 34 distinct `Id_Sim`)

- **Grain confirmed**: PK `Id_stock` unique; declared unique key `(Id_Sim, Code_Sim, Taille_Sim, Date_Sim, Client)` holds with **0 violations** in this dataset.
- `Client` field (top values): `Sartex` (98,887 rows, **85%**), then real apparel brands: `HUGO BOSS` (3,350), `PME LEGEND` (3,240), `DENIM HOUSE` (3,174), `RALPH LAUREN` (1,940), `GUESS EUROPE` (1,348), `7 FOR ALL MANKIND`, `LACOSTE`, `VANGUARD`, `DIESEL KIDS`, `MARC O POLO`, `BRAX`, etc.
  **Key finding**: `Sartex` is not a brand — it is almost certainly the name of the textile mill / internal fabric-supplier entity (consistent with the Tunisian textile-manufacturing context of this project). This means the `Client` column in the stock table **conflates two different roles**: (a) the actual end-client/brand that owns/reserved certain stock rows, and (b) the supplier/mill holding the (much larger) bulk of the stock. **This contradicts the plain reading of `Client` as "the client"** in the data dictionary, and is important: any POI↔stock matching logic that filters "stock for this client" must first decide whether `Sartex` rows are in scope. **CONTRADICTION / open question flagged.**
- `Taille_Sim` (size): empty string in 84,839/116,200 rows (73%); populated with real garment/fabric sizes otherwise (`29`,`30`,`32`, combined waist/length like `3232`, or letter sizes `M`,`L`). CONFIRMS this is a genuine size field, but it is optional/inapplicable for the majority of rows — likely because bulk fabric stock (measured in meters/kg) has no size dimension while cut-piece/garment stock does.
- `Qte`: range **-15,140 to 50,154,000**, mean ≈ 28,145. **6,005 rows (5%) have negative quantity**, **24,287 rows (21%) are exactly zero**. Negative and zero values were NOT cleaned — they are preserved and flagged. The huge range strongly suggests **mixed units** across rows (fabric in meters, thread in a different unit, accessories in pieces) — a simple `SUM(Qte)` across `Code_Sim` would not be meaningful without first normalizing by material type/unit. **HYPOTHESIS, needs business confirmation.**
- `Code_Sim`: 7,331 distinct values. Two visibly different code shapes coexist: long numeric EAN-like codes (e.g. `437149199001`, seen for `Id_Sim=3322`/HUGO BOSS) and short alphanumeric brand-prefixed codes (`PME00004`, `H12400`, `VGD00014`, `GU04510`) seen for other simulations. This suggests `Code_Sim` **may represent different business objects depending on the simulation/client** (fabric article code in some cases, style/product reference in others) — this is an important, previously undocumented ambiguity. **OPEN QUESTION, high priority.**
- `NCde`: populated (non-NULL) in 113,162/116,200 rows, but many of those are **empty strings**, not real order numbers; where filled, values look like real order references (e.g. `2722014367`).
- Stock rows per simulation range from 125 to 4,078 in this extract — highly uneven, consistent with the "large variance" risk flagged in the project documentation for later performance work.

---

## D. `SemTheorique` — Evidence Summary

| Question | Evidence found | Status |
|---|---|---|
| Does `SemTheorique` exist and get populated? | Column exists (CONFIRMED BY SQL); **0/12,302 rows populated** in this extract | Cannot be evaluated from this file |
| Does `DateMax` exist and get populated? | Column exists; **0/12,302 rows populated** | Cannot be evaluated |
| Is `DateMax` == `MAX(component dates)`? | Untestable — both sides of the comparison are empty for all rows that have any component date | **UNKNOWN — no evidence either way** |
| Is `DateOKProduction` always the latest/blocking component? | Tested on the 34 rows with 2+ co-populated dates: true in 31/34, **false in 3/34** | **HYPOTHESIS, contradicted in ~9% of testable cases** |
| Week-numbering convention for `SemTheorique` | No populated values to inspect | **UNKNOWN** |
| Tie-breaking rule for multiple max dates | No populated `DateMax`/`SemTheorique` to check against ties | **UNKNOWN** |

### D.3 Working hypothesis on *why* this file is empty (HYPOTHESIS — not confirmed)

Two independent signals point toward the same explanation:
1. `EtapeFH` values (`Cotation`, `Proto`, `Collection`) are development/sampling-stage labels, not production-planning labels.
2. `plan_t_simplanif.Categ_Sim` includes `Devellopement A.W.` / `Devellopement B.W.` categories (23 + 34 of 431 simulations) distinct from the dominant `Piquage` (production stitching) category.

It is plausible that `Id_Sim = 5601` was a **development/sampling simulation**, for which the fabric/supply/thread/OK-Production availability workflow and the `SemTheorique` calculation are either not run at all or not yet reached at the time of this 2021-10-14 extract. **This must be validated with the engineer — it is not confirmed.** If true, it would mean the simulator's scope needs an explicit filter (e.g., only `Categ_Sim = 'Piquage'` simulations, or only simulations with `Cloture_Sim = -1`) before the `SemTheorique` logic is meaningful.

---

## E. POI ↔ Stock Relationship — Direct Test

The only simulation present in both files is `Id_Sim = 5601` (12,302 POI rows / 185 stock rows).

- Stock `Code_Sim` values for `Id_Sim=5601` look like fabric-article codes with a brand prefix, e.g. `GU04510`, `GU13569`, `GU13152` ("GU" ≈ Guess).
- POI `POI_Sim` values for the same simulation are 12–13-character item codes, e.g. `0133898091CD`.
- **Direct join test `stock.Code_Sim = poi.POI_Sim` → 0 matches out of 185 stock rows.**
- `Client` breakdown within this one simulation: `Sartex` (176/185, 95%), `GUESS EUROPE` (5), `GUESS KIDS` (4) — again showing the supplier/mill (`Sartex`) holding the bulk of stock, with the brand appearing only for a handful of reserved/client-specific rows.

**Conclusion: there is no direct, demonstrable key between POI and Stock in the data as provided.** The relationship, if it exists, must go through an intermediate table/mapping not present in these three files (e.g. a BOM/nomenclature table linking `POI_Sim` to one or more `Code_Sim` fabric references). This matches and reinforces the existing documentation's caution (Data Model §9, Data Relationships §5) — it is now **backed by a concrete negative test**, not just a theoretical caveat.

---

## F. Data Quality Report (Observed Anomalies)

| # | Finding | Table | Severity |
|---|---|---|---|
| 1 | 12,302/12,302 POI rows have no `Id_Sim` match in `plan_t_simplanif` | POI | CRITICAL |
| 2 | `SemTheorique`, `DateMax`, `DateTissu`, `DateTissuSec` are 100% NULL | POI | CRITICAL |
| 3 | All `Ind*` indicator fields are always `0` | POI | HIGH |
| 4 | `EtatOkProduction` appears to mirror `DateOKProduction` as text, contradicting "status code" assumption | POI | HIGH |
| 5 | 3/34 testable rows show `DateOKProduction` earlier than `DateFourniture`, contradicting "OK Production is last" | POI | MEDIUM |
| 6 | `Client` field in stock conflates a supplier/mill name (`Sartex`, 85% of rows) with real brand clients | Stock | HIGH |
| 7 | `Qte` has 6,005 negative and 24,287 zero values; magnitude range spans 6 orders of magnitude, suggesting mixed units | Stock | MEDIUM |
| 8 | `Code_Sim` shape differs across simulations (long numeric vs. short alphanumeric), suggesting inconsistent semantics | Stock | MEDIUM |
| 9 | `Taille_Sim` empty in 73% of rows | Stock | LOW |
| 10 | One `Sem_Sim` outlier value `202651` breaks the otherwise continuous `YYYYWW` sequence | Simulation | LOW |
| 11 | Boolean-like fields use `-1/0`, never `1`, matching legacy convention warning already in the docs | Simulation | INFO (confirms existing doc) |
| 12 | Stock↔Simulation match rate 91%, not 100% (10,305 orphan stock rows relative to `plan_t_simplanif`) | Stock/Sim | MEDIUM |

No raw data was modified. All findings are read-only observations from the parsed dumps.

---

## G. Business Logic Evidence Matrix

| Business Rule | Evidence Found | Status |
|---|---|---|
| All required components must be available before production | No contradicting evidence found, but also no positive confirmation possible from this data (fields empty) | CONFIRMED BY SPEC ONLY — not verifiable from data |
| Theoretical date = MAX(component dates) | Untestable: `DateMax`/`SemTheorique` always NULL; partial ordering test on 34 rows shows the "latest = OK Production" pattern holds 31/34 times but not always | HYPOTHESIS — partially contradicted |
| Theoretical week derives from theoretical date | No populated `SemTheorique` to inspect at all | UNKNOWN |
| Blocking element = component with the latest date | Same 34-row test: OK Production is not always latest | HYPOTHESIS — partially contradicted |
| `Id_Sim` links Simulation → POI | 0/12,302 POI rows match `plan_t_simplanif` in this extract | NOT DEMONSTRATED (data-extraction artifact, not necessarily false in production DB) |
| `Id_Sim` links Simulation → Stock | 105,895/116,200 (91%) match | STRONGLY SUPPORTED |
| POI ↔ Stock joins directly on an identifiable key | Direct `POI_Sim = Code_Sim` test on the one shared simulation → 0/185 matches | REFUTED as stated; relationship (if any) requires an intermediate/BOM table not present here |
| `Client` in stock = the end client of the POI | 85% of stock rows are attributed to `Sartex`, which behaves like a supplier, not a brand | CONTRADICTED as a blanket rule |

---

## H. Open Questions (Prioritized)

**CRITICAL**
1. Why do the three files not share a consistent `Id_Sim` window? Are they independent exports taken at different times/for different purposes, and can we obtain a **single consistent full export** (all three tables, same extraction run, same period) for real end-to-end validation?
2. Is `Id_Sim = 5601` (the only POI simulation we have) a development/sampling simulation rather than a production one? If yes, should the simulator explicitly exclude `Categ_Sim` values like `Devellopement A.W./B.W.` from its scope?
3. Can we get at least one POI extract where `SemTheorique` and `DateMax` are actually populated, so the MAX-formula hypothesis can be tested against real historical values?

**HIGH**
4. What does `Client = 'Sartex'` actually represent in the stock table, and should Sartex-owned stock rows be included or excluded when computing a client's fabric availability?
5. What do `EtatFourniture`, `EtatFil`, `EtatOkProduction` actually encode — are they genuinely a mirror of the date field, or does that only hold for the OK-Production case?
6. What do `StatutFourniture`/`StatutFil`='S' and `StatutOkProduction`='R' mean?
7. Is `Code_Sim` a fabric/material code, a style code, or both depending on context? How should the simulator disambiguate?

**MEDIUM**
8. Is the `DateOKProduction < DateFourniture` pattern observed in 3/34 rows a data-entry error, a manual correction, or a legitimate business case (e.g., conditional/provisional OK Production)?
9. How should negative and zero `Qte` values in stock be interpreted (reservations, returns, corrections, true absence)?
10. Is the `Sem_Sim = 202651` value a typo, or does the company use a 53-week convention in some years?

**LOW**
11. Why is `Taille_Sim` blank for 73% of stock rows — is this simply "not applicable to fabric-level stock," and can that be confirmed?

---

## I. Recommendations for Next Phase

1. **Do not proceed to baseline-simulator implementation using these three files as-is for validation.** They cannot currently support an end-to-end SemTheorique reconstruction or historical match-rate measurement, because the reference field (`SemTheorique`) and the primary formula inputs (`DateTissu`, `DateTissuSec`, `DateMax`) are entirely empty in the only available POI extract, and the POI/Simulation `Id_Sim` ranges do not overlap.
2. **Request a single, time-consistent full export** of all three tables (ideally covering the same `Id_Sim` range and time window used in `plan_t_simplanif`, i.e. `Id_Sim` ≈ 10775–12039), so that POI↔Simulation and POI↔Stock relationships and the `SemTheorique` formula can actually be tested against real, populated data.
3. In parallel, it is still useful to build the **baseline simulator logic itself** (the MAX/week-conversion/blocking-element function) as a **pure, testable function** against synthetic/unit-test data, so that once a valid extract arrives, validation can start immediately. This does not violate "baseline before Hadoop" — it is preparing the baseline, not skipping validation.
4. Escalate the `Sartex`-as-client and `Code_Sim` ambiguity questions to the project owner/engineer before any stock-based availability logic is designed, since they directly affect what "available quantity" means.
5. The other provided files (`consommation_tissu_par_type.xlsx`, `table.xlsx`, `cde.xls`, the PO PDFs, and the internship report PDF) were not analyzed in this task (out of scope per Task 1's instructions, which focused on the three SQL sources). They should be examined next, specifically to look for a POI↔fabric/BOM mapping that could bridge the POI↔Stock gap identified in section E.
6. Suggested storage location in the project workspace for this report: `docs/data_profiling/TASK1_Raw_SQL_Deep_Analysis.md` (or equivalent existing profiling folder) — the local SQLite database used to produce these numbers can be regenerated at any time by re-running the parser against the raw SQL files, so it does not need to be committed as a permanent artifact.

---

## TASK 1 STATUS

**Inspected:**
- `plan_t_simplanif.sql` (431 rows, full schema, full column value distributions)
- `plan_t_simplanifpoi.sql` (12,302 rows, full 80-column schema, non-null/non-zero coverage for every column)
- `plan_t_simplanifstock.sql` (116,200 rows, full schema, key field distributions)
- Cross-table referential integrity (`Id_Sim` joins) between all three tables
- Direct POI↔Stock key test for the one shared simulation

**Confirmed:**
- Primary keys and unique constraints hold with zero violations in all three tables.
- `SemTheorique` does not exist in `plan_t_simplanif` (only in POI table).
- `*_old` / `*_Manuel` manual-date column pairs genuinely exist in the POI schema.
- Boolean-like simulation status fields use `-1/0`, never `1`.
- `Sem_Sim` follows a `YYYYWW` convention (with one anomaly).

**Observed:**
- 0% POI↔Simulation match rate in this extract; 91% Stock↔Simulation match rate.
- `SemTheorique`/`DateMax`/`DateTissu`/`DateTissuSec` are 100% NULL across all 12,302 POI rows; `Ind*` fields always 0.
- `Client='Sartex'` dominates 85% of stock rows.
- Direct `POI_Sim = Code_Sim` join yields 0 matches on the one shared simulation.

**Inferred:**
- `Id_Sim=5601` is plausibly a development/sampling simulation, not a production one (from `EtapeFH` values).
- `EtatOkProduction` is plausibly a text-mirror of `DateOKProduction`, not an independent status code.
- `Code_Sim` may denote different business objects (fabric code vs. style code) depending on the simulation.

**Hypotheses (explicitly unconfirmed):**
- `DateTheo = MAX(5 component dates)` — partially supported (31/34), partially contradicted (3/34), and untestable against the actual `SemTheorique`/`DateMax` fields in this file.
- `StatutFourniture/Fil='S'` and `StatutOkProduction='R'` meanings.
- Stock quantity aggregation/unit-normalization needs.

**Unknown:**
- Real POI↔Stock join key/path.
- Week-numbering and tie-breaking conventions for `SemTheorique` (no populated example to inspect).
- Meaning of all `Ind*` fields (no non-zero example exists in this file).

**Contradictions vs. existing documentation:**
- `Client` (stock) ≠ "the client" as a blanket rule (85% is a supplier, `Sartex`).
- `Etat*` fields are not uniformly categorical status codes; at least `EtatOkProduction` mirrors a date.
- POI table has 80 real columns including confirmed manual/old fields, more than the ~55 previously enumerated in the data dictionary as a "critical subset."

**Data quality issues:** see section F (12 findings, 3 CRITICAL/HIGH-severity groups).

**Files created/modified:**
- `TASK1_Raw_SQL_Deep_Analysis.md` (this report; new file, no existing equivalent found).
- No raw SQL or existing documentation files were modified.
- A working SQLite database and parser script were created in a scratch/session directory for analysis only; not part of the permanent workspace deliverable.

**Critical decisions requiring project-owner validation:**
- Whether the three SQL exports can be regenerated as one consistent, joinable snapshot for real validation.
- Whether `Id_Sim=5601` should be excluded from `SemTheorique` scope as a development simulation.
- The correct interpretation of `Client='Sartex'` in the stock table and of `Code_Sim` semantics.

**Recommended next step:**
Obtain a single time-consistent export of all three tables (or at minimum, one `plan_t_simplanif` + matching `plan_t_simplanifpoi` pair with populated `SemTheorique`) before attempting any historical validation. Do not begin baseline-simulator implementation intended for validation purposes until that data is available; building the pure calculation function against unit tests can proceed in parallel.
