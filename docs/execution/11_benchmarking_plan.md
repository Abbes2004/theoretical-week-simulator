# Benchmarking Plan

## Objective
Measure whether optimization and distributed processing improve simulator execution.

## Versions
1. Local baseline
2. Local optimized
3. Hadoop MapReduce prototype

All must implement the same logical calculation.

## Metrics
- total execution time
- input size
- number of POIs
- throughput (POIs/second)
- peak memory where practical
- preprocessing time
- computation time
- output-writing time
- Hadoop startup/overhead

## Experimental Rules
- Same dataset for comparable runs.
- Document hardware/software environment.
- Separate warm-up from measured runs when relevant.
- Use multiple repetitions.
- Report median and variability.
- Keep workloads logically equivalent.

## Scaling
Use small, medium, large, and stress datasets. Synthetic expansion is allowed when real data is insufficient, but must be explicitly labelled.

## Bottleneck
Profile the local baseline before deciding what to distribute.

Potential bottlenecks:
- parsing
- joins
- aggregation
- quantity calculations
- date calculations
- serialization
- disk I/O

## Result Table

| Version | Dataset | POIs | Time | Throughput | Memory | Notes |
|---|---|---:|---:|---:|---:|---|
| Local baseline | ... | ... | ... | ... | ... | ... |
| Local optimized | ... | ... | ... | ... | ... | ... |
| Hadoop | ... | ... | ... | ... | ... | ... |

## Interpretation
Hadoop is not considered successful merely because it runs. Correctness, reproducibility, and measurable performance characteristics are required.
