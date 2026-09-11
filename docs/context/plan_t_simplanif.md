# SQL Reference — `plan_t_simplanif`

## 1. Document Purpose

This document is a reference for the SQL source file:

`plan_t_simplanif.sql`

It documents the structure, fields, constraints, and directly observable characteristics of the table `plan_t_simplanif`.

> **Important:** This document is derived from the raw SQL dump.  
> The raw SQL file remains the authoritative source whenever an exact schema, value, or data-level verification is required.

---

## 2. Source Information

| Property | Value |
|---|---|
| Source database | `production` |
| Target database | `production` |
| Source host | `192.168.0.50` |
| Target host | `192.168.0.50` |
| Export date | `31/03/2026 11:04:13` |
| Table | `plan_t_simplanif` |
| Storage engine | InnoDB |
| Character set | latin1 |
| Auto-increment start in dump | 12040 |

These values are explicitly present in the SQL dump. **CONFIRMED BY SQL.**

---

## 3. Table Role

`plan_t_simplanif` represents the **simulation-level information**.

A row is identified by `Id_Sim`.

The table contains information related to:

- simulation type and category;
- simulation date and user;
- simulation week;
- validation/closure/cancellation state;
- calculation dates;
- client and product/planning context;
- priority and notification/reservation parameters;
- POI-related configuration;
- element state.

**CONFIRMED BY SQL:** the table is explicitly named `plan_t_simplanif` and contains one primary key, `Id_Sim`.

**OBSERVED:** the table appears to represent the parent/header level of a simulation, while detailed POI information is stored separately in `plan_t_simplanifpoi`.

---

## 4. Table Grain

### Grain

One row corresponds to one simulation identified by:

`Id_Sim`

### Primary Key

```text
PRIMARY KEY (Id_Sim)
```

**CONFIRMED BY SQL.**

### Foreign Keys

No explicit foreign-key constraint is defined in the table.

However, `Id_Sim` is a strong candidate for a relationship with:

```text
plan_t_simplanifpoi.Id_Sim
plan_t_simplanifstock.Id_Sim
```

This relationship must be validated using the actual data and not assumed to be a formal database FK.

---

## 5. Complete Schema

| Column | SQL Type | Default | Description / Role |
|---|---|---|---|
| `Id_Sim` | `int(11)` | — | Unique simulation identifier |
| `Type_Sim` | `varchar(20)` | `NULL` | Simulation type |
| `Categ_Sim` | `varchar(25)` | `NULL` | Simulation category |
| `Date_Sim` | `datetime` | `NULL` | Simulation date/time |
| `User_Sim` | `varchar(50)` | `NULL` | User associated with simulation |
| `Obs_Sim` | `varchar(150)` | `NULL` | Observation/comment |
| `Dat_Cal_Priorite` | `datetime` | `NULL` | Priority calculation date/time |
| `Cloture_Sim` | `tinyint(1)` | `0` | Closure indicator |
| `Sem_Sim` | `int(11)` | `NULL` | Simulation week |
| `Creat_Sim` | `int(11)` | `0` | Creation/status indicator |
| `Valid_Sim` | `int(11)` | `0` | Validation/status indicator |
| `Annul_Sim` | `int(1)` | `0` | Cancellation indicator |
| `Dat_Valid_Sim` | `date` | `NULL` | Validation date |
| `User_Valid_Sim` | `varchar(25)` | `NULL` | Validation user |
| `Dat_Cal_Tissu` | `datetime` | `NULL` | Fabric calculation date/time |
| `Dat_Cal_Fourniture` | `datetime` | `NULL` | Supply/accessory calculation date/time |
| `Client_Sim` | `varchar(50)` | `NULL` | Client |
| `Division_Sim` | `varchar(50)` | `NULL` | Division |
| `Saison_Sim` | `varchar(50)` | `NULL` | Season |
| `Model_Sim` | `varchar(75)` | `NULL` | Model |
| `Tissu_Sim` | `varchar(20)` | `NULL` | Fabric information |
| `Prog_Sim` | `varchar(255)` | `NULL` | Program |
| `Etape_Sim` | `int(11)` | `NULL` | Simulation step |
| `Typ_Sem_Sim` | `varchar(50)` | `NULL` | Week type |
| `Val_Sem_Min` | `int(11)` | `NULL` | Minimum week value |
| `Val_Sem_Max` | `int(11)` | `NULL` | Maximum week value |
| `Dest_Sim` | `varchar(35)` | `NULL` | Destination |
| `Priorite_Sim` | `varchar(5)` | `NULL` | Priority |
| `Notif_Sim` | `varchar(10)` | `NULL` | Notification parameter |
| `Resev_Sim` | `varchar(10)` | `NULL` | Reservation parameter |
| `Reserv_Frn_Sim` | `varchar(10)` | `NULL` | Supplier reservation parameter |
| `NewPOI_Sim` | `tinyint(1)` | `0` | New POI indicator |
| `Regr_Sim` | `tinyint(1)` | `0` | Re-grouping indicator |
| `Etat_Element` | `varchar(25)` | `NULL` | Element state |
| `Type_POI` | `int(11)` | `NULL` | POI type |
| `CrtDateAuto` | `timestamp` | `CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` | Automatic creation/update timestamp |

Schema confirmed directly by the `CREATE TABLE` statement in the SQL source.

---

## 6. Important Simulation Fields

### Identification

```text
Id_Sim
```

Main simulation identifier.

### Simulation context

```text
Type_Sim
Categ_Sim
Date_Sim
User_Sim
Obs_Sim
```

These fields describe the simulation itself.

### Planning / week

```text
Sem_Sim
Typ_Sem_Sim
Val_Sem_Min
Val_Sem_Max
```

`Sem_Sim` is explicitly stored as an integer.

**OBSERVED:** examples contain values such as `202531`, `202532`, `202533`, etc.

The exact encoding rule of these week values must be validated before implementing week calculations.

### Client / product context

```text
Client_Sim
Division_Sim
Saison_Sim
Model_Sim
Tissu_Sim
Prog_Sim
Etape_Sim
```

These fields can contain planning/product information.

### Calculation timestamps

```text
Dat_Cal_Priorite
Dat_Cal_Tissu
Dat_Cal_Fourniture
```

These fields indicate that different calculations are associated with the simulation.

**UNKNOWN:** the exact algorithm and meaning of each calculation timestamp are not established by the table schema alone.

---

## 7. Status and Control Fields

The table contains several fields represented as integer/tinyint indicators:

```text
Cloture_Sim
Creat_Sim
Valid_Sim
Annul_Sim
NewPOI_Sim
Regr_Sim
```

Examples in the dump show values such as:

```text
0
-1
1
```

Therefore, these fields should **not automatically be interpreted as simple Boolean values** without validating the application's business semantics.

In particular:

> `-1` must not automatically be converted to `False` or `True`.

The actual meaning should be confirmed from the application/business logic.

---

## 8. Date Fields

The table contains:

```text
Date_Sim
Dat_Cal_Priorite
Dat_Valid_Sim
Dat_Cal_Tissu
Dat_Cal_Fourniture
CrtDateAuto
```

There are different SQL temporal types:

- `datetime`
- `date`
- `timestamp`

The dump contains both populated and `NULL` values.

**OBSERVED:** simulations of type `Globale` often have populated calculation dates, while several `Partielle` simulations contain `NULL` calculation-related fields.

This is an observation from sample records, not a confirmed business rule.

---

## 9. Examples Observed in the Dump

Examples include simulations such as:

```text
Id_Sim = 10775
Type_Sim = Globale
Categ_Sim = Piquage
Sem_Sim = 202531
Client_Sim = DIESEL KIDS
```

and:

```text
Id_Sim = 10777
Type_Sim = Globale
Categ_Sim = Piquage
Sem_Sim = 202531
Client_Sim = RALPH LAUREN
```

Other simulation categories include:

```text
Piquage
Repassage
Devellopement A.W.
Devellopement B.W.
```

The dataset also contains both `Globale` and `Partielle` simulations.

These observations are directly visible in the SQL INSERT records.

---

## 10. Relationship to the Simulator

For the theoretical-week simulator, this table should primarily be considered the **simulation/header/context layer**.

Potential architecture:

```text
plan_t_simplanif
        |
        | Id_Sim
        |
        +--------------------+
        |                    |
        v                    v
plan_t_simplanifpoi    plan_t_simplanifstock
        |
        v
POI-level availability
        |
        v
SemTheorique
```

This is an architectural interpretation based on the schemas of the three provided SQL sources.

The exact joins and business relationships must be validated against the raw data.

---

## 11. Relevance to `SemTheorique`

`plan_t_simplanif` does **not** contain the `SemTheorique` field.

The theoretical week is stored at the POI level in:

```text
plan_t_simplanifpoi.SemTheorique
```

Therefore:

- `plan_t_simplanif` provides simulation-level context;
- `plan_t_simplanifpoi` is the main candidate table for theoretical-week computation;
- `plan_t_simplanifstock` provides stock-related information that may contribute to availability calculations.

**CONFIRMED:** `SemTheorique` itself is not a column of `plan_t_simplanif`.

---

## 12. Potential Join Key

The most important candidate relationship is:

```text
plan_t_simplanif.Id_Sim
        =
plan_t_simplanifpoi.Id_Sim
```

and:

```text
plan_t_simplanif.Id_Sim
        =
plan_t_simplanifstock.Id_Sim
```

No explicit foreign keys are declared in this SQL table.

Therefore these are **relationship candidates**, not formal FK constraints.

---

## 13. Data Quality Observations

The SQL dump shows:

- nullable fields;
- empty strings;
- different simulation types;
- different simulation categories;
- indicator values including `0` and `-1`;
- missing client/user/context information for some simulations;
- simulations with different planning modes such as `Date` and `Semaine`.

These characteristics must be taken into account when building the simulator.

**Do not assume that every row is a valid production POI simulation.**

---

## 14. What This Table Can and Cannot Establish

### CONFIRMED BY SQL

- `plan_t_simplanif` is a simulation-level table.
- `Id_Sim` is its primary key.
- `Sem_Sim` exists and is an integer.
- Calculation timestamps for fabric and supplies exist.
- Client, season, model, program and planning fields exist.
- No explicit foreign keys are declared.
- `SemTheorique` is not stored in this table.

### OBSERVED

- Both `Globale` and `Partielle` simulations exist.
- `Piquage` is frequently present as a simulation category.
- Week values appear in the form `YYYYWW`, e.g. `202531`.
- Some fields are frequently `NULL` depending on the simulation.

### UNKNOWN / TO VALIDATE

- Exact meaning of every status value (`0`, `-1`, etc.).
- Exact business meaning of `Type_Sim` and `Categ_Sim`.
- Exact calculation represented by `Dat_Cal_Tissu`.
- Exact calculation represented by `Dat_Cal_Fourniture`.
- Exact meaning of `Sem_Sim` versus the theoretical week.
- Whether all simulation rows should participate in the simulator.
- Exact relationship between simulation-level and POI-level records.
- Whether `Id_Sim` alone is sufficient for every required join.

---

## 15. Usage Rule for the Project

When implementing the simulator:

1. Treat the raw SQL dump as the source of truth.
2. Use this document for fast orientation.
3. Do not infer business rules from column names alone.
4. Validate joins using actual records.
5. Preserve `NULL`, empty strings, and status values until their semantics are established.
6. Do not use `Sem_Sim` as a substitute for `SemTheorique` without validation.
7. Any inferred relationship or business rule must be explicitly labelled as such.

---

## 16. Source Reference

Primary source:

`plan_t_simplanif.sql`

The table definition and records documented here are derived directly from the provided SQL dump.