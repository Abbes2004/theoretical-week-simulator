# TASK 2 — Supporting Data Sources & Business Mapping Analysis

**Scope:** Phase 1 — Data Understanding, continued. No simulator, no business-logic implementation, no Hadoop. All findings below come from actually opening and querying the files (pandas for Excel, zip/text extraction for the PDFs, direct cross-referencing against the SQLite database built in Task 1) — not from assumptions about column names.

**Files analyzed:**
```
table.xlsx                         → sheets: tablerecappoi_piq (8 rows × 255 cols), plan_t_simplaniffourniture (19 rows × 17 cols)
cde.xls                            → sheets: Liste cde tissu (12), detail prevision reception (2), cde FN (4), detail reception FN (10)
consommation_tissu_par_type.xlsx   → sheet: Feuil1 (48 rows × 4 cols)
PO_3034174_72000022_Ladies.pdf     → 2-page customer purchase order
PO_3034281_72000022_Ladies.pdf     → 2-page customer purchase order
RapportStageSimulateurDisponibilite.pdf → 5-page document
```

All files were small enough to inspect in full (max 255 columns / 48 rows), so every conclusion below is based on complete, not sampled, content unless stated otherwise.

---

## 0. Single Most Important Discovery — `RapportStageSimulateurDisponibilite.pdf` Is the Cahier des Charges, Not a Prior Report

Despite its filename, this 5-page PDF **is the project's assignment brief ("Cahier des Charges") itself** — the same specification already reflected in `project_context.md` / `business_rules.md` — not a previous intern's completed report on the real system. This changes how every other finding should be read. Key excerpts (paraphrased, not quoted, per copyright policy):

- It explicitly frames the target rule exactly as already documented: theoretical week = the **latest** week among Tissu principal, Tissu secondaire, Accessoires, Fils, OK Prod, illustrated with the same style of example (fabric S35 / secondary S34 / accessories S36 / thread S35 / OK Prod S33 → result S36). **CONFIRMED as the officially specified target rule**, sourced directly from the brief.
- Crucially, Mission 2 ("Préparation des données") tells the intern to **create or use a *simulated* database**, with a deliberately simple illustrative structure (`PO_ID, Ref_Article, Tissu_Principal, Tissu_Secondaire, Accessoires, Fils, OK_Prod, Semaine_Theorique`) and weeks written as plain text like `S32`...`S52`.
- Hadoop/HDFS is explicitly framed as a **"Découverte" (discovery/exploration) level** add-on, not a hard requirement, to be attempted only after a simple local version works.
- The deliverables list (analysis document, simulated dataset, calculation program, UI, Hadoop POC, final report) matches the phased plan already followed in this project.
- The document is dated 18 August 2026.

**Implication (INFERRED, not stated in the brief):** the brief's minimum expectation was a toy/simulated dataset. The fact that this project instead has access to real, messy production SQL exports (`plan_t_simplanif`, `plan_t_simplanifpoi`, `plan_t_simplanifstock`) is going beyond the base assignment. This is very plausibly *why* the real data doesn't cleanly match the brief's idealized formula: the brief describes the target business concept, but was never meant to be a schema specification for the real production database. It does **not** resolve any of Task 1's data-quality findings (empty `SemTheorique`, mismatched `Id_Sim` ranges, etc.) — it only confirms that the formula itself is the correct thing to aim for, once real, validated inputs are available.

---

## A. Source-by-Source Analysis

### A.1 `table.xlsx` — sheet `plan_t_simplaniffourniture` (19 rows)

This is the single most valuable new evidence source in Task 2.

- `Id_Sim = 10775` for all 19 rows — **this simulation exists in `plan_t_simplanif`** (Task 1: `Id_Sim=10775`, `Type_Sim=Globale`, `Categ_Sim=Piquage`, `Sem_Sim=202531`, `Client_Sim=DIESEL KIDS`). This is the **first genuine, confirmed cross-file link** obtained in this project: `plan_t_simplaniffourniture.Id_Sim` values are real, existing `plan_t_simplanif.Id_Sim` values (unlike the POI SQL extract from Task 1, which had none).
- `TypeFourniture = "Tissu"` for **all 19 rows**. This contradicts the assumption that `plan_t_simplaniffourniture` is exclusively an "accessories" table — **OBSERVED**: it is a **generic material-requirement table** where `TypeFourniture` discriminates the material category (fabric/secondary fabric/accessory/thread), and this particular sample happens to only contain `Tissu` (main fabric) rows. This means `plan_t_simplaniffourniture` filtered by `TypeFourniture='Tissu'` is a strong candidate as the actual **source detail** behind `BesoinTissu` and `DateTissu` at the POI level (an aggregation target), rather than being unrelated to fabric.
- `Besoin` (e.g. 47.03, 4.54, 13.62, 67.20) — plausible per-line fabric requirement quantities, consistent with the `BesoinTissu` hypothesis. **INFERRED**, same unit family as `BesoinTissu` (both non-trivial decimals in a similar range).
- `CI` and `CISibstitue` are identical in every row (no substitution occurred in this sample) and take the form of **12-digit numeric codes** (e.g. `689072001001`, `172009009001`, `366189238001`). One of these (`689037021001`) was tested directly against `plan_t_simplanifstock.Code_Sim` and **found 3 matching rows** (under a different, older `Id_Sim=3322`, clients `GUESS KIDS`/`Sartex`/`GUESS EUROPE`). **CONFIRMED, positive match**: `CI` and `Code_Sim` share the same code space for numeric 12-digit fabric-article codes. This is real, demonstrated evidence of the bridge Task 1 was looking for — not a 100%-coverage join (only 1 of 5 spot-checked codes matched, and it matched a *different* simulation than the one it came from, which is consistent with fabric articles being reused across seasons/simulations), but a genuine, non-coincidental structural link.
- `DateAccesoire` / `EtatAccessoire` pair gives **the first confirmed date→week conversion evidence in this project**: rows with `DateAccesoire = 2025-07-30` have `EtatAccessoire = '202531'`. Computing the ISO calendar week of 2025‑07‑30 gives **ISO week 31 of 2025** — an exact match. **CONFIRMED (computed, not assumed)**: the week-numbering convention used in this data is **standard ISO‑8601 week numbering**, expressed as `YYYY` + 2-digit ISO week (matching the `Sem_Sim` format already seen in Task 1). This directly answers one of Task 1's CRITICAL open questions, at least for this table; it has not yet been directly confirmed for `SemTheorique` itself (still empty everywhere).
- `EtatAccessoire` takes two kinds of values: the literal string `"NL"` (when `DateAccesoire` is missing — plausibly "Non Livré" = "not delivered/received", HYPOTHESIS) or the `YYYYWW` week string (when `DateAccesoire` is populated). This is analogous to the Task-1 finding that `EtatOkProduction` mirrors `DateOKProduction` — reinforcing the pattern that several `Etat*` fields are **not independent categorical codes** but rather **derived displays of a corresponding date** (or an absence marker).
- `PrevStock` takes values `'S'` or `'N'`, correlated exactly with whether `DateAccesoire`/`EtatAccessoire` are populated (`'S'` when available, `'N'` when not). **INFERRED**: `S`/`N` = "Oui"/"Non" (Yes/No) style flag for "stock foreseen/available", consistent with French `Stock`.
- `QteResev` (reserved quantity) is `0` in every row of this sample — no evidence either way about how it behaves when non-zero.

### A.2 `table.xlsx` — sheet `tablerecappoi_piq` (8 rows, 255 columns)

This is a very large denormalized "recap" export, richer than the SQL POI table, evidently built for reporting/planning use rather than being the live transactional table. Only a fraction of the 255 columns were populated in this sample (typical of a wide reporting table where most fields apply to later production stages not yet reached for these example rows).

- `POIntern` values (`"01.006.DOOSAN FL09 WW4"`, `"01.008.170281"`, `"01.007.806121"`) use a **dotted hierarchical scheme** (`prefix.subcode.reference`), completely different in shape from `plan_t_simplanifpoi.POI_Sim` (`"0133898091CD"`). **No format overlap found; no join key demonstrated between `POIntern` and `POI_Sim`.**
- `POCl` ("PO Client") appears to be the trailing component of `POIntern` in at least one case (`POIntern="01.008.170281"`, `POCl="170281"`) — a **CONFIRMED, demonstrated relationship within this table**: `POIntern = <prefix>.<POCl-or-similar>`. This does not, by itself, bridge to `POI_Sim`.
- `CodeT` (e.g. `56278117`) and `CodeQualit` (e.g. `56278`) are related — `CodeT` appears to be `CodeQualit` with a numeric suffix appended (fabric quality/article code with a batch or width qualifier). **INFERRED**, consistent pattern across all 6 populated rows.
- `NomFrs` (supplier name) contains **real external fabric-mill names**: `ISKO DOKUMA`, `NUOA TESSILBRENTA`, `LEGLER`, `SWIFT`. This is different from `Sartex`, which is the value seen dominating the `Client` column of `plan_t_simplanifstock`. **This clarifies the Task 1 "Sartex" open question**: `NomFrs` = the actual raw-material supplier/mill, while `Sartex` (stock table) behaves like an **internal receiving/holding entity** distinct from both the mill and the end client — most plausibly the company's own fabric-sourcing/warehousing division or a sister company, consistent with this being a Tunisian textile-manufacturing group. **Still not formally confirmed by an engineer — INFERRED, but now backed by two independent pieces of evidence** (this table's `NomFrs`≠`Sartex` distinction, plus `cde.xls`'s `DateSouhSartex` field, see A.3).
- `Tissu` column holds `"Oui"/"Non"` values — a plausible, directly-usable answer to Task 1's open question "how do we know a component is required?", **at least for the main-fabric component in this particular reporting table**. This field does not exist under this name in the `plan_t_simplanifpoi` SQL schema, so it cannot yet be used as-is in the simulator without confirming whether an equivalent flag exists at the transactional level. **HYPOTHESIS / promising lead, not yet portable to the SQL data.**
- `TypepPcs` (garment type label, e.g. `"Pant à Court"`, `"Pantalon"`) and `Consom` (style-specific fabric consumption, e.g. `0.93294`, `1.32434`) — see cross-reference with `consommation_tissu_par_type.xlsx` in A.4 below.
- Rows 0–1 have `Client = "Collection"` / `"Collection3"` and `POIntern = "Collection"` / `"POColtTeintr"` — clearly **placeholder/sample-development rows**, not real client orders. This reinforces the Task 1 hypothesis that some records in this ecosystem represent development/collection-stage items rather than production POIs, though it does not directly confirm that hypothesis for `Id_Sim=5601` specifically.
- Column list confirms several previously-guessed business concepts by name alone (still to be validated against real values, since no other rows populate them): `EtatTissu`, `EtatTissuSec`, `EtatFourniture` (matching SQL POI names exactly — same table lineage, OBSERVED), `SemPrevOkProd`, `SemPrevRecpTiss`, `SemPrevRecpDblr`, `SemPrevRecpFrnt` (predicted-reception-week fields per component — a strong **structural** hint, not yet value-tested, that `DateTissu`/`DateFourniture` in the SQL table may originate from a "predicted reception week" concept rather than a stock-quantity calculation). `Doublure` (lining) is the plain-French term matching `TissuSec` (secondary fabric = lining). **INFERRED naming clarification**, not a tested value relationship.

### A.3 `cde.xls` — four sheets (fabric and accessory order/reception tracking)

- **`Liste cde tissu`** (fabric order headers, 12 rows): columns `N°Order`, `Date`, `N°Client`, `Saison`, `EtatCde`, `POI`, `CodeFrs`, `Cde_Interne`. **Important negative finding**: the `POI` column here contains a **date value** (e.g. `"02/01/2026"`), not a POI identifier — despite the column name. This is a direct, concrete confirmation of the project's own warning not to trust column names: **`POI` in this sheet ≠ `POI_Sim`; it is unrelated, coincidentally-named field.**
- **`detail prevision reception`** (fabric reception forecast, 2 rows): links to the header via `N°Order`; contains `CodeTissu`, `CodeColoris`, `Date` (order-line date), `Qté`, `DatePr` (forecast reception date), `Recu` (boolean, `-1`/`0` pattern — CONFIRMS the legacy `-1`=True convention again, now in a third table), `DateRecR` (actual reception date). This is a genuine **order → forecast → actual reception** pipeline for fabric, structurally exactly what would be needed to reconstruct a fabric availability date — but the sample is too small (2 rows, `CodeTissu`/`CodeColoris` both blank) to test any join to `Code_Sim`/`CI`.
- **`cde FN`** (accessory/supply order headers, 4 rows): contains `DateSouhSartex` ("date souhaitée Sartex" — desired date at/by Sartex) and `DateReelRecept` (actual reception date), `Valide` (`-1`/`0` boolean again), `EtapeCde` (order stage, numeric). **This is the second independent confirmation that "Sartex" is a real, named operational entity in the order/reception process** — specifically tied to accessory ("FN" = Fourniture) orders, not just an incidental value in the stock table's `Client` column.
- **`detail reception FN`** (accessory/thread reception detail, 10 rows): `NCde` matches the `N°Cde` from `cde FN` (confirmed order-number bridge between header and detail). `CI` values here are `"YT33537"`, `"YT35713"`, `"YT36151"`, etc. — the **same `YT#####` prefix pattern found in `plan_t_simplanifpoi.LastFil`** (Task 1 sample: `"YT08654:1712 Tex 60 Epic"`) — **CONFIRMED**: `CI` in this reception sheet and the thread-reference embedded in `LastFil` share the same code family, and (see A.5) this same `YT#####` pattern is independently and heavily present in `plan_t_simplanifstock.Code_Sim` (60,451/116,200 rows, 52%). This is a real, demonstrated three-way structural link: **reception detail `CI` ↔ POI `LastFil` ↔ stock `Code_Sim`, all using the `YT#####` thread-code scheme.**

### A.4 `consommation_tissu_par_type.xlsx` (48 rows)

- A clean reference/lookup table: `codeType` (small integer), `TypePcs` (French garment-type label, e.g. `Pantalon`, `Blouson`, `Chemise`), `TypePcs_Eng` (English translation), `Cons_Tissu` (a coefficient, e.g. `1.3`, `1.8`, `1.5`).
- Cross-checked directly against `tablerecappoi_piq`: the garment-type label `"Pantalon"` appears in both files; `tablerecappoi_piq` also has a row with `TypepPcs="Pant à Court"` and a specific `Consom=0.93294`, versus this lookup table's generic `Cons_Tissu=1.5` for the same `"Pant à Court"` type code (row `codeType=13`). **CONFIRMED relationship**: `Cons_Tissu` is a **generic/default fabric-consumption coefficient per garment type**, distinct from and typically different in value from the POI-specific, pattern-measured `Consom` field in `tablerecappoi_piq`. **HYPOTHESIS** (plausible, not confirmed by an engineer): `Cons_Tissu` may serve as a fallback estimate for `BesoinTissu` before a real pattern-based `Consom` is available for a given style — this would explain why the project keeps both a generic table and a per-style field.
- Several `codeType` rows have `Cons_Tissu = 0.0` (e.g. `Short`, `Bandana`, `Top`, `casquette`) — plausibly items with no meaningful fabric-consumption ratio in this scheme (e.g. accessories rather than cut-and-sew garments), or genuinely unpopulated defaults. **UNKNOWN**, not investigated further given the small effort budget for this reference table.

### A.5 `Code_Sim` Format Breakdown (revisited with new evidence)

Re-querying `plan_t_simplanifstock.Code_Sim` by length across all 116,200 rows gives a clean, four-way split:

| Length | Row count | Example | Likely meaning (evidence) |
|---:|---:|---|---|
| 7 | 97,764 (84%) | `YT05035` | **Thread code** — confirmed via `cde.xls` reception `CI` and POI `LastFil` |
| 8 | 9,338 (8%) | `USA00547` | Brand/division-prefixed style or article code (matches client `7 FOR ALL MANKIND USA`) — INFERRED |
| 6 | 8,973 (8%) | `H10741` | Brand-prefixed code (`H` ≈ Hugo Boss) — INFERRED |
| 12 | 125 (0.1%) | `689037021001` | **Fabric-article code** — confirmed via direct match with `plan_t_simplaniffourniture.CI` |

This resolves, with much more confidence than Task 1 could, the open question "what does `Code_Sim` represent?": **it is a heterogeneous field whose meaning depends on a recognizable prefix/length pattern**, not a single business object. A future simulator should classify `Code_Sim` by this pattern before attempting to use it, rather than treating it as one homogeneous "material code."

### A.6 PO PDFs (`PO_3034174...`, `PO_3034281...`)

- Both are **customer/finished-goods sales purchase orders**, not fabric/material purchase orders. Seller = `DENIM HOUSE` (seller code `72000022`), a Tunisian garment manufacturer (Ksar Hellal), selling finished jeans styles (`7UCJ0A53-3RX2x`, `7U4X0A53-3RX2x`) to brand buyers (`Seven for all Mankind International SAGL` / `Seven for all Mankind USA`, via logistics partner `Bleckmann Nederland B.V.`).
- `DENIM HOUSE` and `7 FOR ALL MANKIND` / `7 FOR ALL MANKIND USA` are both real, independently-seen `Client` values in `plan_t_simplanifstock` (Task 1 top-client list). **CONFIRMED, real cross-source name match** — these PDFs describe orders for brands that genuinely appear elsewhere in this project's data ecosystem, even though no record-level (row-level) match could be established.
- Each line item carries a style/colorway code (`7UCJ0A53-3RX23`), a delivery date (`Dlv. date`, format DD/MM/YY), and a **customer order number** (`DH002881`, `DH002882`). These item codes and order numbers **do not match the format of `POI_Sim`, `POIntern`, or `Code_Sim`** in any of the other sources inspected. **No row-level match established — explicitly reporting "NOT SUPPORTED" rather than guessing.**
- `POCl` (client-PO field seen in `tablerecappoi_piq`) is plausibly meant to hold values like `DH002881` in general (the field name literally suggests "PO Client"), but this could not be confirmed since no sampled `POCl` value happened to match this format. **HYPOTHESIS, plausible but unconfirmed.**

---

## B. Cross-Source Relationship Map (Only Demonstrated Links)

```
plan_t_simplanif.Id_Sim (10775)
        │  CONFIRMED — same Id_Sim literally present
        ▼
plan_t_simplaniffourniture.Id_Sim (10775)
        │  demonstrated within-file relationship (POIntern-style POI naming, TypeFourniture, Besoin, DateAccesoire)
        │  CI (12-digit numeric) ──── CONFIRMED format+value match (1 of 5 spot-checked) ────▶ plan_t_simplanifstock.Code_Sim
        │
        ▼ (POI field, dotted-hierarchical id — NOT the same shape as POI_Sim)
"01.XXX.reference" naming space  ◀── shared naming pattern (not a tested join) ──▶ tablerecappoi_piq.POIntern

cde.xls "cde FN" (N°Cde) ──CONFIRMED── "detail reception FN" (NCde)
cde.xls "detail reception FN".CI (YT#####) ──CONFIRMED format match── plan_t_simplanifpoi.LastFil (YT#####...)
                                          ──CONFIRMED format match── plan_t_simplanifstock.Code_Sim (YT#####, 52% of rows)

consommation_tissu_par_type.Cons_Tissu (by TypePcs) ──CONFIRMED value relationship (same label, different magnitude)── tablerecappoi_piq.Consom (by TypepPcs)

PO PDFs (client, style codes, customer order no.) ──CONFIRMED name-level only── plan_t_simplanifstock.Client (DENIM HOUSE, 7 FOR ALL MANKIND[ USA])
                                                    ──NOT SUPPORTED (no format/value match)── POI_Sim / POIntern / Code_Sim
```

**Still NOT bridged, even with these new sources:** a direct, row-level key from `plan_t_simplanifpoi.POI_Sim` to anything else (`POIntern`, `Code_Sim`, `CI`, PO item codes). Every new source either uses its own identifier scheme or, where it shares a scheme (like `plan_t_simplaniffourniture.POI` using the `POIntern`-style dotted format), still doesn't match `POI_Sim`'s `"0133898091CD"` shape.

---

## C. POI → Material → Stock Investigation (Central Deliverable)

| Path | Status | Evidence |
|---|---|---|
| `POI_Sim` → `Code_Sim` (direct) | **NOT SUPPORTED** | Task 1: 0/185 direct matches on the one shared simulation |
| `POI_Sim` → `POIntern`/`plan_t_simplaniffourniture.POI` (direct) | **NOT SUPPORTED** | Different code shapes (`CD`-suffixed vs. dotted hierarchical); no shared sample row to test |
| `plan_t_simplaniffourniture.CI` → `Code_Sim` | **PARTIALLY SUPPORTED** | 1 of 5 spot-checked 12-digit codes matched (different `Id_Sim`, same code) |
| `LastFil` (POI) → `CI` (accessory reception) → `Code_Sim` (stock, `YT` prefix) | **SUPPORTED (format-level)** | Same `YT#####` naming scheme confirmed in three independent sources |
| `Id_Sim` (POI) → `Id_Sim` (`plan_t_simplaniffourniture`) → `Id_Sim` (`plan_t_simplanif`) | **SUPPORTED, for `Id_Sim=10775`** | Real, existing value chain (unlike the Task-1 POI extract's `Id_Sim=5601`, which matched nothing) |
| `tablerecappoi_piq.POCl` → PO PDF "Customer order no" | **HYPOTHESIS, unconfirmed** | Field name is suggestive; no matching sample value found |

**Overall conclusion for this section:** the supporting files did **not** produce a clean, single, confirmed POI→Material→Stock key path. They did, however, produce the first **positive, demonstrated evidence** (rather than pure hypothesis) that the material-code space used in `Code_Sim`/`CI`/`LastFil` is shared and internally consistent — the missing piece is specifically the **POI-level bridge** (how a `POI_Sim` value maps to one or more `CI`/fabric codes). None of the six supporting files contain a table that stores `POI_Sim` next to a fabric/material code in the exact `POI_Sim` format; the closest candidate (`plan_t_simplaniffourniture.POI`) uses a different identifier scheme.

---

## D. Business Logic Evidence — What Can Now Be Supported

| Business Concept | Source | Evidence | Status |
|---|---|---|---|
| POI identification | SQL, `tablerecappoi_piq`, `plan_t_simplaniffourniture` | **At least three different identifier schemes coexist** (`POI_Sim`, `POIntern`, `plan_t_simplaniffourniture.POI`) with no demonstrated cross-mapping | OBSERVED — unresolved multiplicity, not a single confirmed identifier |
| Fabric requirement (`BesoinTissu`) | `plan_t_simplaniffourniture.Besoin` (TypeFourniture='Tissu'), `consommation_tissu_par_type.Cons_Tissu`, `tablerecappoi_piq.Consom` | Three related-but-distinct quantity concepts found; no formula tested end-to-end | HYPOTHESIS — plausible aggregation/estimation chain, not proven |
| Fabric code | `Code_Sim` (12-digit numeric), `CI` | Confirmed shared code space (1 real match found) | PARTIALLY CONFIRMED |
| Fabric availability (`DateTissu`) | `plan_t_simplaniffourniture.DateAccesoire`/`EtatAccessoire` (when `TypeFourniture='Tissu'`), `cde.xls` reception dates, `tablerecappoi_piq.SemPrevRecpTiss` | Structural candidates identified; none tested against a real, populated `DateTissu` (still 100% NULL in the only POI extract available) | HYPOTHESIS |
| Accessory/thread availability | `plan_t_simplaniffourniture` (`TypeFourniture` other than 'Tissu', not observed in this 19-row sample), `cde.xls` "FN" sheets, `YT` thread codes | Structural pipeline (order → reception → `CI`) fully evidenced for thread; fabric-vs-accessory distinction within `plan_t_simplaniffourniture` not directly observed (sample only contained 'Tissu' rows) | PARTIALLY SUPPORTED |
| OK Production | No new evidence found in Task 2 sources | — | UNKNOWN (same as Task 1) |
| Stock availability | `Client='Sartex'` clarified as likely internal entity (mill/warehouse), distinct from `NomFrs` (external mill) and from end-client brands | Two independent naming clues (`NomFrs`≠Sartex; `DateSouhSartex` field) | INFERRED, not confirmed by engineer |
| Theoretical date/week conversion | `DateAccesoire`→`EtatAccessoire` (2025-07-30 → ISO week 31 → `202531`) | **Directly computed and matched** | CONFIRMED (for this field pair; not yet directly confirmed for `SemTheorique`/`DateMax`) |
| Blocking element | Cahier des charges confirms this is a required output, gives no tie-break rule; no new data evidence | — | Still UNKNOWN (unchanged from Task 1) |
| Component "required vs. not applicable" | `tablerecappoi_piq.Tissu` = "Oui"/"Non" | One usable flag found, but only in a different (reporting) table than the SQL POI table | HYPOTHESIS / promising lead |

---

## E. Updated Open Questions (from Task 1)

**CRITICAL**
1. Why are the datasets from different periods? → **STILL UNKNOWN.** The cahier des charges (§0) doesn't address extraction methodology; the supporting files don't explain it either. Recommend asking directly.
2. Nature of `Id_Sim = 5601`? → **STILL UNKNOWN**, but a plausible new lead: `tablerecappoi_piq` shows genuine "Collection"-labeled placeholder rows exist in this business's data model, and the cahier des charges confirms the whole project may lean on simulated/illustrative data — both are consistent with, but do not prove, the Task 1 "development simulation" hypothesis for `5601`.
3. Can any supporting source provide populated historical `SemTheorique`/`DateMax`? → **NO.** None of the six files contain `SemTheorique` or `DateMax` at all. **STILL UNKNOWN / requires a different data pull.**

**HIGH**
4. What does `Client = Sartex` mean? → **PARTIALLY ANSWERED.** Strong circumstantial evidence (two independent sources) that it is an internal entity distinct from both the external fabric mill (`NomFrs`) and the end-client brand. Not confirmed by an engineer.
5. What do `Etat*`/`Statut*` fields mean? → **PARTIALLY ANSWERED.** New evidence (`EtatAccessoire`) reinforces the Task 1 pattern that some `Etat*` fields mirror a date (as `YYYYWW`) or hold a short absence code (`NL`), rather than being generic status codes. Still no confirmed dictionary for `Statut*` single-letter codes (`S`, `R`).
6. What does `Code_Sim` represent? → **PARTIALLY ANSWERED.** Now resolved into four distinguishable sub-formats by length/prefix (thread, two brand-style schemes, fabric-article), rather than one meaning.
7. Is there a POI ↔ fabric/material mapping? → **PARTIALLY ANSWERED.** The material-code space itself is now confirmed to be shared and consistent (`CI`≈`Code_Sim`≈`LastFil` family), but the **POI-level bridge is still missing** — no source ties a `POI_Sim` value to a specific `CI`/`Code_Sim` value directly.

**MEDIUM**
8. What do negative/zero stock quantities represent? → **STILL UNKNOWN.** No new evidence.
9. Can `BesoinTissu` be independently explained? → **PARTIALLY ANSWERED.** A plausible three-tier chain now has structural support: generic coefficient (`Cons_Tissu`) → style-specific consumption (`Consom`) → per-line requirement (`plan_t_simplaniffourniture.Besoin`) → aggregated `BesoinTissu`. Not proven end-to-end with matching values.
10. Can availability dates be reconstructed from orders/receptions? → **PARTIALLY ANSWERED.** The pipeline structure (order header → reception detail → date fields) is now confirmed to exist for both fabric (`cde.xls` "tissu" sheets) and accessories/thread (`cde.xls` "FN" sheets), but sample sizes (2–10 rows) are far too small to validate a formula, and no populated `DateTissu`/`DateFil` example exists yet to check the reconstruction against.

---

## F. Contradictions Found

| # | Contradiction | Sources |
|---|---|---|
| 1 | `POI` (column name) in `cde.xls`/"Liste cde tissu" is a **date**, not a POI identifier | `cde.xls` vs. naming expectation set by `plan_t_simplanifpoi.POI_Sim` |
| 2 | `plan_t_simplaniffourniture` is documented/assumed as an "accessories" table, but the only sample available contains exclusively `TypeFourniture='Tissu'` (fabric) rows | `Data_Relationships.md` §10 vs. `table.xlsx` |
| 3 | `NomFrs` (real external mill names) vs. `Client='Sartex'` (stock table) shows these are **not the same concept**, contradicting a naive reading of "supplier"/"client" as interchangeable | `tablerecappoi_piq` vs. `plan_t_simplanifstock` |
| 4 | `Code_Sim` was implicitly treated as one homogeneous "material code" in prior docs; it is demonstrably **four different code families** by length/prefix | This task's A.5 analysis |

No contradiction was found between the cahier des charges and the existing MD documentation regarding the core `MAX()` formula itself — that part is consistently and correctly represented everywhere.

---

## G. Recommendation

**Can the project now define:**

1. **The data model** — **PARTIALLY.** The three-SQL-table model from Task 1 stands, and we now have a fourth confirmed table (`plan_t_simplaniffourniture`) with a demonstrated `Id_Sim` link and partial `Code_Sim` bridge. But the model still cannot include a confirmed POI↔material key, and the multiple incompatible POI identifier schemes (`POI_Sim`, `POIntern`, `plan_t_simplaniffourniture.POI`) are an unresolved structural gap, not just a documentation gap.
2. **The business logic** — **PARTIALLY.** The `MAX()` rule itself is now doubly confirmed (business docs + cahier des charges), and the date→week (ISO) conversion is now confirmed by a real computed example. But component-requirement rules (what counts as "applicable"), tie-breaking, and the exact `DateTissu`/`DateFourniture`/`DateFil`/`DateOKProduction` calculation are still not confirmed end-to-end from real populated data.
3. **A baseline simulator** — **NO, not for historical validation purposes.** We still have zero rows anywhere across nine files where `SemTheorique` (or `DateMax`) is populated. A baseline simulator's pure calculation function (`MAX` + ISO week conversion + blocking-element identification) **can** be written and unit-tested now, using the newly-confirmed ISO week convention and the cahier des charges' own worked example as a test case — but it cannot yet be validated against real company history.

**Overall: PARTIALLY ready.** The project has significantly more structural understanding than after Task 1, and several previously-open questions are now genuinely (if only partially) answered with real evidence. What is still missing is not more documentation or more small sample files — it is **one real extraction** containing: (a) POI rows with populated `SemTheorique`/component dates, and (b) a consistent `Id_Sim`/POI-identifier space shared with the stock and fourniture tables.

---

## TASK 2 STATUS

**Sources analyzed:**
- `table.xlsx` (2 sheets, full content)
- `cde.xls` (4 sheets, full content)
- `consommation_tissu_par_type.xlsx` (1 sheet, full content)
- `PO_3034174_72000022_Ladies.pdf`, `PO_3034281_72000022_Ladies.pdf` (full text)
- `RapportStageSimulateurDisponibilite.pdf` (full text, 5 pages)
- Existing MD documentation and `TASK1_Raw_SQL_Deep_Analysis.md` (for comparison)

**Important discoveries:**
- `RapportStageSimulateurDisponibilite.pdf` is the project's own cahier des charges (assignment brief), not an external report — it explicitly allows a *simulated* dataset, which reframes Task 1's data-quality gaps.
- `plan_t_simplaniffourniture.Id_Sim=10775` genuinely exists in `plan_t_simplanif` — the first confirmed cross-table `Id_Sim` link found in this project.
- `DateAccesoire → EtatAccessoire` gives a directly computed, confirmed ISO-week conversion example (`2025-07-30 → 202531`).
- `Code_Sim` resolved into 4 distinguishable code families by length/prefix, one of which (`YT#####`, thread) is confirmed to also appear in `LastFil` and `cde.xls` reception detail.

**POI ↔ Material mapping:**
- Still not directly established at the row level. Three incompatible POI identifier schemes found (`POI_Sim`, `POIntern`, `plan_t_simplaniffourniture.POI`); none of the six new files bridges them.

**Material ↔ Stock mapping:**
- Partially established: 1 of 5 spot-checked `CI` (fabric) codes matched a real `Code_Sim` value; thread codes (`YT#####`) confirmed shared across `LastFil`, `cde.xls` reception `CI`, and 52% of all stock rows.

**Business rules confirmed:**
- The `MAX()` theoretical-week rule is the official target (cahier des charges).
- ISO-8601 week numbering is used (computed and matched).
- `N°Cde`/`NCde` genuinely bridges order headers to reception details.

**Business rules inferred:**
- `Sartex` = internal entity, distinct from external mills and end clients.
- `Etat*` fields often mirror a date (as week number) or an absence code, rather than being independent status codes.
- `Cons_Tissu` (generic) vs. `Consom` (style-specific) form a two-tier fabric-consumption estimate.

**Hypotheses:**
- `tablerecappoi_piq.Tissu` ("Oui"/"Non") as a component-required flag.
- `POCl` as the field meant to carry customer PO numbers like those seen in the PO PDFs.
- A `Besoin`(fourniture) → aggregation → `BesoinTissu` chain.

**Open questions resolved:** Q4, Q5, Q6, Q7 (Task 1 HIGH) — partially. Q9, Q10 (Task 1 MEDIUM) — partially.

**Open questions remaining:** Q1, Q2, Q3 (Task 1 CRITICAL) — unresolved. Q8 (Task 1 MEDIUM) — unresolved. Plus new: exact POI-identifier reconciliation across schemes; confirmation of `Sartex`, `S`/`R`/`NL` codes by an engineer.

**Contradictions:** 4 found (see section F) — none affecting the core `MAX()` rule.

**Critical missing data:** a POI/simulation extract with populated `SemTheorique`/`DateMax`/component dates, and any single table that stores `POI_Sim` alongside a material/fabric code in a directly matching format.

**Can we define the baseline simulator?**
**PARTIALLY.**

**Reason:**
The pure calculation function (MAX of available component dates → ISO week → blocking element) can be written and unit-tested today using confirmed rules and a confirmed week-conversion example. It cannot yet be validated against real historical results, and the component-availability *input* side (how `DateTissu`, `DateFourniture`, `DateFil`, `DateOKProduction` are actually derived from stock/orders/receptions) is still only partially evidenced, not provable end-to-end.

**Recommended next step:**
1. Request one consistent extract containing populated `SemTheorique` and component dates for validation (same ask as Task 1).
2. Ask the engineer to confirm: the identity/role of `Sartex`; the meaning of `Statut*` single-letter codes (`S`, `R`); and how (if at all) `POI_Sim`, `POIntern`, and `plan_t_simplaniffourniture.POI` relate to each other.
3. In parallel, implement and unit-test the pure `MAX()`/ISO-week/blocking-element function against the cahier des charges' own worked example and synthetic edge cases (missing component, tie, invalid date) — this is safe to start now and does not require the missing data above.
