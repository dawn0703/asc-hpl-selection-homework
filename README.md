# ASC Selection Homework — HPL Performance Optimization

> ASC homework submission information and reproduction entry:
> [`SUBMISSION.md`](SUBMISSION.md)

This repository documents the complete HPL performance-optimization
workflow for the ASC selection homework, including environment setup,
baseline benchmarking, parameter tuning, correctness validation,
repeated measurements, performance-variability analysis, empirical
DGEMM comparison, and reproducible experiment artifacts.

The experiments use the official Netlib HPL 2.3 release. The upstream
HPL computational source code was not modified. Optimization focused on:

- MPI and OpenBLAS build/runtime configuration;
- `HPL.dat` parameter tuning;
- MPI rank placement and CPU affinity;
- BLAS/OpenMP thread configuration;
- correctness and repeated validation;
- performance-variability analysis;
- reproducible logs, structured results, and automated visualization.

See [`SOURCE.md`](SOURCE.md) for upstream source information and the
scope of local modifications.

---

## 1. Main Result

The primary validated optimization in this study compares two block sizes under the same workload:

- `N = 18432`
- `P × Q = 2 × 2`
- `4 MPI ranks`
- `1 OpenBLAS thread per rank`
- `NB = 128` versus `NB = 192`

Three fixed-N paired validation runs were performed:

| Pair | NB=128 (GFLOPS) | NB=192 (GFLOPS) | Relative Change |
|---|---:|---:|---:|
| 1 | 76.029 | 82.429 | +8.42% |
| 2 | 84.164 | 79.708 | -5.29% |
| 3 | 74.418 | 84.430 | +13.45% |
| **Mean** | **78.204** | **82.189** | **+5.10%** |

The repeated mean performance of `NB=192` is therefore **5.10% higher** than that of `NB=128` under the same problem size, process grid, MPI configuration, and BLAS threading configuration.

The highest single HPL performance observed in the retained experiments was:

**84.430 GFLOPS**

![Fixed-N paired validation](figures/fig2_fixedN_nb_validation.png)

`NB=192` outperformed `NB=128` in two of the three paired runs. Because the platform showed measurable run-to-run variation, the main conclusion is based on repeated measurements and their mean rather than on a cherry-picked single-run peak.

The primary validated conclusion is therefore:

> Under the fixed workload `N=18432`, `P×Q=2×2`, four MPI ranks, and one OpenBLAS thread per rank, changing `NB` from 128 to 192 increased the repeated mean HPL performance from **78.204 GFLOPS** to **82.189 GFLOPS**, corresponding to a **5.10% mean improvement**.

---

## 2. Hardware and Software Environment

### 2.1 Hardware

- CPU: Intel Core i7-10510U
- Physical cores: 4
- Logical CPUs: 8
- Threads per core: 2
- SIMD support: AVX2
- FMA support: yes
- L3 cache: 8 MiB
- Host memory: approximately 16 GB
- WSL2 memory available to the Linux guest: approximately 7.7 GiB

The processor exposes eight logical CPUs through SMT, but all formal HPL runs use only the four physical cores.

### 2.2 Software

- Host OS: Windows 11
- Linux environment: WSL2 Ubuntu 26.04 LTS
- HPL: Netlib HPL 2.3
- GCC: 15.2.0
- GFortran: 15.2.0
- Open MPI: 5.0.10
- OpenBLAS: 0.3.32 pthread

Detailed environment records are stored in:

- [`results/system_info.txt`](results/system_info.txt)
- [`results/software_info.txt`](results/software_info.txt)
- [`results/linked_libraries.txt`](results/linked_libraries.txt)
- [`results/thread_env.txt`](results/thread_env.txt)
- [`results/mpi_binding.txt`](results/mpi_binding.txt)

### 2.3 Process and Thread Model

Formal runs use:

```text
4 MPI ranks
×
1 OpenBLAS thread per rank
=
4 primary computational execution streams
```

This mapping was chosen because the CPU contains four physical cores.

Using eight MPI ranks or allowing every MPI rank to create multiple BLAS threads would risk oversubscribing the four physical cores and introducing additional scheduling overhead.

The MPI binding record confirms that the four ranks were bound to four physical cores.

---

## 3. HPL Algorithm and Tuning Strategy

HPL solves a dense linear system:

```text
A x = b
```

using LU factorization with partial pivoting and distributes the matrix across a two-dimensional `P × Q` MPI process grid using a block-cyclic distribution.

At a high level, the computation repeatedly performs:

1. panel factorization;
2. pivot handling and row exchange;
3. panel broadcast;
4. trailing-matrix update;
5. transition to the next panel;
6. final triangular solve.

The trailing-matrix update contains a large amount of BLAS Level-3 work, especially DGEMM. Therefore, HPL performance depends not only on raw floating-point throughput, but also on blocking, cache behavior, process-grid layout, communication, synchronization, and the balance between panel work and trailing updates.

### 3.1 Tuning Parameters

The main parameters investigated in this study are:

| Parameter | Meaning | Main Performance Concern |
|---|---|---|
| `N` | Matrix order / problem size | Memory usage, arithmetic intensity, BLAS-3 fraction |
| `NB` | Algorithmic block size | Blocking, cache behavior, BLAS efficiency, panel overhead |
| `P × Q` | MPI process grid | Data distribution and communication pattern |
| `BCAST` | Panel broadcast algorithm | Communication behavior |
| `DEPTH` | Look-ahead depth | Critical-path overlap between communication/panel work and updates |

Other HPL algorithmic settings were held fixed while the selected parameters were investigated.

### 3.2 Experimental Methodology

The tuning process follows a coarse-to-fine workflow:

```text
Correctness smoke test
        ↓
Baseline
        ↓
Coarse parameter search
        ↓
Candidate selection
        ↓
Controlled comparison
        ↓
Independent confirmation
        ↓
Repeated paired validation
        ↓
Algorithm-level exploratory tuning
        ↓
Stop when additional search is no longer justified
```

For the main optimization claim, the experiment changes only one primary parameter while keeping the workload and runtime configuration fixed.

The experimental design also distinguishes three levels of evidence:

- **validated result** — supported by repeated controlled measurements;
- **exploratory result** — useful observation, but without sufficient repetition for a stable claim;
- **highest observed result** — the best individual measurement, reported separately from the validated result.

This distinction is important because absolute GFLOPS varied noticeably between different time windows on the WSL2 laptop platform.

---

## 4. Build

The experiments use the official Netlib HPL 2.3 release:

<https://www.netlib.org/benchmark/hpl/>

The upstream HPL computational source code was not modified.

The local build configuration is stored in:

[`build/Make.WSL`](build/Make.WSL)

The configuration uses:

- Open MPI through `/usr/bin/mpicc`;
- OpenBLAS through the system OpenBLAS installation;
- CBLAS interface support through `HPL_CALL_CBLAS`;
- compiler optimization flags including `-O3` and `-march=native`.

The original tested `Make.WSL` contains the absolute `TOPdir` from the experiment machine. A reproducing user should update it to the location of their own HPL 2.3 checkout.

For example:

```bash
export HPL_ROOT=/path/to/hpl-2.3
cp build/Make.WSL "$HPL_ROOT/Make.WSL"

sed -i "s|^TOPdir[[:space:]]*=.*|TOPdir       = $HPL_ROOT|" \
  "$HPL_ROOT/Make.WSL"
```

Then build HPL with:

```bash
cd "$HPL_ROOT"
make arch=WSL
```

### 4.1 Parallel-Build Issue

An early attempt used:

```bash
make arch=WSL -j4
```

The legacy HPL build system produced missing-directory/copy errors during parallel initialization.

The final tested build therefore uses:

```bash
make arch=WSL
```

The serial build completed successfully.

This was treated as a build-system race rather than as an HPL numerical or MPI runtime failure.

### 4.2 Linked Libraries

The generated `xhpl` executable was verified to link against the expected MPI and OpenBLAS libraries.

The recorded linkage information is available in:

[`results/linked_libraries.txt`](results/linked_libraries.txt)

---

## 5. Runtime Configuration

All formal HPL experiments use:

```bash
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
```

The standard MPI launch command is:

```bash
mpirun -np 4 \
  --map-by core \
  --bind-to core \
  --mca btl self,sm \
  ./xhpl
```

### 5.1 Rationale

`-np 4`

: Uses one MPI rank per physical CPU core.

`--map-by core`

: Maps ranks by CPU core.

`--bind-to core`

: Pins each MPI rank to a core, reducing migration and improving experimental control.

`OMP_NUM_THREADS=1`

: Prevents unintended OpenMP parallelism.

`OPENBLAS_NUM_THREADS=1`

: Prevents each MPI process from independently creating several BLAS threads.

`--mca btl self,sm`

: Restricts Open MPI communication to self/shared-memory transports, which is appropriate because all MPI ranks run inside the same WSL2 virtual machine.

Actual rank bindings were recorded using Open MPI's binding-report functionality and are preserved in:

[`results/mpi_binding.txt`](results/mpi_binding.txt)

---

## 6. Baseline

The formal baseline configuration is:

```text
N  = 18432
NB = 128
P  = 2
Q  = 2
```

Configuration file:

[`configs/HPL_baseline.dat`](configs/HPL_baseline.dat)

The first formal baseline run produced:

```text
Time        : 57.87 s
Performance : 72.149 GFLOPS
Correctness : PASSED
```

The baseline establishes the initial reference point for tuning.

Because later experiments demonstrated significant run-to-run performance variation, this single baseline measurement is not treated as the machine's fixed or deterministic performance level.

The raw output is preserved in:

[`logs/baseline.log`](logs/baseline.log)

---

## 7. Block Size (`NB`) Tuning

`NB` controls the algorithmic block size used by HPL.

A very small block size may increase panel-related overhead and reduce BLAS Level-3 efficiency. A very large block size may reduce available parallelism and interact poorly with cache behavior and panel factorization.

Therefore, the first tuning stage used a coarse sweep.

### 7.1 Coarse Sweep

Fixed parameters:

```text
N     = 18432
P × Q = 2 × 2
np    = 4
```

Results:

| NB | Time (s) | Performance (GFLOPS) | Correctness |
|---:|---:|---:|---|
| 128 | 62.61 | 66.684 | PASSED |
| 192 | 62.08 | 67.255 | PASSED |
| 256 | 67.21 | 62.119 | PASSED |

![NB coarse sweep](figures/fig1_nb_coarse_sweep.png)

`NB=256` was clearly slower in this session.

The difference between `NB=128` and `NB=192`, however, was small enough that the coarse sweep alone was not considered sufficient evidence.

### 7.2 Independent Confirmation

The two strongest candidates were tested again after a cooldown period.

The confirmation measurements were:

```text
NB=128 : 70.404 GFLOPS
NB=192 : 72.610 GFLOPS
```

Both runs passed the HPL correctness check.

These results supported `NB=192` as a candidate, but the platform variability observed during the study motivated a stronger repeated validation.

### 7.3 Fixed-N Paired Validation

The final validation kept the following fixed:

```text
N     = 18432
P × Q = 2 × 2
np    = 4
OMP_NUM_THREADS      = 1
OPENBLAS_NUM_THREADS = 1
```

Only `NB` changed.

Three paired comparisons were run:

| Pair | Order | NB=128 (GFLOPS) | NB=192 (GFLOPS) |
|---|---|---:|---:|
| 1 | 128 → 192 | 76.029 | 82.429 |
| 2 | 128 → 192 | 84.164 | 79.708 |
| 3 | 192 → 128 | 74.418 | 84.430 |

The third pair reversed the execution order to reduce the risk that a simple first-run/second-run ordering effect determined the result.

Summary statistics:

```text
NB=128
Mean   : 78.204 GFLOPS
Median : 76.029 GFLOPS
CV     : 6.68%

NB=192
Mean   : 82.189 GFLOPS
Median : 82.429 GFLOPS
CV     : 2.88%
```

Mean improvement:

```text
82.189 / 78.204 - 1
≈ 5.10%
```

Pairwise changes:

```text
Pair 1 : +8.42%
Pair 2 : -5.29%
Pair 3 : +13.45%
```

`NB=192` won two of the three paired comparisons.

The validated conclusion is therefore not that `NB=192` must win every individual run. Instead, the evidence supports that `NB=192` achieved a higher repeated mean performance under the tested fixed workload.

Raw structured data:

[`results/fixedN_validation.csv`](results/fixedN_validation.csv)

---

## 8. MPI Process Grid

HPL distributes the matrix over a two-dimensional MPI process grid.

With four MPI ranks, two relevant layouts are:

```text
1 × 4
2 × 2
```

The experiment fixed:

```text
N  = 18432
NB = 192
np = 4
```

Results:

| P × Q | Time (s) | Performance (GFLOPS) | Correctness |
|---|---:|---:|---|
| 1 × 4 | 60.01 | 69.575 | PASSED |
| 2 × 2 | 57.50 | 72.610 | PASSED |

![MPI process-grid comparison](figures/fig3_process_grid.png)

Within this comparison session, the more balanced `2 × 2` process grid achieved approximately 4.36% higher throughput than `1 × 4`.

This is consistent with the general expectation that a more balanced two-dimensional decomposition can reduce unfavorable communication geometry for dense linear algebra.

However, this result is interpreted specifically for:

```text
4 MPI ranks
+
this HPL workload
+
this machine
```

and is not claimed to prove that `2 × 2` is universally optimal for all HPL systems or process counts.

The later experiments therefore retain:

```text
P × Q = 2 × 2
```

---

## 9. Problem-Size Sensitivity

After selecting `NB=192` and `P×Q=2×2`, the effect of the problem size was explored.

Fixed parameters:

```text
NB    = 192
P × Q = 2 × 2
np    = 4
```

Results:

| N | Performance (GFLOPS) | Correctness |
|---:|---:|---|
| 15360 | 68.417 | PASSED |
| 18432 | 72.610 | PASSED |
| 23040 | 73.850 | PASSED |

![Problem-size sensitivity](figures/fig4_problem_size.png)

The largest tested case, `N=23040`, achieved the highest throughput in this sweep:

```text
73.850 GFLOPS
```

### 9.1 Memory Consideration

The dense matrix alone requires approximately:

```text
8 × N² bytes
```

For `N=23040`:

```text
8 × 23040²
≈ 3.96 GiB
```

The run completed without using swap.

A larger problem can improve HPL throughput because fixed overhead and communication can be amortized over more floating-point work, while a larger fraction of execution may occur in efficient BLAS Level-3 kernels.

However, increasing `N` also increases memory pressure and total computational work.

### 9.2 Interpretation

Changing `N` changes the workload itself.

Therefore, this experiment is reported as:

**problem-size sensitivity**

rather than:

**same-workload speedup**

The `N=23040` result is useful for understanding throughput behavior, but it is not used as the main optimization comparison because it does not represent the same computational problem as the baseline.

---

## 10. BCAST × DEPTH Algorithm-Level Exploration

After the primary `NB` optimization had been validated, a small `2 × 2` factorial experiment was used to explore algorithm-level interaction between panel broadcast and look-ahead depth.

Tested values:

```text
BCAST ∈ {1, 3}
DEPTH ∈ {0, 1}
```

Fixed parameters:

```text
N     = 18432
NB    = 192
P × Q = 2 × 2
np    = 4
```

Results:

| BCAST | DEPTH | Performance (GFLOPS) | Correctness |
|---:|---:|---:|---|
| 1 | 0 | 60.255 | PASSED |
| 1 | 1 | 64.775 | PASSED |
| 3 | 0 | 55.743 | PASSED |
| 3 | 1 | 67.005 | PASSED |

![BCAST and DEPTH interaction](figures/fig5_bcast_depth_interaction.png)

Within this mini-sweep session, the best observed combination was:

```text
BCAST = 3
DEPTH = 1
```

with:

```text
67.005 GFLOPS
```

Compared with:

```text
BCAST = 1
DEPTH = 0
60.255 GFLOPS
```

the session-local improvement was:

```text
67.005 / 60.255 - 1
≈ 11.20%
```

### 10.1 Interaction

The effect of `BCAST` depends on the value of `DEPTH`.

At `BCAST=1`:

```text
DEPTH 0 → 1
60.255 → 64.775 GFLOPS
≈ +7.50%
```

At `BCAST=3`:

```text
DEPTH 0 → 1
55.743 → 67.005 GFLOPS
≈ +20.20%
```

Similarly, the effect of changing `BCAST` differs between `DEPTH=0` and `DEPTH=1`.

This is evidence of a parameter interaction: the effect of one tuning parameter cannot be fully described independently of the other.

### 10.2 Evidence Level

Each factorial cell was measured only once.

Because the platform had already demonstrated substantial run-to-run variation, the `BCAST × DEPTH` result is classified as:

**exploratory algorithm-level evidence**

rather than:

**validated stable speedup**

The main validated configuration therefore remains based on the repeated fixed-N `NB` experiment:

```text
N     = 18432
NB    = 192
P × Q = 2 × 2
BCAST = 1
DEPTH = 0
```

The advanced mini-sweep is retained because it demonstrates additional algorithmic analysis and exposes an interaction that could be investigated further on a more stable benchmarking platform.

---

## 11. Correctness Validation

Performance optimization is only meaningful if the numerical result remains correct.

All retained formal HPL runs passed the HPL residual test:

```text
PASSED
```

HPL evaluates a scaled residual of the form:

```text
||Ax - b||∞
-----------------------------------------------
eps × (||A||∞ × ||x||∞ + ||b||∞) × N
```

Typical scaled residuals observed during the experiments were on the order of:

```text
10^-3
```

For example, the repeated `NB=192` runs produced residual values around:

```text
2.209 × 10^-3
```

and passed the configured HPL correctness criterion.

Correctness was checked after parameter changes instead of assuming that a faster run remained numerically valid.

Raw HPL output files are preserved under:

[`logs/`](logs/)

including baseline, parameter sweeps, confirmations, repeated validation, and the advanced mini-sweep.

---

## 12. Performance Variability and Experimental Control

A major practical observation during this study was that absolute HPL performance was not perfectly stable across different time windows.

A sustained-load validation alternated the original baseline configuration and a larger candidate configuration.

The absolute GFLOPS values changed noticeably during the sequence.

The repeated baseline values in that sustained experiment had a coefficient of variation of approximately:

```text
11%
```

The larger configuration showed a similar level of variability.

Structured results are stored in:

[`results/final_validation.csv`](results/final_validation.csv)

### 12.1 Possible Sources

Possible contributors include:

- CPU dynamic frequency;
- processor power limits;
- thermal state;
- Windows host scheduling;
- WSL2 scheduling and virtualization effects;
- background host activity.

No direct frequency, power, or temperature telemetry was collected during the benchmark runs.

Therefore, this study does **not** claim that the observed variability was uniquely caused by thermal throttling or any other single mechanism.

### 12.2 Methodological Response

The experimental workflow was strengthened progressively:

```text
single observation
        ↓
independent confirmation
        ↓
cooldown between runs
        ↓
fixed-workload comparison
        ↓
paired measurements
        ↓
repeated pairs
        ↓
reversed execution order
        ↓
mean / median / coefficient of variation
```

This is why the final optimization claim is based on the fixed-N repeated paired experiment rather than on the highest individual GFLOPS value.

Comparisons between measurements from different sessions are treated cautiously.

Where possible, conclusions are based on measurements collected:

```text
under the same workload
+
with the same runtime configuration
+
within a controlled experiment
```

---

## 13. Nominal Rpeak and DGEMM Reference

To place the HPL results in context, two performance references were considered:

1. a nominal base-frequency FP64 Rpeak estimate;
2. an empirical OpenBLAS DGEMM throughput reference.

These references answer different questions and should not be confused.

### 13.1 Nominal Base-Frequency FP64 Rpeak

The Intel Core i7-10510U supports AVX2 and FMA.

A 256-bit AVX2 vector contains:

```text
4 FP64 values
```

An FMA performs one multiplication and one addition per element:

```text
2 FLOPs per element
```

Assuming two 256-bit FMA execution units per physical core:

```text
4 FP64 values
× 2 FLOPs/FMA
× 2 vector FMA units
=
16 FP64 FLOP/cycle/core
```

Using four physical cores and the nominal 1.80 GHz base frequency:

```text
4 cores
× 1.80 GHz
× 16 FLOP/cycle/core
=
115.2 GFLOPS
```

Thus the nominal base-frequency reference is:

**115.2 GFLOPS**

The validated HPL mean is:

```text
82.189 GFLOPS
```

Therefore:

```text
82.189 / 115.2
≈ 71.3%
```

The validated HPL mean corresponds to approximately:

**71.3% of nominal base-frequency Rpeak**

This `115.2 GFLOPS` value is a nominal reference, not a strict sustained physical ceiling.

The processor can operate at dynamic frequencies above or below the nominal base-frequency assumption depending on workload, power, and thermal conditions.

### 13.2 Empirical MPI + OpenBLAS DGEMM Reference

Because HPL spends a large fraction of its time in BLAS Level-3 operations, an additional MPI + CBLAS DGEMM microbenchmark was implemented.

The microbenchmark uses a runtime structure similar to HPL:

```text
4 MPI ranks
1 OpenBLAS thread per rank
core binding
```

Source:

[`analysis/dgemm/mpi_dgemm_ceiling.c`](analysis/dgemm/mpi_dgemm_ceiling.c)

A size sweep produced:

| Local DGEMM Size | Repetitions | Performance (GFLOPS) |
|---:|---:|---:|
| 2048 | 5 | 85.583 |
| 3072 | 3 | 82.082 |
| 4096 | 2 | **86.478** |

The best observed DGEMM result was:

**86.478 GFLOPS**

Comparing the validated HPL mean with this empirical observation:

```text
82.189 / 86.478
≈ 95.0%
```

Therefore, the validated HPL mean is approximately:

**95.0% of the best observed DGEMM throughput**

### 13.3 Why DGEMM Is Not Treated as a Strict Ceiling

A later three-run repetition of the `N=4096` DGEMM test produced:

```text
79.418 GFLOPS
78.870 GFLOPS
79.475 GFLOPS
```

with:

```text
Mean   ≈ 79.254 GFLOPS
Median ≈ 79.418 GFLOPS
CV     ≈ 0.42%
```

This repetition was internally stable, but its absolute throughput was below several HPL measurements from other time windows.

Therefore, the best observed `86.478 GFLOPS` DGEMM result is reported only as an:

**empirical performance reference**

and not as a theoretical or physical upper bound.

DGEMM data and analysis are stored in:

[`analysis/dgemm/`](analysis/dgemm/)

---

## 14. Final Results

The main results are summarized below.

| Metric | Result | Evidence Level |
|---|---:|---|
| Initial formal baseline | 72.149 GFLOPS | Single baseline |
| Fixed-N `NB=128` mean | 78.204 GFLOPS | Repeated |
| Fixed-N `NB=192` mean | **82.189 GFLOPS** | Repeated |
| Validated mean improvement | **+5.10%** | **Validated** |
| Highest single HPL observation | **84.430 GFLOPS** | Observed peak |
| `N=23040` problem-size result | 73.850 GFLOPS | Sensitivity study |
| Best BCAST × DEPTH cell | 67.005 GFLOPS | Exploratory |
| B3D1 vs B1D0 session-local change | **+11.20%** | Exploratory |
| Nominal base-frequency Rpeak | 115.2 GFLOPS | Analytical reference |
| Validated HPL / nominal Rpeak | **71.3%** | Derived |
| Best observed DGEMM | 86.478 GFLOPS | Empirical reference |
| Validated HPL / best observed DGEMM | **95.0%** | Empirical comparison |

The key result used as the final optimization claim is:

```text
Same workload:
N = 18432
P × Q = 2 × 2
4 MPI ranks
1 OpenBLAS thread/rank

NB=128 mean = 78.204 GFLOPS
NB=192 mean = 82.189 GFLOPS

Mean improvement = 5.10%
```

The highest single HPL observation, `84.430 GFLOPS`, is reported separately and is not substituted for the repeated mean.

Likewise, the `BCAST=3, DEPTH=1` result is retained as exploratory evidence rather than being promoted to the final validated optimization.

Machine-readable summary statistics are stored in:

[`results/final_statistics.csv`](results/final_statistics.csv)

A concise analysis summary is stored in:

[`results/hpl_analysis_summary.txt`](results/hpl_analysis_summary.txt)

---

## 15. Reproducing an HPL Run

The commands below describe the reproduction workflow used by this repository.

### 15.1 Clone This Repository

```bash
git clone https://github.com/dawn0703/asc-hpl-selection-homework.git
cd asc-hpl-selection-homework

export REPO_ROOT="$(pwd)"
```

### 15.2 Obtain Netlib HPL 2.3

Download HPL 2.3 from:

<https://www.netlib.org/benchmark/hpl/>

After extracting it, define:

```bash
export HPL_ROOT=/path/to/hpl-2.3
```

### 15.3 Apply the Tested Build Configuration

Copy the tested configuration:

```bash
cp "$REPO_ROOT/build/Make.WSL" \
   "$HPL_ROOT/Make.WSL"
```

Update `TOPdir` for the local checkout:

```bash
sed -i "s|^TOPdir[[:space:]]*=.*|TOPdir       = $HPL_ROOT|" \
  "$HPL_ROOT/Make.WSL"
```

The tested `Make.WSL` assumes the Ubuntu OpenBLAS installation layout recorded in this repository. Library/include paths may need adjustment if OpenBLAS is installed elsewhere.

Build:

```bash
cd "$HPL_ROOT"
make arch=WSL
```

Expected executable:

```text
$HPL_ROOT/bin/WSL/xhpl
```

### 15.4 Set Runtime Threading

```bash
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
```

### 15.5 Reproduce the Baseline

```bash
cp "$REPO_ROOT/configs/HPL_baseline.dat" \
   "$HPL_ROOT/bin/WSL/HPL.dat"

cd "$HPL_ROOT/bin/WSL"

mpirun -np 4 \
  --map-by core \
  --bind-to core \
  --mca btl self,sm \
  ./xhpl
```

Baseline parameters:

```text
N  = 18432
NB = 128
P  = 2
Q  = 2
```

### 15.6 Reproduce the Validated `NB=192` Candidate

```bash
cp "$REPO_ROOT/configs/HPL_nb192_confirm.dat" \
   "$HPL_ROOT/bin/WSL/HPL.dat"

cd "$HPL_ROOT/bin/WSL"

mpirun -np 4 \
  --map-by core \
  --bind-to core \
  --mca btl self,sm \
  ./xhpl
```

Main parameters:

```text
N  = 18432
NB = 192
P  = 2
Q  = 2
```

Because HPL performance depends on hardware, operating-system state, CPU frequency behavior, and library versions, an independent reproduction should not be expected to produce identical absolute GFLOPS.

The relevant reproducibility targets are:

- the configuration;
- the experimental method;
- correctness;
- the direction and interpretation of observed performance effects.

---

## 16. Reproducing the Analysis and Figures

The figures and final statistics are generated from structured experimental CSV files rather than being manually entered.

### 16.1 Create a Python Environment

From the repository root:

```bash
python3 -m venv .venv-report
source .venv-report/bin/activate
```

Install the recorded analysis dependency:

```bash
python -m pip install -r analysis/requirements.txt
```

### 16.2 Regenerate Statistics and Figures

Run:

```bash
python analysis/make_figures.py
```

The script reads the structured experiment data and regenerates:

```text
results/final_statistics.csv

figures/fig1_nb_coarse_sweep.png
figures/fig2_fixedN_nb_validation.png
figures/fig3_process_grid.png
figures/fig4_problem_size.png
figures/fig5_bcast_depth_interaction.png
```

The analysis includes:

- repeated mean;
- median;
- coefficient of variation;
- paired fixed-N improvement;
- nominal Rpeak comparison;
- empirical DGEMM comparison;
- BCAST × DEPTH interaction metrics.

The intended data-provenance chain is:

```text
HPL configuration
        ↓
HPL execution
        ↓
raw log
        ↓
structured CSV
        ↓
automated statistics
        ↓
figure
        ↓
README / final-report conclusion
```

This structure reduces the risk of manually copying inconsistent numbers between raw benchmark output and the final report.

---

## 17. Repository Structure

```text
.
├── README.md
├── SUBMISSION.md
├── SOURCE.md
├── .gitignore
│
├── build/
│   └── Make.WSL
│
├── configs/
│   ├── HPL_original.dat
│   ├── HPL_smoke.dat
│   ├── HPL_baseline.dat
│   ├── HPL_nb_sweep.dat
│   ├── HPL_nb128_confirm.dat
│   ├── HPL_nb192_confirm.dat
│   ├── HPL_grid_1x4.dat
│   ├── HPL_n15360.dat
│   ├── HPL_n23040.dat
│   ├── HPL_bcast1_depth0.dat
│   ├── HPL_bcast1_depth1.dat
│   ├── HPL_bcast3_depth0.dat
│   └── HPL_bcast3_depth1.dat
│
├── scripts/
│   ├── run_fixedN_validation.sh
│   ├── run_final_validation.sh
│   └── run_bcast_depth_sweep.sh
│
├── results/
│   ├── results.csv
│   ├── fixedN_validation.csv
│   ├── final_validation.csv
│   ├── bcast_depth_sweep.csv
│   ├── final_statistics.csv
│   ├── hpl_analysis_summary.txt
│   ├── system_info.txt
│   ├── software_info.txt
│   ├── linked_libraries.txt
│   ├── thread_env.txt
│   └── mpi_binding.txt
│
├── logs/
│   └── raw HPL output logs
│
├── analysis/
│   ├── make_figures.py
│   ├── requirements.txt
│   └── dgemm/
│       ├── mpi_dgemm_ceiling.c
│       ├── dgemm_summary.csv
│       ├── dgemm_size_sweep.log
│       ├── dgemm_repeat.log
│       ├── performance_summary.txt
│       ├── cpu_peak_info.txt
│       └── run_dgemm_repeat.sh
│
└── figures/
    ├── README.txt
    ├── fig1_nb_coarse_sweep.png
    ├── fig2_fixedN_nb_validation.png
    ├── fig3_process_grid.png
    ├── fig4_problem_size.png
    └── fig5_bcast_depth_interaction.png
```

Generated binaries and HPL object files are intentionally not stored in this repository.

---

## 18. Troubleshooting and Lessons Learned

### 18.1 Correctness Comes Before Optimization

A small smoke test was used before larger benchmark experiments.

The smoke configuration confirmed that:

```text
HPL executable
+
MPI runtime
+
OpenBLAS linkage
+
HPL.dat
```

worked together and produced a `PASSED` result.

This prevented large tuning experiments from being built on an unverified runtime environment.

### 18.2 Old Build Systems Are Not Necessarily Parallel-Safe

The failed:

```bash
make arch=WSL -j4
```

attempt demonstrated that adding `-j` is not automatically safe for a legacy Makefile.

Serial compilation was retained because it was reproducible and successful.

### 18.3 MPI × BLAS Oversubscription Must Be Controlled

With four physical cores, a configuration such as:

```text
4 MPI ranks
×
multiple BLAS threads per rank
```

could create more runnable threads than available physical cores.

The final runtime explicitly sets:

```text
OMP_NUM_THREADS=1
OPENBLAS_NUM_THREADS=1
```

and binds one MPI rank to each physical core.

### 18.4 Process Placement Is Part of the Experiment

A benchmark command is not completely specified by `-np`.

CPU mapping and binding can change scheduling and cache behavior.

Therefore, the formal command explicitly records:

```text
--map-by core
--bind-to core
```

and the actual bindings are preserved in the repository.

### 18.5 A Single Fast Run Is Weak Evidence

Early short runs showed substantial performance variation.

A single highest measurement can result from a favorable system state and may not represent the typical performance of a configuration.

The final analysis therefore uses:

```text
repetition
+
pairing
+
reversed order
+
mean / median / CV
```

for the primary optimization.

### 18.6 Different Problem Sizes Must Not Be Reported as Same-Workload Speedup

The HPL computational cost grows approximately as:

```text
O(N^3)
```

Changing `N` changes the amount of work.

Therefore, a larger `N` producing higher GFLOPS is reported as a throughput/problem-size effect rather than as a direct speedup over the baseline problem.

### 18.7 Parameter Interactions Matter

The `BCAST × DEPTH` experiment showed that the apparent effect of `BCAST` changes depending on `DEPTH`.

This demonstrates why a purely one-factor-at-a-time search cannot expose every interaction.

However, interaction exploration also increases the experimental search space, so the study uses a small factorial experiment only after the primary optimization had already been established.

### 18.8 Performance References Must Be Defined Carefully

The nominal base-frequency Rpeak and the empirical DGEMM result answer different questions.

`115.2 GFLOPS`

is an analytical reference based on architectural assumptions and nominal base frequency.

`86.478 GFLOPS`

is the best throughput actually observed in the custom DGEMM experiment.

Neither should be misrepresented as a guaranteed sustained ceiling under all CPU states.

### 18.9 Stop Criteria Are Part of Performance Engineering

An exhaustive HPL parameter search is not practical on a noisy laptop environment.

The search was stopped after:

- the main `NB` effect had been repeatedly validated;
- process-grid and problem-size behavior had been investigated;
- an advanced BCAST × DEPTH interaction had been explored;
- the remaining incremental search value became smaller relative to runtime cost and platform variability.

The objective was therefore not to claim the globally optimal HPL configuration, but to demonstrate a controlled and reproducible optimization process.

---

## 19. Conclusion

This study implemented a complete HPL performance-engineering workflow rather than simply searching for the largest individual GFLOPS value.

The workflow was:

```text
Environment setup
        ↓
Build and linkage verification
        ↓
Correctness smoke test
        ↓
Formal baseline
        ↓
NB coarse search
        ↓
Independent confirmation
        ↓
MPI process-grid comparison
        ↓
Problem-size sensitivity
        ↓
Fixed-N repeated paired validation
        ↓
Sustained-load variability analysis
        ↓
Nominal Rpeak and DGEMM reference
        ↓
BCAST × DEPTH interaction exploration
        ↓
Reproducibility and evidence packaging
```

The main validated configuration is:

```text
N     = 18432
NB    = 192
P × Q = 2 × 2
np    = 4

OMP_NUM_THREADS      = 1
OPENBLAS_NUM_THREADS = 1
```

Under the same workload, the repeated validation produced:

```text
NB=128 mean = 78.204 GFLOPS
NB=192 mean = 82.189 GFLOPS
```

corresponding to:

**a 5.10% mean performance improvement.**

The highest individual HPL observation was:

**84.430 GFLOPS**

The validated HPL mean corresponds to approximately:

**71.3% of the 115.2 GFLOPS nominal base-frequency Rpeak reference**

and:

**95.0% of the 86.478 GFLOPS best-observed empirical DGEMM reference.**

The BCAST × DEPTH mini-sweep additionally exposed a meaningful algorithmic interaction, but because each combination was measured only once, it remains exploratory evidence rather than part of the validated final speedup.

The most important result of the study is therefore not a single benchmark number, but a reproducible methodology:

> performance observations should be connected to algorithmic hypotheses, controlled experiments, correctness checks, repeated measurements, uncertainty awareness, and traceable raw evidence.

The repository preserves the build configuration, HPL parameter files, raw logs, structured results, statistical analysis, figures, environment records, and reproduction instructions required to audit the complete process.
