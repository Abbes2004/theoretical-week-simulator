# Canonical Dataset Specification

## Purpose
Define the canonical dataset consumed by the simulator after ingestion, validation, cleaning, and integration.

## Principle
Raw SQL/Excel/PDF sources remain immutable source-of-truth artifacts. The canonical dataset is a derived analytical layer.

## Target Grain
One row per simulated POI: `(Id_Sim, POI_Sim)`.

## Required Schema

| Field | Type | Role | Status |
|---|---|---|---|
| `id_sim` | integer/string | Simulation identifier | Confirmed |
| `poi_sim` | string | POI identifier | Confirmed |
| `date_tissu` | date | Main fabric availability | Candidate |
| `date_tissu_sec` | date | Secondary fabric availability | Candidate |
| `date_fourniture` | date | Supplies availability | Candidate |
| `date_fil` | date | Thread availability | Candidate |
| `date_ok_production` | date | Production approval | Candidate |
| `date_theorique` | date | Maximum applicable date | Derived |
| `iso_year` | integer | ISO year | Derived |
| `iso_week` | integer | ISO week | Derived |
| `week_key` | string | `YYYYWW` | Derived |
| `sem_theorique` | string | Final theoretical week | Derived |
| `blocking_element` | string/list | Latest component(s) | Derived |
| `calculation_status` | enum | Calculation state | Derived |
| `data_origin` | enum | REAL/SYNTHETIC/DERIVED | Required |
| `data_quality_flag` | string/list | Quality information | Required |

## Applicability
Each component must be classified as `NOT_REQUIRED`, `REQUIRED_AND_AVAILABLE`, `REQUIRED_BUT_UNAVAILABLE`, or `UNKNOWN`.

A NULL date must never be silently converted to an arbitrary date.

## Core Calculation
For applicable components with valid availability dates:

`date_theorique = MAX(applicable availability dates)`

Then derive the theoretical week.

## Provenance
Every canonical row must remain traceable to its source table/file, source identifiers, transformations, and rule version.

## Current Limitation
The supplied POI extract has `SemTheorique`, `DateMax`, `DateTissu`, and `DateTissuSec` completely NULL, so it cannot validate the complete historical calculation.
