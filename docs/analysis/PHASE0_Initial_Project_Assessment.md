# PHASE 0 — Initial Project Assessment

**Date:** 2026-09-08
**Scope:** Workspace inspection, documentation review, raw-data verification, planning. No simulator code, no business logic implementation, no Hadoop.
**Method:** Every number in this document was re-derived from the raw files in this session by `scripts/profile_raw_sql.py` (SQL dumps), pandas + openpyxl/xlrd (Excel), and pypdf (PDF). Raw data was opened read-only; nothing under `data/raw/` was modified.

Evidence labels used: `CONFIRMED`, `OBSERVED`, `INFERRED`, `HYPOTHESIS`, `SYNTHETIC`, `RECOMMENDATION`, `UNKNOWN`.

---

## 1. WORKSPACE INVENTORY

Directory skeleton matches `MASTER_PROMPT.md` §3 exactly. All source, test, config, notebook, benchmark, and output directories exist and are **empty**.

| Path | State |
|---|---|
| `MASTER_PROMPT.md` | present, 19.7 KB |
| `README.md` | present, **0 bytes** |
| `requirements.txt` | present, **0 bytes** |
| `.gitignore` | present, 518 B — ignores `outputs/`, `data/interim/`, `data/processed/`, `data/raw/`, `benchmarks/{datasets,baseline,optimized,mapreduce}/` |
| `src/{business,ingestion,mapreduce,optimization,preprocessing,simulation}/` | empty (no `__init__.py`) |
| `tests/{unit,integration,validation}/` | empty |
| `configs/`, `scripts/`, `notebooks/*`, `benchmarks/*`, `outputs/*` | empty |
| `data/{interim,processed,canonical}/` | empty |
| `data/raw/{sql,excel,pdf}/` | populated (see §3) |
| Git | 1 commit (`9be18bd Initial project workspace`), branch `main` |

**Note (OBSERVED):** `.gitignore` excludes `data/raw/` and `data/canonical/` is *not* excluded. Since `data/raw/` is untracked, the raw sources are not in Git history — they exist only on this machine. `docs/context/*` and `docs/data_dictionary/*` show as deleted-and-re-added in git status: the previous `docs/data_dictionary/` folder was moved to `docs/context/` plus new `docs/analysis/`, `docs/cahier_des_charges/`, `docs/execution/` folders, none of which are committed yet.

**Python environment:** Python 3.14.4, pandas 3.0.2, numpy 2.4.4 already present. `openpyxl 3.1.5`, `xlrd 2.0.1`, `pypdf 5.1.0` installed during this assessment (needed to read the Excel/PDF sources). Missing and needed later: `pytest`, a web framework (`flask` or `streamlit`), optionally `pyarrow`.

---

## 2. DOCUMENTATION INVENTORY

25 files, all read in this session.

### `docs/context/` (13 files) — business/data specification layer
| File | Content | Verified against raw data? |
|---|---|---|
| `project_context.md` | Project overview, objective, sources, dev strategy | yes — table/field names match actual schemas |
| `Business Rules.md` | The `MAX()` rule, blocking element, tie case, confirmed-vs-unconfirmed matrix | yes |
| `Theoretical Week (SemTheorique).md` | Deepest treatment of the target calculation, validation metrics, 19 open questions | yes |
| `Business Logic to Data Mapping.md` | Business element → column mapping | yes |
| `Data Dictionary.md` | Field-by-field dictionary (~55 fields flagged as "critical subset") | partially — actual POI table has **80** columns |
| `Data Model.md` | Grain, PKs, uniqueness, relationships | yes — PK/unique claims re-verified, all hold |
| `Data Relationships.md` | Join candidates and their support level | yes |
| `Data Profiling.md` | Profiling expectations | yes |
| `Edge Cases & Data Quality Handling.md` | Status vocabulary (`VALID_RESULT`/`INCOMPLETE_DATA`/`INVALID_DATA`/`NOT_APPLICABLE`/`AMBIGUOUS`), null/invalid-date policy | n/a (policy doc) |
| `Open Questions & Business Validation.md` | 29 numbered open questions Q1–Q29 with priorities | n/a (question register) |
| `plan_t_simplanif.md`, `plan_t_simplanifpoi.md`, `plan_t_simplanifstock.md` | Per-table reference docs | yes |

### `docs/analysis/` (2 files) — prior investigation
- `TASK1_Raw_SQL_Deep_Analysis.md` (27.5 KB) — deep analysis of the three SQL dumps.
- `TASK2_Supporting_Sources_Business_Mapping.md` (35 KB) — Excel + PDF analysis and cross-source mapping.

**Verification of prior analysis (this session):** I re-derived the key claims independently. **All headline numbers in TASK1 and TASK2 reproduce exactly.** Specific re-verified items are marked ✅ in §5–§7 below. Two claims needed correction/refinement — see §7 items DQ-13 and DQ-14, and §11 "Corrections to prior documentation".

### `docs/cahier_des_charges/` (1 file)
`RapondStageSimulateurDisponibilite.pdf` → actual filename `RapportStageSimulateurDisponibilite.pdf`, 5 pages, dated 18 August 2026, French. Read in full this session.

**CONFIRMED — this is the assignment brief, not a prior intern's report.** Content directly relevant:
- §1 states the rule verbatim: *"la production ne peut commencer que lorsque tous les éléments nécessaires sont disponibles"* → theoretical week = latest week among the required elements. Worked example: Tissu principal S35, Tissu secondaire S34, Accessoires S36, Fils S35, OK Prod S33 → **S36**, blocking = Accessoires.
- §3.2 Mission 2 explicitly authorises *"Création ou utilisation d'une base de données simulée"* with the toy schema `{PO_ID, Ref_Article, Tissu_Principal, Tissu_Secondaire, Accessoires, Fils, OK_Prod, Semaine_Theorique}` and weeks as text `S32`…`S52`. **This is the single most important scope fact in the brief: a simulated dataset is an accepted deliverable.**
- §3.3 Mission 3: `Semaine théorique = max(Tissu Prin., Tissu Sec., Accessoires, Fils, OK Prod)`, and the programme must isolate the blocking element.
- §3.4 Mission 4: must handle missing dates, corrupt/incorrectly-formatted data, incomplete PO, and PO outside the studied period.
- §3.5 Mission 5: simple GUI or web UI — Tkinter, Flask, or Streamlit.
- §4: Hadoop/HDFS is `Découverte` (discovery) level, on "several tens or hundreds of thousands of *simulated* POs", explicitly to compare sequential local vs distributed.
- §5: six deliverables — analysis document, simulated dataset, commented+tested calculation program, working UI, Hadoop/HDFS PoC, full report.
- §6: mandatory stack Python, SQL, CSV/JSON, SQLite, Git; discovery stack Hadoop, HDFS, MapReduce, PySpark.

### `docs/execution/` (9 files, `08`–`16`) — execution specifications
`08_canonical_dataset_specification.md`, `09_pipeline_architecture.md`, `10_simulator_specification.md`, `11_benchmarking_plan.md`, `12_hadoop_mapreduce_plan.md`, `13_testing_strategy.md`, `14_report_structure.md`, `15_working_llm_instructions.md`, `16_execution_checklist.md`. All read. These are concrete and directly implementable; the canonical schema in `08` and the calculation contract in `10` are the design I will follow.

**Documentation gap (OBSERVED):** `docs/architecture/`, `docs/business_rules/`, `docs/decisions/`, `docs/report/` exist but are empty. Files `01`–`07` of the `docs/execution/` numbering series are absent — the `docs/context/` files carry those numbers internally (`Theoretical Week` is titled "08", `Edge Cases` is "09", `Open Questions` is "10"), so the numbering is inconsistent across folders but no content is actually missing.

---

## 3. RAW DATA INVENTORY

All figures re-derived this session. Full log: `outputs/logs/phase0_raw_profile.txt`.

### 3.1 SQL — `data/raw/sql/` (24.9 MB total)

All three are MySQL dumps from `Source Host: 192.168.0.50`, `Database: production`, exported **31/03/2026** within 18 seconds of each other (11:04:13 / 11:04:20 / 11:04:38). ✅ This is new detail: the three files were exported in **one extraction run**, so the period mismatch below is *not* an artifact of three separate exports at three different times — it reflects what those tables actually contained on 31/03/2026.

| File | Size | Rows | Cols | Grain / key | Verified |
|---|---:|---:|---:|---|---|
| `plan_t_simplanif.sql` | 165 KB | 431 | 36 | PK `Id_Sim`, 431 distinct, 0 dups | ✅ |
| `plan_t_simplanifpoi.sql` | 6.8 MB | 12,302 | 80 | PK `Id_SimPoi`; UNIQUE `(Id_Sim, POI_Sim)` holds, 0 violations | ✅ |
| `plan_t_simplanifstock.sql` | 17.9 MB | 116,200 | 9 | PK `Id_stock`; UNIQUE `(Id_Sim, Code_Sim, Taille_Sim, Date_Sim, Client)` holds, **0 violations** | ✅ |

**`plan_t_simplanif` (431 rows)** — OBSERVED:
- `Id_Sim` 10775–12039; `Date_Sim` 2025-07-30 09:42:49 → 2026-03-31 11:00:55.
- `Type_Sim`: Globale 251 / Partielle 180. `Categ_Sim`: Piquage 341 / Devellopement B.W. 34 / Repassage 33 / Devellopement A.W. 23.
- Boolean-ish fields take only `-1` and `0`, never `1`: `Cloture_Sim` (-1: 358), `Creat_Sim` (-1: 415), `Valid_Sim` (-1: 14), `Annul_Sim` (-1: 12), `NewPOI_Sim` (-1: 20), `Regr_Sim` (-1: 34). ✅ legacy `-1 = TRUE` convention.
- `Sem_Sim`: 38 distinct, `YYYYWW`, 202520→202614, plus the single outlier **`202651`**. ✅
- `Etat_Element`: `Semaine` 324, `''` 56, `Date` 49, and two garbage values **`^c`** and **`c`** (1 row each). 🔴 **New finding, not in prior docs** — evidence of free-text corruption in a control field.
- `Typ_Sem_Sim` null in 406/431; `Dat_Cal_Tissu` 346/431; `Dat_Cal_Fourniture` 390/431.
- `Client_Sim` **null in 227/431 (53%)**; populated values are brands (BRAX 31, GUESS EUROPE 30, 7 FOR ALL MANKIND 26, RALPH LAUREN 22, …). 🔴 **New finding** — the simulation-level client is absent for over half the simulations.

**`plan_t_simplanifpoi` (12,302 rows, 80 columns)** — OBSERVED:
- **Single simulation: `Id_Sim = 5601` for all 12,302 rows.** `CrtDateAuto` 2021-10-14. ✅
- 12,302 distinct `POI_Sim`, **all ending in `CD`**, length 13 (11,915) or 12 (387). ✅
- **62 of 80 columns contain no usable value** (all NULL / `''` / `0`). ✅ Prior docs said "only 18 of 80 columns contain data" — exactly consistent.
- Component-date population:

| Column | Populated | % |
|---|---:|---:|
| `DateTissu` | **0** | 0% |
| `DateTissuSec` | **0** | 0% |
| `DateFourniture` | 9 | 0.07% |
| `DateFil` | 29 | 0.24% |
| `DateOKProduction` | 50 | 0.41% |
| `DateMax` | **0** | 0% |
| `SemTheorique` | **0** | 0% |
| `SemTheoriqueCoupe` | **0** | 0% |
| `BesoinTissu` | 12,302 | 100% |

- All `Ind*` fields (`IndTissu`, `IndTissuSec`, `IndFourniture`, `IndFil`, `IndOkProd`, `IndSemPiq`) = `0` in every row. ✅
- **Component-date co-occurrence (re-derived, more precise than prior docs):** 12,252 rows have **zero** component dates; 16 rows have 1; 30 rows have 2; 4 rows have 3; **0 rows have 4 or 5**. Populated combinations: `{DateFil, DateOKProduction}` 25, `{DateOKProduction}` 16, `{DateFourniture, DateOKProduction}` 5, `{DateFil, DateFourniture, DateOKProduction}` 4. ✅ **The full 5-component MAX has never been exercisable on real data — not in a single row of the 12,302.**
- MAX-ordering test on the 34 rows with ≥2 dates: `DateOKProduction` is the max in **31/34**; in **3/34** it is earlier than `DateFourniture`. ✅ Counterexamples re-derived: `01028121081CD` (Fourniture 2021-10-14, OKProd 2021-08-22), `03028121081CD` (2021-10-14 / 2021-08-30), `06028120642CD` (2021-10-14 / 2021-09-08).
- `EtatOkProduction` vs `DateOKProduction`: **50/50 exact match** when parsed as `%d/%m/%Y`, 0 mismatches. ✅ CONFIRMED: for OK Production, `Etat*` is a `dd/mm/yyyy` text mirror of the date, not an independent status code.
- `EtatFil` (32 populated): `14/10/2021` ×28, `Manque FH` ×3, `Sortie` ×1. `EtatFourniture` (12): `Sortie` ×8, `Manque FH` ×3, `14/10/2021` ×1. ✅ Mixed semantics — same column holds either a mirrored date or a French status word.
- `StatutFourniture` = `S` (9/9), `StatutFil` = `S` (74/74), `StatutOkProduction` = `R` (50/50). ✅ Single-valued in this extract — zero discriminative information.
- `EtapeFH` (113 populated): `Cotation(1)` 58, `Proto(1)` 45, `Collection(1)` 5, `Proto(2)` 2, `Manque FH` 3. ✅
- `LastFil` (5 rows): `YT08654:1712 Tex 60 Epic` ×3, `YT33448: C9424 EPIC TEX 40`, `YT19147:C7953 Tex 24 Epic`.
- `Priorite_Sim` populated in only 50 rows (`1` ×32, `2` ×18) — and those are the **same 50 rows** that have `DateOKProduction`. 🔴 **New finding (INFERRED):** whatever process populated OK Production also set the priority; the two are co-populated, suggesting a single downstream workflow step touched exactly 50 POIs.
- All `*_old` and `*_Manuel` date columns exist in the schema (CONFIRMED by DDL) and are **entirely empty**.

**`plan_t_simplanifstock` (116,200 rows)** — OBSERVED:
- 34 distinct `Id_Sim`: 3322, 4826, 5601, 6948, 7586, then 10775…10876 (29 values).
- `Date_Sim` 2020-07-01 → **2025-10-31**; `CrtDateAuto` 2020-07-02 → 2025-08-29. 🔴 **Correction to prior docs:** TASK1 reported the stock date range as ending 2025-08-29 — that is the *insert* timestamp (`CrtDateAuto`) max, not `Date_Sim`. `Date_Sim` runs two months further, to **2025-10-31**, with **4,630 rows dated after the last insert timestamp**. ✅ INFERRED: `Date_Sim` is forward-looking (a projected/expected stock date), not a historical observation date. This matters for the availability logic — it means the stock table already contains future-dated availability rows.
- `Code_Sim`: 7,331 distinct; length distribution 7 → 97,764 / 8 → 9,338 / 6 → 8,973 / 12 → 125. Codes starting `YT` (case-insensitive): **60,451 (52%)**. ✅
- 🔴 **New finding:** **8 codes appear in both upper and lower case** (`YT16169`/`yt16169`, `UU00055`/`uu00055`, `GU13389`/`gu13389`, `HB09883`/`hb09883`, …) affecting **1,715 rows**. Distinct codes drop from 7,331 to 7,323 under case folding. Identifier normalisation is therefore not optional.
- `Client`: `Sartex` 98,887 (85%), then HUGO BOSS 3,350, PME LEGEND 3,240, DENIM HOUSE 3,174, RALPH LAUREN 1,940, GUESS EUROPE 1,348, 7 FOR ALL MANKIND 1,280, LACOSTE 689, … ✅
- `Qte`: min **-15,140.00**, max **50,154,000.00**, mean 28,145.05; **6,005 negative (5.2%)**, **24,287 exactly zero (20.9%)**. ✅ 6-order-of-magnitude spread ⇒ mixed units.
- `Taille_Sim` empty in 84,839/116,200 (73%). ✅
- `NCde`: 3,038 NULL, 2,491 empty string, and **94,570 rows (81%) equal to `'0000000000'`** — a placeholder, not an order number. 🔴 **New finding**: prior docs said "many are empty strings"; the dominant pattern is actually the all-zeros placeholder.
- Rows per `Id_Sim`: 125 → 4,078. Max rows for one `(Id_Sim, Code_Sim)` pair: **279** (mean 1.50) — i.e. the same material within one simulation can carry hundreds of dated stock lines.

### 3.2 Excel — `data/raw/excel/`

**`table.xlsx`** — 2 sheets:
- `plan_t_simplaniffourniture`, 19 rows × 17 cols. All rows `Id_Sim = 10775`, **which does exist in `plan_t_simplanif`** ✅ (`Globale` / `Piquage` / `Sem_Sim=202531` / `Client_Sim=DIESEL KIDS` / `Date_Sim=2025-07-30 09:42:49`). `TypeFourniture = 'Tissu'` in **all 19 rows** ✅. `POI` uses the dotted scheme `01.006.4702013572`. `Besoin` 4.54–67.20. 5 distinct `CI` (12-digit), `CI == CISibstitue` in every row. `PrevStock`: `S` ⇔ `DateAccesoire` present (13 rows), `N` ⇔ absent (6 rows) — perfect correlation ✅. `EtatAccessoire` = `NL` in exactly the 6 rows with no date ✅.
- `tablerecappoi_piq`, 8 rows × 255 cols (157 with any value). `POIntern` values include two obvious placeholders (`Collection`, `POColtTeintr`) and dotted codes (`01.006.DOOSAN FL09 WW4`, `01.008.170281`). `POCl` = the trailing segment of `POIntern` ✅. `Tissu` column: `Oui` ×5, `Non` ×1, blank ×2. Contains the per-component predicted-week columns `SemPrevOkProd`, `SemPrevRecpTiss`, `SemPrevRecpDblr`, `SemPrevRecpFrnt` — 🔴 **all four are entirely empty in this sample** (only `SemLav`, `SemRepassage`, `SemRepLimite` have values, and those look like stale 2001/2003/2009-era week codes: `200928`, `200101`, `200308`, plus three zeros). So the "predicted reception week" lead from TASK2 is structural only; there is **no value evidence** behind it.

**`consommation tissu par type.xlsx`** — 1 sheet `Feuil1`, 48 rows × 4 cols: `codeType`, `TypePcs` (French garment type), `TypePcs_Eng`, `Cons_Tissu` (coefficient, e.g. Pantalon 1.3, Blouson 1.8, Chemise 1.8, Jupe 1.5, Short 0.0). Clean reference table, no keys into the SQL data.

**`cde.xls`** — 4 sheets (order/reception tracking):
- `Liste cde tissu` 12 rows × 32 cols — fabric order headers. Column literally named `POI` holds **date strings** (`02/01/2026`) ✅ CONFIRMED: unrelated to `POI_Sim`.
- `detail prevision reception` 2 rows × 57 cols — fabric reception forecast; `DatePr` (forecast) and reception fields present but `CodeTissu`/`CodeColoris` blank. Too small to join.
- `cde FN` 4 rows × 40 cols — accessory order headers; `DateSouhSartex`, `DatePrev`, `DateEnvoiCde`, `EtapeCde`, `Valide`.
- `detail reception FN` 10 rows × 27 cols — accessory/thread receptions; `NCde=2726000415`, `CI` = `YT33537`…`YT38287`, `QteE` 5,000–105,000, `DateEnlev`/`DateEnlevR` Jan 2026.

### 3.3 PDF — `data/raw/pdf/`
Two customer purchase orders, seller `DENIM HOUSE (72000022)` (Ksar Hellal, Tunisia):
- `PO 3034174` — buyer *Seven for all Mankind International SAGL*, EUR, order date 25/03/26, 12 lines, style `7UCJ0A53-3RX23…34`, delivery 19/06/26.
- `PO 3034281` — buyer *Seven for all Mankind USA*, USD, order date 25/03/26, 10 lines, style `7U4X0A53-3RX23…32`, delivery 07/08/26.

Both are **finished-goods sales orders**, not material purchase orders. No identifier in them matches `POI_Sim`, `Code_Sim`, or `CI`. `DENIM HOUSE` and `7 FOR ALL MANKIND [USA]` do appear as `Client` values in the stock table — name-level match only.

---

## 4. CURRENT CODE INVENTORY

**There is no project code.** `src/`, `tests/`, `configs/`, `notebooks/`, `benchmarks/` are all empty; `requirements.txt` and `README.md` are 0 bytes.

Created during this assessment (Phase 0 tooling, read-only against raw data):
- `scripts/profile_raw_sql.py` — standalone parser + profiler for the three MySQL dumps. Custom quote-aware INSERT-tuple splitter (12,302/12,302 POI tuples parse with correct arity; 0 failures). Prints schema, per-column population, key/uniqueness checks, cross-table join rates. Reproducible: `python scripts/profile_raw_sql.py`.
- `outputs/logs/phase0_raw_profile.txt` — captured output of the above (gitignored).

---

## 5. CONFIRMED BUSINESS RULES

**`CONFIRMED` (cahier des charges + project documentation, mutually consistent):**

1. `SemTheorique = MAX(Tissu principal, Tissu secondaire, Fourniture, Fil, OK Production)` — the theoretical production week is the **latest** availability among the required elements. Stated identically in the brief (§1, §3.3), `Business Rules.md` §3, and `Theoretical Week.md` §4.
2. The five components are exactly: main fabric, secondary fabric, accessories/supplies, sewing thread, OK Production technical validation.
3. Production cannot theoretically start until **all required** components are available.
4. The simulator must output the **blocking element** — the component carrying the latest availability.
5. Anomalies must be surfaced, not hidden: missing component date, corrupt/badly-formatted data, incomplete PO, PO outside the studied period (brief §3.4).
6. The calculation grain is one result per POI, keyed `(Id_Sim, POI_Sim)` (`Theoretical Week.md` §2; UNIQUE constraint verified in the DDL).
7. A **simulated dataset is an accepted, explicitly requested deliverable** (brief §3.2, Livrable 2). This is a scope fact, not an escape hatch — it means synthetic data is legitimate for the calculator and the Hadoop PoC, provided it is labelled.
8. Hadoop/HDFS is `Découverte` level: exploratory, on tens-to-hundreds of thousands of **simulated** POs, for a sequential-vs-distributed comparison (brief §4). Not required to be faster.
9. Mandatory stack: Python, SQL, CSV/JSON, SQLite, Git. UI: Tkinter, Flask, or Streamlit (brief §3.5, §6).

**`CONFIRMED` from data (computed this session):**

10. **Week encoding is ISO-8601 `YYYYWW`.** In `plan_t_simplaniffourniture`, all 13 rows with `DateAccesoire = 2025-07-30` carry `EtatAccessoire = '202531'`; ISO calendar week of 2025-07-30 is 2025-W31 → `202531`. Exact match, 13/13, 0 mismatches. Same format as `Sem_Sim` (202520…202614). ✅ **This resolves the week-convention question for these two fields.** It is *not* yet confirmed for `SemTheorique` itself, because `SemTheorique` has no populated value anywhere in the available data.
11. **`Etat*` is a date mirror, not a status code — at least for OK Production.** `EtatOkProduction` equals `DateOKProduction` rendered `dd/mm/yyyy` in 50/50 rows. For `EtatFil`/`EtatFourniture` the column is *polymorphic*: it holds either a mirrored `dd/mm/yyyy` date **or** a French status word (`Sortie`, `Manque FH`). This contradicts the "generic status code" reading in `Data Dictionary.md`.
12. **Legacy boolean encoding is `-1 = TRUE`, `0 = FALSE`.** Six boolean-ish columns in `plan_t_simplanif` take only these two values across 431 rows; `1` never occurs. Also seen in `cde.xls` (`Recu`, `Valide`, `PrevisionPaiement`).

**`OBSERVED`, insufficient to confirm a rule:**

13. `DateOKProduction` is the latest component date in 31/34 testable rows but **not** in 3/34. OK Production is therefore *usually* but not *always* the blocker → the `MAX()` must be computed, never shortcut to "OK Prod".
14. `StatutFourniture`/`StatutFil` = `S`, `StatutOkProduction` = `R` — single-valued, so no dictionary can be derived. `HYPOTHESIS` only: `S` = "Sorti" (issued), `R` = "Réalisé"/"Reçu".

**`UNKNOWN` — nothing in any of the nine source files establishes these:**
- How each of `DateTissu`, `DateTissuSec`, `DateFourniture`, `DateFil`, `DateOKProduction` is *derived* by the company system.
- When a component is *required* vs *not applicable* for a given POI.
- What `NULL` on a component date means (not required / not yet available / calculation not run / error).
- Whether `DateMax == MAX(component dates)`.
- The tie-breaking rule for multiple blocking components.
- The meaning of the `Ind*` fields (all zero everywhere).
- How stock quantity participates in availability, if at all.

---

## 6. CONFIRMED DATA RELATIONSHIPS

Re-tested this session. Match rates are exact counts, not estimates.

| Relationship | Result | Status |
|---|---|---|
| `plan_t_simplanif.Id_Sim` → `plan_t_simplanifstock.Id_Sim` | **105,895 / 116,200 stock rows match (91.1%)**. 5 orphan simulations: 3322 (125 rows), 4826 (2,728), 5601 (185), 6948 (3,189), 7586 (4,078) = 10,305 orphan rows. Also **402 of 431 simulations have no stock rows at all**. | `SUPPORTED` where ranges overlap |
| `plan_t_simplanif.Id_Sim` → `plan_t_simplanifpoi.Id_Sim` | **0 / 12,302 (0%)**. POI has only `Id_Sim=5601`; the simulation table covers 10775–12039. | `NOT DEMONSTRATED` — schema-level candidate only |
| `plan_t_simplanifpoi.POI_Sim` → `plan_t_simplanifstock.Code_Sim` | Tested on the one shared simulation `Id_Sim=5601`: 12,302 POI codes vs 176 distinct stock codes → **0 matches**. Formats are incompatible (`0133898091CD` vs `GU04510`, `7F00734`). | `REFUTED` as a direct join |
| `plan_t_simplaniffourniture.Id_Sim` → `plan_t_simplanif.Id_Sim` | `10775` exists in the simulation table. **1/1 match.** | `CONFIRMED` (single value) |
| `plan_t_simplaniffourniture.CI` → `plan_t_simplanifstock.Code_Sim` | 5 distinct `CI`; **1 matches** (`689037021001`) — and only under `Id_Sim=3322`, not under its own `Id_Sim=10775`. Within `Id_Sim=10775`: **0/5**. | `PARTIAL` — shared code space, no usable join |
| `plan_t_simplanifpoi.LastFil` (thread code) → `plan_t_simplanifstock.Code_Sim` | Extracted 3 distinct codes (`YT08654`, `YT33448`, `YT19147`) from the `YT#####:description` strings → **3/3 present in stock**. | `SUPPORTED` (format + value) |
| `cde.xls` `detail reception FN.CI` → `plan_t_simplanifstock.Code_Sim` | 10 distinct `YT` codes → **8/10 present in stock**. | `SUPPORTED` (format + value) |
| `cde FN.N°Cde` → `detail reception FN.NCde` | `2726000415` present in both. | `CONFIRMED` |
| `tablerecappoi_piq.POIntern` / `plan_t_simplaniffourniture.POI` → `POI_Sim` | **0 matches** either way. Three mutually incompatible POI identifier schemes coexist: `POI_Sim` (`0133898091CD`), dotted (`01.006.4702013572`), and `POCl`-style (`170281`). | `NOT SUPPORTED` |
| PO PDF item/order codes → any SQL identifier | No format or value overlap. Only client *names* match. | `NOT SUPPORTED` |

**Demonstrated relationship graph (only edges with evidence):**

```
plan_t_simplanif (Id_Sim 10775-12039)
   ├── Id_Sim ──91%──> plan_t_simplanifstock            [SUPPORTED]
   ├── Id_Sim ──1/1──> plan_t_simplaniffourniture(10775) [CONFIRMED]
   └── Id_Sim ───0%──> plan_t_simplanifpoi (5601 only)   [NOT DEMONSTRATED]

plan_t_simplanifpoi.LastFil "YT#####:.." ──3/3──> stock.Code_Sim (YT family)  [SUPPORTED]
cde.xls detail reception FN.CI (YT#####)  ──8/10─> stock.Code_Sim             [SUPPORTED]
fourniture.CI (12-digit)                  ──1/5──> stock.Code_Sim            [PARTIAL]

POI_Sim ──X──> Code_Sim | POIntern | fourniture.POI | PO PDF codes    [NO BRIDGE]
```

**The structural gap is precise and unchanged:** the material code space (`CI` / `LastFil` / `Code_Sim`) is internally consistent and demonstrably shared, but **no available source stores a `POI_Sim` value next to a material code.** Without that bridge, component availability cannot be reconstructed bottom-up from stock/orders for any POI in the available data.

---

## 7. DATA QUALITY ISSUES

Ordered by impact on computing `SemTheorique`. Items marked 🔴 are new in this assessment.

| # | Issue | Where | Rows/Scale | Severity | Effect on `SemTheorique` |
|---|---|---|---|---|---|
| DQ-1 | `SemTheorique` and `DateMax` are 100% NULL | POI | 12,302 / 12,302 | **CRITICAL** | **No historical reference value exists anywhere.** Match-rate validation against company history is impossible with this data. |
| DQ-2 | `DateTissu` and `DateTissuSec` are 100% NULL | POI | 12,302 / 12,302 | **CRITICAL** | Two of the five MAX inputs are never available. |
| DQ-3 | No row has more than 3 of 5 component dates | POI | max 3, in only 4 rows | **CRITICAL** | The 5-component MAX is untestable on real data at any row. |
| DQ-4 | POI ↔ Simulation join rate 0% | POI vs SIM | 0 / 12,302 | **CRITICAL** | POIs cannot be attributed to a simulation, client, season, or week context. |
| DQ-5 | No POI ↔ material bridge exists in any source | all | — | **CRITICAL** | Availability dates cannot be reconstructed from stock/orders. |
| DQ-6 | All `Ind*` indicator fields are `0` | POI | 12,302 | HIGH | Cannot use indicators to decide component applicability. |
| DQ-7 | `Statut*` fields are single-valued (`S`,`S`,`R`) | POI | 9 / 74 / 50 | HIGH | No status dictionary derivable; cannot gate on status. |
| DQ-8 | `Etat*` polymorphic: mirrored date **or** French word (`Sortie`, `Manque FH`) | POI | 32 + 12 rows | HIGH | Parsing must handle both; column carries no reliable independent state. |
| DQ-9 | `Client` in stock conflates supplier and end client (`Sartex` = 85%) | Stock | 98,887 | HIGH | Any "stock for this client" filter must first decide Sartex scope. |
| DQ-10 | `Client_Sim` NULL in 53% of simulations 🔴 | SIM | 227 / 431 | HIGH | Client-scoped logic is unavailable for over half the simulations. |
| DQ-11 | `Code_Sim` is 4 code families by length/prefix (7/8/6/12), semantics differ | Stock | 116,200 | MEDIUM | Must classify before use; `SUM(Qte)` across families is meaningless. |
| DQ-12 | `Code_Sim` case inconsistency 🔴 | Stock | **1,715 rows, 8 codes** | MEDIUM | Case-sensitive joins silently lose rows. Normalisation is mandatory. |
| DQ-13 | `Date_Sim` runs to 2025-10-31, **beyond** the last insert timestamp (2025-08-29); 4,630 future-dated rows 🔴 | Stock | 4,630 | MEDIUM | `Date_Sim` is a *projected* date, not an observation. Changes its interpretation in availability logic. |
| DQ-14 | `NCde = '0000000000'` placeholder 🔴 | Stock | **94,570 (81%)** | MEDIUM | `NCde` is unusable as an order key for 81% of rows. |
| DQ-15 | `Qte` negative (6,005) and zero (24,287); range −15,140 … 50,154,000 | Stock | 30,292 | MEDIUM | Mixed units; sign semantics unknown. Quantity-based availability is unsafe. |
| DQ-16 | `DateOKProduction < DateFourniture` in 3/34 testable rows | POI | 3 | MEDIUM | Refutes "OK Prod is always last"; MAX must be genuinely computed. |
| DQ-17 | `Etat_Element` contains garbage `^c` and `c` 🔴 | SIM | 2 | LOW | Free-text corruption exists in control fields; validation layer needed. |
| DQ-18 | `Sem_Sim = 202651` outlier, breaks the 202520–202614 sequence | SIM | 1 | LOW | Either a typo or a 53-week year; flag, don't guess. |
| DQ-19 | `Taille_Sim` empty in 73% of stock rows | Stock | 84,839 | LOW | Size dimension inapplicable to bulk material — expected, but confirms grain is not size-uniform. |
| DQ-20 | 402 / 431 simulations have zero stock rows 🔴 | SIM/Stock | 402 | LOW | Stock coverage is sparse at the simulation level, not just the row level. |
| DQ-21 | `SemPrevRecp*` predicted-week columns entirely empty 🔴 | `tablerecappoi_piq` | 8 / 8 | INFO | The TASK2 "predicted reception week" lead has structural support only, no values. |

No raw file was modified. Every count above is reproducible via `scripts/profile_raw_sql.py` and the Excel/PDF readers.

---

## 8. UNRESOLVED QUESTIONS

Consolidating `docs/context/Open Questions & Business Validation.md` (Q1–Q29) with what this assessment could and could not settle.

**Resolved or narrowed by this assessment:**
- Week convention (Q12 in `Theoretical Week.md` §18): **ISO-8601 `YYYYWW`**, confirmed by computation on `DateAccesoire`/`EtatAccessoire`. Still unconfirmed *for `SemTheorique` specifically*.
- Meaning of `Etat*` (Q12): mirrors the date for OK Production (50/50); polymorphic for Fil/Fourniture.
- `Code_Sim` semantics (Q7 TASK1): four families by length/prefix; `YT` = thread, confirmed by three independent sources.
- Extraction methodology (Q1 TASK1): 🔴 **partially answered** — the three dumps came from **one export run on 31/03/2026** (timestamps 18 s apart), so the period mismatch is a property of the source tables, not of three separate exports. *Why* the production POI table contained only a 2021 simulation on that date remains unknown.

**Still blocking, must be asked (with what has already been tried):**

| ID | Question | Why it matters | Already attempted |
|---|---|---|---|
| **B-1** | Can a POI extract with **populated** `SemTheorique`, `DateMax`, `DateTissu`, `DateTissuSec` be provided (ideally `Id_Sim` in 10775–12039 to match the simulation table)? | Without it there is **no** historical validation target and no way to test the MAX formula end-to-end. | Searched all 9 raw files; `SemTheorique`/`DateMax` appear in **zero** rows anywhere and are absent from every Excel sheet. |
| **B-2** | What table maps a `POI_Sim` to its material codes (BOM / nomenclature)? | Without it, component availability cannot be derived from stock/orders. | Tested `POI_Sim`↔`Code_Sim` (0/185), `POI_Sim`↔`POIntern` (0/8), `POI_Sim`↔`fourniture.POI` (0/19), `POI_Sim`↔PO PDF codes (no format overlap). |
| **B-3** | Why does the POI table contain only `Id_Sim=5601` (2021) while the simulation table covers 2025-07→2026-03? Is 5601 a development/sampling simulation? | Determines whether the empty fields are an extraction filter or the normal state of development simulations. | `EtapeFH` shows `Cotation`/`Proto`/`Collection` labels; `Categ_Sim` has `Devellopement A.W./B.W.` categories. Consistent with the hypothesis but not proof. |
| **B-4** | Is `Client='Sartex'` the internal mill/warehouse entity? Should Sartex stock rows be in or out of scope for a client's availability? | Affects 85% of all stock rows. | Two independent clues: `tablerecappoi_piq.NomFrs` holds real external mills (ISKO DOKUMA, LEGLER, SWIFT) ≠ Sartex; `cde.xls` has a `DateSouhSartex` column. INFERRED, not confirmed. |
| **B-5** | When is each component **required** vs not applicable? | Directly changes the MAX set and therefore the result. | `Ind*` all zero; `tablerecappoi_piq.Tissu` (Oui/Non) exists but only in a reporting table with no key to `POI_Sim`. |
| **B-6** | What does a NULL component date mean? | Determines `NOT_REQUIRED` vs `REQUIRED_BUT_UNAVAILABLE`. | No populated counterexample exists to infer from. |
| **B-7** | Tie-break rule when several components share the max date? | Affects the blocking-element output. | Not addressed in the brief or any doc; no populated data to observe. |
| **B-8** | What do `Statut*` `S` and `R` mean? | Would allow status gating. | Single-valued in the extract — undecidable from data. |
| **B-9** | Does the company use ISO weeks for `SemTheorique`, or a production calendar? Is `202651` a typo or a 53-week year? | Year-boundary correctness. | ISO confirmed for `EtatAccessoire`; `SemTheorique` has no values to check. |
| **B-10** | `Qte` units and sign semantics; how are multiple stock lines for one material aggregated? | Any quantity-based availability rule depends on it. | Observed 6-order range, 5% negative, 21% zero, up to 279 lines per `(Id_Sim, Code_Sim)`. Not decidable from data. |
| **B-11** | What is the actual performance problem being solved, and at what scale (POIs per run, acceptable latency)? | The whole project objective is calculation-time reduction; there is no baseline figure to beat. | Not stated in the brief or any doc. The brief only says "tens to hundreds of thousands of *simulated* POs" for the Hadoop part. |

**RECOMMENDATION:** B-1, B-2, B-5, B-11 are the four that change the shape of the deliverable. B-11 in particular should be asked early — the project's stated objective is minimising calculation time, and right now there is no measured incumbent to compare against.

---

## 9. ASSUMPTIONS THAT MAY BE REQUIRED

Each will be implemented as an **explicit, configurable, individually testable** assumption in `configs/`, never hardcoded, and each is labelled. The engine will support switching them so their effect on results is measurable.

| ID | Assumption | Label | Justification | Risk if wrong |
|---|---|---|---|---|
| A-1 | Week derivation uses **ISO-8601** (`iso_year`, `iso_week`, `week_key=YYYYWW`), displayed as `S{week}`. | `INFERRED` (computed, 13/13 on `EtatAccessoire`) | Only week convention with positive evidence; matches `Sem_Sim` format. | Off-by-one weeks at year boundaries if a production calendar is used. Mitigated by storing `iso_year` explicitly and keeping the converter swappable. |
| A-2 | `date_theorique = MAX(dates of components that are applicable **and** have a valid date)`. | `CONFIRMED` (brief §3.3) | Verbatim in the cahier des charges. | None on the rule itself; risk is in the applicability set (A-3). |
| A-3 | A component with a NULL date is treated as `UNKNOWN` applicability by default; the POI result status becomes `INCOMPLETE_DATA` rather than being silently dropped from the MAX. | `RECOMMENDATION` | `Edge Cases` doc §2/§3 forbids substituting a value; brief §3.4 requires flagging anomalies. | If NULL actually means "not required", results will be over-flagged as incomplete. Configurable: `null_policy = unknown | not_required | required_unavailable`. |
| A-4 | All five components are treated as **potentially required**; no component is assumed inapplicable without evidence. | `RECOMMENDATION` | No applicability rule is confirmed (B-5). | May flag POIs that legitimately need no secondary fabric. Surfaced per-component in output, so it is auditable. |
| A-5 | On a tie, **all** tied components are returned as blocking elements (list, not scalar). | `RECOMMENDATION`, per `10_simulator_specification.md` | Explicitly the documented behaviour absent a company rule. | Downstream consumers expecting a scalar. Output carries both a list and a canonical joined string. |
| A-6 | Identifier normalisation: `Code_Sim`/`CI` upper-cased and trimmed for joins; original value retained. | `RECOMMENDATION` | 1,715 rows have case variants (DQ-12). | Could merge two genuinely distinct codes differing only in case — no such case observed; a warning is emitted when folding changes the row count. |
| A-7 | `DateMax` is **not** assumed equal to `MAX(component dates)`; it is carried as a separate reference column only. | `RECOMMENDATION` | `Theoretical Week.md` §7 warns against it; untestable (100% NULL). | None — this is the conservative choice. |
| A-8 | Historical validation is **deferred**, not skipped. The validation harness is built now and runs on synthetic ground truth; it will run against real history the moment a populated extract arrives (B-1). | `RECOMMENDATION` | DQ-1 makes real validation impossible today. | Match rate against company history stays unmeasured. Must be stated as a limitation in the report. |
| A-9 | Benchmark/scale datasets are **`SYNTHETIC`**, generated with a fixed seed and a documented generator, stored under `benchmarks/datasets/`, and never mixed with real rows. Every row carries `data_origin`. | `SYNTHETIC`, authorised by brief §3.2 + §4 | The brief explicitly asks for a simulated dataset and simulated POs for Hadoop. | Presenting synthetic results as company history — prevented by the `data_origin` column and file separation. |
| A-10 | Stock quantity does **not** enter the v1 availability calculation. | `RECOMMENDATION` | B-10 unresolved; `Business Rules.md` §13 explicitly forbids assuming `Qte >= BesoinTissu`. | If availability really is quantity-driven, v1 understates the problem. Documented as a known limitation with a clear extension point. |
| A-11 | Scope filter defaults to processing all POIs, with configurable exclusion of `Categ_Sim` in `{Devellopement A.W., Devellopement B.W.}` (off by default until B-3 is answered). | `RECOMMENDATION` | B-3 unresolved; filtering now would silently change scope. | None while off; the switch makes the effect measurable. |

---

## 10. RISKS

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R-1 | **The real data can never validate the calculation.** `SemTheorique` is 100% NULL; no populated extract may ever arrive. | High | High | Build the calculation as a pure, exhaustively unit-tested function validated against the brief's own worked example (S35/S34/S36/S35/S33 → S36) plus synthetic ground truth. Request B-1 now. Report the limitation explicitly rather than manufacturing a match rate. |
| R-2 | **Silent drift from evidence into invention** — e.g. deciding that NULL means "not required" because it makes the numbers look better. | Medium | High | Every assumption lives in `configs/` with an evidence label; results carry `data_quality_flag` and `calculation_status`; a decision record is written for each in `docs/decisions/`. |
| R-3 | **Real-data pipeline produces almost nothing usable** — on the current extract, a fully evidence-driven canonical build yields 12,252 POIs with zero component dates. A demo over it would show nothing. | High | Medium | Two clearly separated tracks: REAL (honest, mostly `INCOMPLETE_DATA`, valuable as a data-quality finding) and SYNTHETIC (full-coverage, authorised by the brief, drives the UI/benchmark/Hadoop demo). Never merged, never relabelled. |
| R-4 | **Hadoop shows no speed-up** on data of this size (12K POIs, 25 MB). Very likely — JVM/job startup will dominate a per-row MAX. | Very High | Low | The brief calls Hadoop `Découverte`. Plan to measure honestly across dataset sizes and report the crossover point (or its absence). A well-measured negative result is a valid engineering conclusion and will be presented as such. |
| R-5 | **The performance objective has no baseline.** "Minimise calculation time" with no incumbent figure (B-11). | High | Medium | Measure our own baseline rigorously (dataset size, row count, hardware, runs, median + spread), profile to find the real bottleneck, and report relative improvements only. Never claim an improvement over the company system. |
| R-6 | **Optimising the wrong thing** — distributing a trivial `MAX()` while the real cost is parsing/joining. | Medium | Medium | Profile before optimising (`12_hadoop_mapreduce_plan.md` warns about exactly this). Report preparation time and calculation time separately. |
| R-7 | **Identifier normalisation breaks a real distinction** (case folding, code-family classification). | Low | Medium | Retain original values alongside normalised ones; emit a warning whenever folding changes cardinality; unit-test the classifier. |
| R-8 | **Environment fragility** — Python 3.14 is very new; Hadoop on Windows is notoriously awkward. | Medium | Medium | Pin exact versions in `requirements.txt`. For Hadoop, plan a Hadoop-streaming path with a pure-Python mapper/reducer that also runs standalone via pipes, so correctness is testable without a cluster; document the environment precisely and state clearly whether execution was pseudo-distributed or single-node. |
| R-9 | **Scope creep into a large UI.** | Medium | Low | `MASTER_PROMPT.md` §11 Phase 6 and brief §3.5 both ask for something simple. One Flask app, a handful of routes. |
| R-10 | **Raw data accidentally modified.** | Low | High | All raw access is read-only; no write path targets `data/raw/`; an integrity check (file sizes + SHA-256) is recorded in Phase 1 and re-verified in CI-style checks. |

---

## 11. IMPLEMENTATION PLAN

Two tracks run in parallel and are never mixed: **REAL** (evidence-only, honest about emptiness) and **SYNTHETIC** (brief-authorised, drives demo/benchmark/Hadoop).

### Phase 1 — Data understanding, formalised (next)
Turn this assessment's ad-hoc parsing into reusable, tested ingestion + profiling.
- `src/ingestion/` — SQL dump parser (promote `scripts/profile_raw_sql.py`), Excel readers, PDF text reader. Read-only, streaming for the 18 MB file.
- Raw-integrity manifest: file sizes + SHA-256 of all 8 raw files, recorded so any later modification is detectable.
- `src/preprocessing/profiling.py` — schema, population, cardinality, key/uniqueness, date-format, and join-rate reports written to `outputs/results/`.
- Cache parsed raw data to `data/interim/` (Parquet or SQLite) so later phases don't reparse 25 MB.
- **Deliverable:** `docs/analysis/PHASE1_Data_Profiling.md` + machine-readable profile JSON. All DQ-1…DQ-21 codified as automated checks.

### Phase 2 — Preprocessing, normalisation, integration
- `src/preprocessing/normalize.py` — date parsing (`YYYY-MM-DD`, `dd/mm/yyyy`), identifier normalisation (A-6), `Code_Sim` family classifier, `-1/0` boolean decoding, `Etat*` polymorphic parser (date-mirror vs status word).
- `src/preprocessing/integrate.py` — implements **only** the evidence-supported joins from §6; every unsupported join is a named, explicit `UNRESOLVED_LINK` in the output rather than a silent omission.
- **Deliverable:** `data/interim/` normalised tables + `docs/decisions/DEC-001_normalization_rules.md`.

### Phase 3 — Canonical dataset
- `src/business/schema.py` — canonical schema per `08_canonical_dataset_specification.md`: `id_sim`, `poi_sim`, five component dates, `date_theorique`, `iso_year`, `iso_week`, `week_key`, `sem_theorique`, `blocking_element`, `calculation_status`, `data_origin`, `data_quality_flag`, plus provenance columns.
- REAL build from `plan_t_simplanifpoi` → `data/canonical/poi_real.parquet` (expected: 12,302 rows, ~12,252 `INCOMPLETE_DATA`). **This outcome is a finding, not a failure.**
- `src/business/applicability.py` — per-component classification `NOT_REQUIRED` / `REQUIRED_AND_AVAILABLE` / `REQUIRED_BUT_UNAVAILABLE` / `UNKNOWN`, driven by the configurable A-3/A-4 policies.
- **Deliverable:** canonical dataset + `docs/decisions/DEC-002_canonical_schema.md`.

### Phase 4 — Business calculation (the core)
- `src/business/week.py` — ISO conversion, `week_key`, `S{n}` display, year-boundary handling, and a swappable calendar interface.
- `src/business/semtheorique.py` — pure functions: `compute_date_theorique`, `identify_blocking_elements` (returns a list), `compute_sem_theorique`, `classify_status`. No I/O, no globals, fully deterministic.
- `tests/unit/` — pytest suite covering all 12 edge cases from `MASTER_PROMPT.md` §15 and the case table in `13_testing_strategy.md`, plus the four property checks (theoretical date ≥ every included date; every blocker equals the theoretical date; lowering a non-max date cannot change the result; adding a later required component cannot decrease the result). **Includes the cahier des charges' own worked example as a named regression test.**
- **Target: 100% branch coverage of `src/business/`.** This is where correctness is won.
- **Deliverable:** tested calculation engine + `docs/business_rules/RULES_v1.md` with every rule labelled.

### Phase 5 — Synthetic data generator
- `src/simulation/generator.py` — seeded (`seed=20260908`), documented generator producing the brief's `{PO_ID, Ref_Article, Tissu_Principal, Tissu_Secondaire, Accessoires, Fils, OK_Prod, Semaine_Theorique}` shape mapped onto the canonical schema, with controllable rates of missing/tied/invalid/duplicate rows and a **known ground-truth `sem_theorique`**.
- Scale tiers: 1K / 10K / 100K / 1M POIs → `benchmarks/datasets/`, every row `data_origin=SYNTHETIC`.
- **Deliverable:** generator + `docs/decisions/DEC-003_synthetic_data_method.md`. This is the brief's Livrable 2.

### Phase 6 — Baseline simulator
- `src/simulation/baseline.py` — simplest correct batch runner: canonical in → results out, row-at-a-time, no cleverness. Reference implementation for every later version.
- CLI in `scripts/`; results to `outputs/results/`.
- `tests/integration/` — raw→canonical, canonical→simulator, output-schema tests.
- `src/simulation/validate.py` — the validation harness (metrics from `Theoretical Week.md` §12: POIs evaluated, complete, incomplete, valid results, discrepancies, exact matches, match rate). Runs on synthetic ground truth now; ready for real history the day B-1 lands.
- **Deliverable:** working baseline + validation report.

### Phase 7 — Interface
- Flask app: POI lookup, the five component dates, `SemTheorique`, blocking element(s), calculation status, quality flags, and a clear `REAL`/`SYNTHETIC` badge on every result. Minimal HTML/CSS, no JS framework.
- **Deliverable:** the brief's Livrable 4.

### Phase 8 — Benchmark
- `benchmarks/` harness per `11_benchmarking_plan.md`: multiple repetitions, warm-up excluded, median + spread, and **separate timing for preprocessing / calculation / output writing**. Records hardware, OS, Python version, dataset size, row count, run count.
- **Deliverable:** `docs/report/BENCHMARK_baseline.md` + raw timings in `outputs/benchmarks/`.

### Phase 9 — Profiling and optimisation
- `cProfile`/`timeit` on the baseline to locate the actual bottleneck (expected: parsing and I/O, not the `MAX()`).
- `src/optimization/` — vectorised/columnar version. Every change justified by a measured delta; correctness re-verified against the baseline row-for-row.
- **Deliverable:** `docs/report/OPTIMIZATION.md` with before/after measurements and the bottleneck evidence.

### Phase 10 — Hadoop MapReduce
- `src/mapreduce/` — mapper keyed `(Id_Sim, POI_Sim)`, reducer applying the **same** `src/business/` functions (shared code, so logic cannot diverge).
- Runnable two ways: piped locally (`cat | mapper | sort | reducer`) for correctness, and via Hadoop streaming for the real run. Environment documented precisely, including whether execution was single-node or pseudo-distributed.
- Row-for-row output comparison against the baseline on identical input.
- **Deliverable:** Livrable 5 + `docs/report/HADOOP.md`.

### Phase 11 — Comparison and final documentation
- Baseline vs optimised vs MapReduce across all scale tiers; find the crossover point or state that none exists in the tested range.
- Populate `docs/architecture/`, `docs/business_rules/`, `docs/decisions/`, `docs/report/`; write the real `README.md` and pin `requirements.txt`.
- **Deliverable:** Livrable 1 + Livrable 6 material.

**Dependency note:** Phases 1–4 depend on nothing external and start now. Phase 6's *real*-data validation is gated on B-1; everything else is gated only on our own work. If B-1 never arrives, the project still delivers all six of the brief's deliverables — with the historical match rate declared unmeasurable and the reason documented.

---

## 12. EXPECTED DELIVERABLES

Mapped to the cahier des charges:

| Brief | Deliverable | Where |
|---|---|---|
| Livrable 1 | Analysis document (context, rules, functional needs) | `docs/analysis/`, `docs/business_rules/`, `docs/architecture/`, this file |
| Livrable 2 | Simulated dataset (CSV/JSON/SQLite) | `src/simulation/generator.py` → `benchmarks/datasets/`, `data/canonical/` |
| Livrable 3 | Commented, tested calculation program | `src/business/`, `src/simulation/`, `tests/` |
| Livrable 4 | Working user interface | Flask app + templates |
| Livrable 5 | Hadoop/HDFS PoC | `src/mapreduce/` + run scripts + `docs/report/HADOOP.md` |
| Livrable 6 | Full internship report material | `docs/report/` per `14_report_structure.md` |

Plus, beyond the brief's minimum: reproducible ingestion of the real production exports, a canonical layer with provenance, a data-quality report on real company data (a genuine finding in its own right), a benchmark harness, and decision records.

---

## 13. FILES THAT NEED TO BE CREATED OR MODIFIED

**Already created in this phase:**
- `scripts/profile_raw_sql.py` (new)
- `docs/analysis/PHASE0_Initial_Project_Assessment.md` (this file, new)
- `outputs/logs/phase0_raw_profile.txt` (new, gitignored)

**To create, Phase 1–2:**
```
requirements.txt                          (populate: pandas, numpy, openpyxl, xlrd, pypdf, pytest, flask, pyarrow — pinned)
README.md                                 (populate)
configs/paths.yaml                        (all paths, no hardcoding)
configs/business_rules.yaml               (A-1…A-11 as switches with evidence labels)
configs/logging.yaml
src/__init__.py  +  __init__.py in all six src subpackages
src/ingestion/{sql_dump.py,excel.py,pdf.py,manifest.py}
src/preprocessing/{profiling.py,normalize.py,integrate.py,quality.py}
docs/analysis/PHASE1_Data_Profiling.md
docs/decisions/DEC-001_normalization_rules.md
```

**To create, Phase 3–6:**
```
src/business/{schema.py,week.py,applicability.py,semtheorique.py,status.py}
src/simulation/{baseline.py,generator.py,validate.py,runner.py}
tests/unit/{test_week.py,test_semtheorique.py,test_blocking.py,test_status.py,test_normalize.py}
tests/integration/{test_raw_to_canonical.py,test_canonical_to_simulator.py}
tests/validation/{test_edge_cases.py,test_properties.py,test_cahier_example.py}
tests/conftest.py
scripts/{build_canonical.py,run_simulator.py,generate_synthetic.py}
docs/business_rules/RULES_v1.md
docs/decisions/{DEC-002_canonical_schema.md,DEC-003_synthetic_data_method.md}
```

**To create, Phase 7–11:**
```
src/simulation/webapp/{app.py,templates/,static/}
benchmarks/{run_benchmark.py,harness.py}
src/optimization/vectorized.py
src/mapreduce/{mapper.py,reducer.py,run_local_pipe.sh,run_hadoop.sh}
docs/architecture/ARCHITECTURE.md
docs/report/{BENCHMARK_baseline.md,OPTIMIZATION.md,HADOOP.md,COMPARISON.md,LIMITATIONS.md}
```

**To modify:** `README.md`, `requirements.txt` (both currently empty). Also worth committing: `docs/context/`, `docs/analysis/`, `docs/cahier_des_charges/`, `docs/execution/` and `MASTER_PROMPT.md` are all untracked or shown as deleted in git status — the documentation move from `docs/data_dictionary/` to `docs/context/` should be committed so the history reflects it.

**Never modified:** everything under `data/raw/`.

---

## 14. CORRECTIONS TO PRIOR DOCUMENTATION

Per `MASTER_PROMPT.md` §18, discoveries that contradict earlier conclusions are recorded rather than silently applied.

1. **Stock date range.** `TASK1_Raw_SQL_Deep_Analysis.md` §A gives stock dates as "2020-07-01 to 2025-08-29". That upper bound is the max of `CrtDateAuto` (insert timestamp). `Date_Sim` actually extends to **2025-10-31**, with 4,630 rows dated after the last insert. Evidence: recomputed min/max of both columns over all 116,200 rows. Consequence: `Date_Sim` is forward-looking, which changes how stock rows should be read in any availability rule.
2. **`NCde` in stock.** TASK1 §C.3 says `NCde` is "populated in 113,162 rows, many of those empty strings". The dominant value is the placeholder `'0000000000'` — **94,570 rows (81%)**. `NCde` is therefore not usable as an order key for the great majority of rows.
3. **Extraction methodology.** TASK1 open question Q1 hypothesised that the three files were "independent exports taken at different times". The dump headers show a **single export run on 31/03/2026**, 18 seconds apart. The period mismatch is a property of the source tables at that moment, not of the export process. Why the production POI table held only a 2021 simulation remains unanswered.
4. **`SemPrevRecp*` fields.** TASK2 §A.2 flags `SemPrevRecpTiss`/`SemPrevRecpDblr`/`SemPrevRecpFrnt`/`SemPrevOkProd` as "a strong structural hint" for the origin of the component dates. All four are **entirely empty** in the 8-row sample. The lead is structural only; no value evidence exists. TASK2 did say "not yet value-tested" — this confirms it as empty, so the lead should not be relied on.
5. **`Data Dictionary.md` column count.** The dictionary enumerates ~55 fields as the critical subset; the POI table has **80** real columns (verified in the DDL), including the `*_old`/`*_Manuel` pairs. Not a contradiction, but the dictionary is incomplete relative to the actual schema.
6. **New quality issues not in any prior document:** `Etat_Element` garbage values `^c`/`c` (DQ-17); `Client_Sim` NULL in 53% of simulations (DQ-10); `Code_Sim` case variants affecting 1,715 rows (DQ-12); `Priorite_Sim` co-populated with exactly the 50 `DateOKProduction` rows; 402/431 simulations with no stock rows (DQ-20).

Nothing found in this assessment contradicts the core `MAX()` business rule. It remains consistently stated across the cahier des charges and all project documentation.
