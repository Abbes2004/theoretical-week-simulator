# Hadoop MapReduce Plan

## Objective
Prototype distributed processing for the expensive part of the theoretical-week pipeline and compare it with the local implementation.

## Prerequisites
Before Hadoop:
- validated business calculation;
- working local baseline;
- benchmark baseline;
- identified bottleneck.

## Conceptual Flow

```text
Canonical POI Data
      |
     HDFS
      |
     Map
      |
Shuffle / Group
      |
    Reduce
      |
Theoretical Date / Week / Blocking Element
```

## Mapper
Emit a key representing the POI:

`(Id_Sim, POI_Sim)`

and the component information needed by the calculation.

## Reducer
For each POI:
1. collect component values;
2. determine applicability;
3. detect incomplete required components;
4. compute maximum applicable date;
5. derive theoretical week;
6. identify blocking component(s);
7. emit the result.

## Correctness
Hadoop output must be compared with the local baseline on exactly the same canonical input.

Expected:

`HadoopResult == LocalResult`

for all comparable records.

## HDFS
HDFS can be used for distributed storage where useful. Its use alone does not prove performance improvement.

## Important Warning
Do not distribute a trivial `MAX()` operation merely for demonstration. If the real bottleneck is preparation or joining, the distributed design should address that bottleneck.

## Deliverables
- HDFS input preparation
- mapper
- reducer
- execution script
- output
- correctness comparison
- benchmark
- overhead/limitation analysis
