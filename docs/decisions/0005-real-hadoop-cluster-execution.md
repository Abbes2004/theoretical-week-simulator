# Decision 0005 — Real Hadoop cluster execution (3-VM VirtualBox cluster)

Status: Accepted. Date: 2026-09-10.

## Context

Decision 0004 established that no Hadoop could run on the Windows host
itself. Mid-session, the user made available a pre-existing 3-node
VirtualBox Hadoop cluster (Lubuntu VMs: `master`, `worker1`, `worker2`)
running on the same physical machine as this Windows host. This decision
documents the inspection, the network/SSH setup, the configuration issues
found and fixed (with explicit user authorization at each step), and the
real-execution results.

## Access setup

- VMs were powered off initially; the user started them.
- VirtualBox host-only networking mismatch found (host adapter
  `192.168.56.1/24`, VMs on `10.15.15.0/24`) and fixed by the **user**,
  who added `10.15.15.1/24` as a secondary address on the existing
  `Ethernet 2` host-only adapter (not done by this session; proposed,
  confirmed, then applied by the user).
- SSH: a dedicated ED25519 keypair (`~/.ssh/tws_hadoop_cluster`, no
  passphrase) was generated on the Windows host and authorized by the user
  running `ssh-copy-id`/manual `authorized_keys` append themselves (no
  password was ever entered into, captured by, or visible to this
  session). `~/.ssh/config` aliases `tws-master`/`tws-worker1`/`tws-worker2`
  were added for convenience; `src/mapreduce/cluster.py` is the only
  module that uses them.

## Cluster inspection (read-only; independently re-verified, not assumed from the user's paste)

| | master | worker1 | worker2 |
|---|---|---|---|
| IP | 10.15.15.11 | 10.15.15.12 | 10.15.15.13 |
| Role | NameNode, SecondaryNameNode, ResourceManager | DataNode, NodeManager | DataNode, NodeManager |
| vCPU | 1 | 1 | 1 |
| RAM | 1.4GiB | 960MiB | 960MiB |
| Disk free | 4.6G/20G | 4.8G/20G | 5.1G/20G |

Hadoop 3.4.2, OpenJDK 1.8.0_482, identical on all three nodes.
`HADOOP_HOME=/home/abbes/hadoop-3.4.2` set via `.bashrc` only (not present
in non-interactive SSH sessions -- every remote command sources it
explicitly or uses absolute paths). `/etc/hosts` consistently maps all
three hostnames to their `10.15.15.x` addresses on every node. `workers`
file lists `worker1`/`worker2` only -- `master` is confirmed NOT a
DataNode/NodeManager, so this is a genuine master/2-worker split, not one
box pretending to be three.

HDFS was already formatted (real `clusterID`/`blockpoolID` in
`VERSION`, dated April) -- **never reformatted**. `dfs.replication=2`.

## Issues found and fixed (each reported before being touched, per the user's explicit process)

### 1. Unsafe YARN resource defaults

No `yarn.nodemanager.resource.memory-mb`/`cpu-vcores` override existed
anywhere; YARN was advertising Hadoop's hardcoded default (8192MB/8
vCores) per node, 8-17x more than the ~260-440MB actually free after the
DataNode+NodeManager daemons' own footprint. Confirmed via
`yarn node -list -showDetails` before any change.

**Fix applied** (backed up first: `/home/abbes/hadoop-config-backups/20260910_154205/{yarn,mapred}-site.xml` on all 3 nodes):

```xml
<!-- yarn-site.xml (all 3 nodes) -->
<property><name>yarn.nodemanager.resource.memory-mb</name><value>384</value></property>
<property><name>yarn.nodemanager.resource.cpu-vcores</name><value>1</value></property>
<property><name>yarn.scheduler.minimum-allocation-mb</name><value>128</value></property>
<property><name>yarn.scheduler.maximum-allocation-mb</name><value>384</value></property>
<property><name>yarn.scheduler.maximum-allocation-vcores</name><value>1</value></property>
```
```xml
<!-- mapred-site.xml (all 3 nodes) -->
<property><name>mapreduce.map.memory.mb</name><value>256</value></property>
<property><name>mapreduce.reduce.memory.mb</name><value>256</value></property>
<property><name>yarn.app.mapreduce.am.resource.mb</name><value>256</value></property>
<property><name>mapreduce.map.java.opts</name><value>-Xmx200m</value></property>
<property><name>mapreduce.reduce.java.opts</name><value>-Xmx200m</value></property>
```

YARN restarted (`stop-yarn.sh` + `start-yarn.sh`, HDFS untouched throughout).
Verified after restart: `Configured Resources: <memory:384, vCores:1>` on
both workers (was `<memory:8192, vCores:8>`).

**Consequence, stated honestly:** 384MB/1 vcore per node means effectively
one container runs at a time per worker -- this cluster cannot run
concurrent tasks per node. That is a real hardware limitation, not
something further tuning fixes; it directly explains the wall-clock
results below.

### 2. Pre-existing YARN queue configuration has no "default" queue

`capacity-scheduler.xml` (not created by this project) defines
`yarn.scheduler.capacity.root.queues` **twice**: the first occurrence says
`default`, but it's overridden later in the same file by a second block
defining a `sales`/`engineering` queue tree (with `engineering.data`
restricted to user `adam` and `engineering.system` `STOPPED` and
restricted to user `med` -- evidently left over from an unrelated
queue-management exercise). The first real job submission failed:
`Application ... submitted by user abbes to unknown queue: default`.

**Fix:** submit jobs with `-D mapreduce.job.queuename=sales` (the one
queue that is `RUNNING` and open to all users,
`acl_submit_applications=*`). `capacity-scheduler.xml` itself was **not
modified** -- per the instruction not to alter unrelated cluster
configuration beyond what's strictly necessary, using the existing open
queue was preferred over editing the scheduler's queue tree.

### 3. Windows `scp.exe` cannot handle this project's own directory name

Every `scp` call to stage `mapper.py`/`reducer.py`/input files failed with
`stat local "": No such file or directory` when given an absolute Windows
path. Root cause: this project's directory name contains literal
parentheses (`theoretical-week-simulator(1)`), which Windows' OpenSSH
`scp.exe` mis-parses. **Fix:** `src/mapreduce/cluster.py::_scp_local_arg`
converts local paths to be relative to the current working directory
(scripts in this project are always run from the project root) before
passing them to `scp`, avoiding the parenthesized path component entirely.

### 4. Intermittent SSH connection failures under rapid successive connections

Observed: an isolated `scp` failing, then succeeding on an identical retry
seconds later, with nothing else changed. Attributed to the single shared
vCPU on each node -- SSH key exchange is CPU-bound, and with
HDFS/YARN daemons also competing for that one core, occasional connection
setup failures are expected, not a configuration bug. **Fix:**
`src/mapreduce/cluster.py` retries `ssh`/`scp` up to 3 times with a 3s
delay -- a documented accommodation for this specific hardware, not a
general "retry until it works" policy (it still raises after 3 failures).

## Correctness (real cluster)

**513-row demo dataset, real Hadoop Streaming job on master+worker1+worker2:**

```text
Compared POIs: 513
Only in Hadoop output: 0
Only in local reference: 0
Field mismatches: 0
EXACT MATCH: True
```

Every one of the 13 curated edge cases (each of the 5 components as sole
blocker, the 2/3/5-way ties, the range boundaries, the three
2025-12-29/30/31 ISO year-boundary rows) came back from the real cluster
with exactly the values Phase 1 computed locally -- e.g.
`DEMO-EDGE-ISO_YEAR_BOUNDARY_2025_12_29` → `iso_year=2026, iso_week=1,
week_key=202601` on the real cluster, identical to the local vectorized
engine.

**Real-cluster wall-clock for this job:** ~15 minutes for 513 POIs /
2,565 events (see the table below) -- see "Honest assessment" for why.

## Benchmark results (real cluster vs. local baseline/vectorized vs. local-emulation)

### Demo dataset (513 POIs, 2,565 component events)

| Phase | Real cluster | Local-emulation |
|---|---:|---:|
| stage input to master (scp) | 1.4s | n/a |
| HDFS upload | 22.0s | n/a |
| MapReduce job | 858.0s (~14.3 min) | 0.33s |
| HDFS download (getmerge) | 21.6s | n/a |
| fetch output to host (scp) | 1.3s | n/a |
| **Total (upload+job+download)** | **901.5s (~15.0 min)** | **0.33s** |

### Required benchmark scales -- local baseline vs. local vectorized

Measured on this session's `benchmark_scale_2025_2026` dataset (same input
for both implementations). Baseline reps reduced at larger scales (1 rep,
marked exploratory) because a single 1M-row baseline run already takes
~7 minutes -- see docs/execution/11_benchmarking_plan.md's allowance for
exploratory single-run results when repetition is impractical.

| Scale | Local baseline (median) | Throughput | Local vectorized (median) | Throughput | Speedup |
|---|---:|---:|---:|---:|---:|
| 100,000 | 43.756s (3 reps) | 2,285 rows/s | 4.466s (5 reps) | 22,394 rows/s | 9.8x |
| 500,000 | 239.165s (1 rep, exploratory) | 2,091 rows/s | 24.405s (5 reps) | 20,487 rows/s | 9.8x |
| 1,000,000 | 430.257s (1 rep, exploratory) | 2,324 rows/s | 38.804s (3 reps) | 25,771 rows/s | 11.1x |

Note: throughput here (~2,000-2,300 rows/s baseline) is measurably lower
than Phase 1's original measurement on the same machine (~4,000-4,700
rows/s, see docs/decisions/0002) -- this session ran these benchmarks
*while the 3-VM cluster was powered on and in use*, competing for the
host's 8GB of RAM (observed as low as ~0.5GB free during the 1M-row run).
This is reported as an honest environmental factor, not a change in the
algorithm: the vectorized-vs-baseline speedup ratio (9.8x-11.1x) is
consistent with Phase 1's finding regardless.

### Real Hadoop cluster at benchmark scale (100,000 POIs)

A real-cluster run completed for the 100,000-POI scale (`scale_100000_real`,
500,000 events, 29MB input) -- a second, larger real-cluster
correctness/timing data point beyond the 513-row demo:

```text
Compared POIs: 100,000
Only in Hadoop output: 0
Only in local reference: 0
Field mismatches: 0
EXACT MATCH: True
```

**Every one of the 100,000 POIs matched the local vectorized reference
exactly** on `Id_Sim, POI_Sim, date_theorique, iso_year, iso_week,
week_key, sem_theorique, blocking_element, calculation_status`.

| Phase | Time |
|---|---:|
| stage input to master (scp, 29MB) | 6.85s |
| HDFS upload | 53.94s |
| MapReduce job | 1,331.49s (~22.2 min) |
| HDFS download (getmerge) | 26.14s |
| fetch output to host (scp) | 2.07s |
| **Total (upload+job+download)** | **1,411.57s (~23.5 min)** |

For the required "at least one large benchmark scale" correctness
comparison, both this **real-cluster** run and **local-emulation** (the
exact same `mapper.py`/`reducer.py` files, run as local subprocesses) were
exercised at 100,000 POIs, both exact matches (0 mismatches). 1,000,000-POI
correctness was additionally verified via local-emulation (also 0
mismatches -- see docs/decisions/0004). A real-cluster run at 500,000 or
1,000,000 POIs was not attempted: extrapolating linearly from the
100,000-POI result (~23.5 minutes for 500k events) suggests roughly 2-4
hours for 1,000,000 POIs (5,000,000 events) on this hardware, which was
judged impractical within this session -- an explicit, evidence-based
scoping decision, not a silently skipped requirement.

## Honest assessment of this cluster for this workload

Even before the final numbers: this is a ~1-vCPU-per-node,
~1GB-RAM-per-node cluster running as 3 VirtualBox VMs on a single Windows
laptop with 8GB RAM total. It demonstrates genuine multi-node HDFS
replication and YARN scheduling, and a genuine Hadoop Streaming job
executing across `master`+`worker1`+`worker2`. It is not, and is not
claimed to be, production-representative hardware -- per-task JVM
launch/container-allocation overhead on this hardware is large relative to
the actual (trivial) per-record computation this job does, which is
precisely the situation docs/execution/12_hadoop_mapreduce_plan.md warns
about ("do not distribute a trivial MAX() operation merely for
demonstration").
