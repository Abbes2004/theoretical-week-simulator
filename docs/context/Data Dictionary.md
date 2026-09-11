# Data Dictionary

## 1. Purpose

This document defines the currently understood meaning of the main fields relevant to the theoretical production week simulator.

The meaning of a field is classified as:

- **Confirmed**: directly supported by the available project information.
- **Observed**: derived only from the database structure/name.
- **To validate**: requires confirmation through data analysis or business logic reconstruction.

---

# 2. Simulation Table — `plan_t_simplanif`

## Identification

| Field | Meaning | Status |
|---|---|---|
| `Id_Sim` | Unique simulation identifier | Confirmed |
| `Type_Sim` | Type of simulation | Observed |
| `Categ_Sim` | Simulation category | Observed |
| `Date_Sim` | Simulation date/time | Observed |
| `User_Sim` | User who created/launched the simulation | Observed |

## Simulation Context

| Field | Meaning | Status |
|---|---|---|
| `Sem_Sim` | Simulation week | Observed |
| `Client_Sim` | Client concerned by the simulation | Observed |
| `Division_Sim` | Division/business unit | Observed |
| `Saison_Sim` | Season | Observed |
| `Model_Sim` | Model | Observed |
| `Tissu_Sim` | Fabric-related simulation context | To validate |
| `Prog_Sim` | Program information | To validate |
| `Etape_Sim` | Process/planning step | To validate |

## Status / Control

| Field | Meaning | Status |
|---|---|---|
| `Cloture_Sim` | Simulation closure status | Observed |
| `Creat_Sim` | Creation/status indicator | To validate |
| `Valid_Sim` | Validation indicator | Observed |
| `Annul_Sim` | Cancellation indicator | Observed |
| `Dat_Valid_Sim` | Validation date | Observed |
| `User_Valid_Sim` | User who validated | Observed |
| `Priorite_Sim` | Simulation priority | Observed |
| `Etat_Element` | Element state | To validate |
| `Type_POI` | POI type | To validate |

---

# 3. POI Table — `plan_t_simplanifpoi`

## Identification

| Field | Meaning | Status |
|---|---|---|
| `Id_SimPoi` | Unique POI record identifier | Confirmed |
| `Id_Sim` | Simulation identifier linking the POI to a simulation | Strongly supported |
| `POI_Sim` | POI/business item identifier | To validate |
| `IdSim_Racine` | Root/original simulation identifier | To validate |

---

# 4. Main Fabric

| Field | Current interpretation | Status |
|---|---|---|
| `BesoinTissu` | Required fabric quantity | Observed |
| `DateTissu` | Fabric-related availability date | Candidate input |
| `DispTissu` | Fabric availability information | To validate |
| `EtatTissu` | Fabric state | To validate |
| `tauxDispTissu` | Fabric availability rate | To validate |
| `IndTissu` | Fabric indicator | To validate |
| `DatIndTissu` | Date of fabric indicator update | Observed |
| `UserIndTissu` | User related to the indicator update | Observed |

### Potential role

```text
Fabric source data
      ↓
Availability evaluation
      ↓
DateTissu
      ↓
Week(Tissu)
```

The exact logic producing `DateTissu` is not yet known.

---

# 5. Secondary Fabric

| Field | Current interpretation | Status |
|---|---|---|
| `DateTissuSec` | Secondary fabric-related availability date | Candidate input |
| `StatutTissuSec` | Secondary fabric status | To validate |
| `EtatTissuSec` | Secondary fabric state | To validate |
| `tauxDispTissuSec` | Secondary fabric availability rate | To validate |
| `IndTissuSec` | Secondary fabric indicator | To validate |
| `DatIndTissuSec` | Indicator update date | Observed |
| `UserIndTissuSec` | User related to update | Observed |

---

# 6. Accessories / Supplies

| Field | Current interpretation | Status |
|---|---|---|
| `DateFourniture` | Supplies-related availability date | Candidate input |
| `LastFourniture` | Last related supply information | To validate |
| `StatutFourniture` | Supply status | To validate |
| `EtatFourniture` | Supply state | To validate |
| `IndFourniture` | Supply indicator | To validate |
| `DatIndFourniture` | Indicator update date | Observed |
| `UserIndFourniture` | User related to update | Observed |

---

# 7. Sewing Thread

| Field | Current interpretation | Status |
|---|---|---|
| `DateFil` | Thread-related availability date | Candidate input |
| `LastFil` | Last related thread information | To validate |
| `StatutFil` | Thread status | To validate |
| `EtatFil` | Thread state | To validate |
| `IndFil` | Thread indicator | To validate |
| `DatIndFil` | Indicator update date | Observed |
| `UserIndFil` | User related to update | Observed |

---

# 8. OK Production

| Field | Current interpretation | Status |
|---|---|---|
| `DateOKProduction` | Date when production is considered ready/approved | Candidate input |
| `EtatOkProduction` | Production approval state | To validate |
| `StatutOkProduction` | Production approval status | To validate |
| `IndOkProd` | Production readiness indicator | To validate |
| `DatIndOkProd` | Indicator update date | Observed |
| `UserIndOkProd` | User related to update | Observed |

---

# 9. Theoretical Result Fields

| Field | Current interpretation | Status |
|---|---|---|
| `DateMax` | Maximum/latest relevant date | Strong candidate |
| `StatutDateTheo` | Status of theoretical date calculation | To validate |
| `SemTheorique` | Theoretical production week | Confirmed project target |
| `SemTheoriqueCoupe` | Theoretical cutting week | To validate |
| `IndSemPiq` | Theoretical sewing-week indicator | To validate |
| `DatIndSemPiq` | Date of sewing-week indicator update | Observed |

### Expected conceptual relationship

```text
DateTissu
DateTissuSec
DateFourniture
DateFil
DateOKProduction
        ↓
     DateMax
        ↓
   SemTheorique
```

This relationship is logically consistent with the project objective, but must be tested against real data.

---

# 10. Manual vs Historical Dates

Several fields exist in pairs such as:

```text
DateTissu_old
DateTissu_Manuel

DateTissuSec_old
DateTissuSec_Manuel

DateFourniture_old
DateFourniture_Manuel

DateFil_old
DateFil_Manuel

DateOKProduction_old
DateOKProduction_Manuel

DateMax_old
DateMax_Manuel
```

### Observed interpretation

The naming suggests:

- `_old`: previous/historical value;
- `_Manuel`: manually entered or overridden value.

However, the precedence rule is unknown.

Critical rule to validate:

```text
Which value should the simulator use?

Automatic calculation?
Manual value?
Old value?
A precedence rule between them?
```

This is important because an incorrect choice can change `DateMax` and therefore `SemTheorique`.

---

# 11. Decision and Validation Fields

| Field | Current interpretation |
|---|---|
| `DecisionPOI` | Decision indicator/value |
| `MotifDecision` | Reason for decision |
| `CommentaireDecision` | Decision comment |
| `ValidationPOI` | POI validation status |
| `DateValidationPOI` | Validation date/time |
| `UserValidationPOI` | Validating user |

These fields may be useful for understanding historical workflow but are not currently required for the first version of the calculation engine unless business analysis proves otherwise.

---

# 12. Stock Table — `plan_t_simplanifstock`

## Identification

| Field | Meaning | Status |
|---|---|---|
| `Id_stock` | Unique stock record identifier | Confirmed |
| `Id_Sim` | Related simulation identifier | Structurally supported |

## Stock Information

| Field | Current interpretation | Status |
|---|---|---|
| `Code_Sim` | Code/product/material identifier | To validate |
| `Taille_Sim` | Size | Observed |
| `Date_Sim` | Date associated with stock record | To validate |
| `Client` | Client | Observed |
| `Qte` | Quantity | Strongly supported |
| `NCde` | Order identifier/reference | To validate |

---

# 13. Stock Candidate Logic

The table clearly stores quantity:

```text
Qte
```

and may therefore be involved in determining whether a required material is available.

Possible conceptual logic:

```text
Required quantity
      ↓
Available stock quantity
      ↓
Enough?
 ┌────┴────┐
Yes         No
↓           ↓
Available   Wait for future availability
```

This is only a **hypothesis** until the real relationship between stock, POI and component availability is established.

---

# 14. Critical Fields for Version 1

The first simulator version should initially focus on the smallest possible set of fields:

```text
POI_Sim
Id_Sim

DateTissu
DateTissuSec
DateFourniture
DateFil
DateOKProduction

DateMax
SemTheorique
```

Then progressively investigate:

```text
BesoinTissu
Qte
DispTissu
tauxDispTissu
Statut*
Etat*
Ind*
*_old
*_Manuel
```

This prevents the first implementation from becoming unnecessarily complex.

---

# 15. Current Input/Output View

```text
                    POI
                     │
       ┌─────────────┼─────────────┐
       │             │             │
   Main Fabric   Secondary      Supplies
                 Fabric
       │             │             │
   DateTissu    DateTissuSec  DateFourniture
       │             │             │
       └─────────────┼─────────────┘
                     │
              Component dates
                     │
             ┌───────┴────────┐
             │                │
          DateFil       DateOKProduction
             │                │
             └────────┬───────┘
                      ▼
                 Latest Date
                  DateMax
                      ▼
              Date → Week conversion
                      ▼
                SemTheorique
```

---

# 16. Dictionary Rule

Column names are not sufficient to define business meaning.

For implementation purposes:

```text
Field exists
    ≠
Business meaning confirmed
```

Every field used in the simulator must be supported by either:

1. confirmed project/business information;
2. reproducible evidence from the data;
3. an explicitly documented assumption.