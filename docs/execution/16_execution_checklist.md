# Project Execution Checklist

## Phase 0 — Workspace
- [ ] Repository structure
- [ ] Documentation
- [ ] README
- [ ] `.gitignore`
- [ ] Raw-data separation

## Phase 1 — Data Understanding
- [ ] Parse SQL
- [ ] Inspect Excel
- [ ] Inspect PDFs
- [ ] Profile sources
- [ ] Validate keys
- [ ] Validate dates
- [ ] Document quality issues

## Phase 2 — Integration
- [ ] Validate Simulation → POI
- [ ] Validate Simulation → Stock
- [ ] Identify POI → material mapping
- [ ] Identify BOM/nomenclature source
- [ ] Validate purchase-order relationships
- [ ] Build canonical dataset

## Phase 3 — Business Logic
- [ ] Component applicability
- [ ] Availability definition
- [ ] Missing-data behavior
- [ ] Theoretical-date rule
- [ ] Week convention
- [ ] Tie handling
- [ ] Blocking element

## Phase 4 — Simulator
- [ ] Pure functions
- [ ] Unit tests
- [ ] Batch processing
- [ ] Output schema
- [ ] Explainability

## Phase 5 — Interface
- [ ] Simple API/UI
- [ ] POI lookup
- [ ] Availability display
- [ ] SemTheorique display
- [ ] Blocking element
- [ ] Quality warnings

## Phase 6 — Performance
- [ ] Baseline benchmark
- [ ] Bottleneck profiling
- [ ] Optimization
- [ ] Re-benchmark

## Phase 7 — Hadoop
- [ ] HDFS input
- [ ] Mapper
- [ ] Reducer
- [ ] Local correctness comparison
- [ ] Benchmark
- [ ] Overhead analysis

## Phase 8 — Finalization
- [ ] Clean repository
- [ ] Reproducible instructions
- [ ] Technical documentation
- [ ] Benchmark report
- [ ] Internship report
- [ ] Limitations/future work
