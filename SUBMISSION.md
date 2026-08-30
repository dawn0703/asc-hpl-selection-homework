# ASC Selection Homework Submission — HPL

## 1. 基本信息

- 姓名：张嘉
- 年级专业：25级计算机科学与技术专业1班
- 对应题目：基础题 — HPL

---

## 2. 运行环境

### Hardware

- CPU: Intel Core i7-10510U
- Physical cores: 4
- Logical CPUs: 8
- Host memory: approximately 16 GB
- WSL2 memory: approximately 7.7 GiB

### Software

- Host OS: Windows 11
- Runtime environment: WSL2 Ubuntu 26.04 LTS
- HPL: Netlib HPL 2.3
- GCC / GFortran: 15.2.0
- Open MPI: 5.0.10
- OpenBLAS: 0.3.32 pthread

详细环境记录见：

- [`results/system_info.txt`](results/system_info.txt)
- [`results/software_info.txt`](results/software_info.txt)
- [`results/linked_libraries.txt`](results/linked_libraries.txt)
- [`results/thread_env.txt`](results/thread_env.txt)
- [`results/mpi_binding.txt`](results/mpi_binding.txt)

---

## 3. 完成情况

已完成：

- HPL 2.3 下载、构建和运行环境配置；
- MPI + OpenBLAS 配置；
- correctness smoke test；
- Baseline 测试；
- `NB` coarse sweep；
- `NB=128` 与 `NB=192` fixed-N repeated paired validation；
- MPI process grid (`P × Q`) 比较；
- problem size (`N`) sensitivity test；
- `BCAST × DEPTH` algorithm-level exploration；
- HPL correctness validation；
- run-to-run performance variability analysis；
- nominal base-frequency Rpeak 分析；
- MPI + OpenBLAS DGEMM empirical reference；
- CSV 数据整理、统计分析与自动绘图；
- reproducibility scripts 和 raw logs 整理。

主要经过重复验证的结果：

| Configuration | Mean Performance |
|---|---:|
| `N=18432, NB=128, P×Q=2×2` | 78.204 GFLOPS |
| `N=18432, NB=192, P×Q=2×2` | **82.189 GFLOPS** |

在相同 workload 下：

**NB=192 相对 NB=128 的平均性能提升为 5.10%。**

最高单次 HPL observation：

**84.430 GFLOPS**

完整技术分析见：

[`README.md`](README.md)

---

## 4. 复现方式

### 4.1 获取 HPL

使用官方 Netlib HPL 2.3：

<https://www.netlib.org/benchmark/hpl/>

假设解压目录为：

```bash
export HPL_ROOT=/path/to/hpl-2.3
```

### 4.2 构建

复制本仓库的 build configuration：

```bash
cp build/Make.WSL "$HPL_ROOT/Make.WSL"
```

将 `Make.WSL` 中的 `TOPdir` 修改为实际 HPL 根目录，然后：

```bash
cd "$HPL_ROOT"
make arch=WSL
```

### 4.3 Runtime Environment

```bash
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
```

正式运行使用：

```bash
mpirun -np 4 \
  --map-by core \
  --bind-to core \
  --mca btl self,sm \
  ./xhpl
```

### 4.4 Baseline

使用：

[`configs/HPL_baseline.dat`](configs/HPL_baseline.dat)

主要参数：

```text
N  = 18432
NB = 128
P  = 2
Q  = 2
```

### 4.5 Validated Optimized Configuration

使用：

[`configs/HPL_nb192_confirm.dat`](configs/HPL_nb192_confirm.dat)

主要参数：

```text
N  = 18432
NB = 192
P  = 2
Q  = 2
```

重复验证脚本：

[`scripts/run_fixedN_validation.sh`](scripts/run_fixedN_validation.sh)

---

## 5. 结果与证据

### Raw logs

[`logs/`](logs/)

### Structured results

[`results/`](results/)

主要统计结果：

[`results/final_statistics.csv`](results/final_statistics.csv)

fixed-N repeated validation：

[`results/fixedN_validation.csv`](results/fixedN_validation.csv)

### Figures

[`figures/`](figures/)

主要结果图：

![Fixed-N validation](figures/fig2_fixedN_nb_validation.png)

### Analysis

[`analysis/`](analysis/)

DGEMM empirical-reference analysis：

[`analysis/dgemm/`](analysis/dgemm/)

---

## 6. 源码与修改说明

HPL 使用官方 Netlib HPL 2.3。

上游 HPL computational source code 未修改。

本实验的主要修改和优化集中于：

- `Make.WSL` build configuration；
- `HPL.dat` runtime parameters；
- MPI process layout；
- BLAS/OpenMP thread configuration；
- benchmark scripts；
- analysis and visualization scripts。

详细来源说明：

[`SOURCE.md`](SOURCE.md)

---

## 7. 说明

本仓库中的主要性能结论区分为：

- **validated result**：通过 fixed-N repeated paired experiments 支持；
- **exploratory result**：用于算法参数探索，但没有重复验证；
- **highest observed result**：单次最高观测值。

因此不使用单次最高 GFLOPS 代替稳定性能结论。

更完整的实验过程、参数分析、正确性验证和性能讨论见：

[`README.md`](README.md)
