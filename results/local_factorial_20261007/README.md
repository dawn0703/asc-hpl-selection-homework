# 本机 HPL BCAST × DEPTH 重复实验

日期：2026-10-07；本地 CPU/WSL2 实验，不使用 GPU。本目录作为本次新提交的证据，保留全部 12 次求解、统计、环境和补跑来源记录。

固定 `N=18432, NB=192, P×Q=2×2`；4 MPI ranks，每 rank 1 个 BLAS thread。四种组合为 `BCAST={1,3} × DEPTH={0,1}`，每组保留 3 次观测，共 12 次，全部 `PASSED`。`BCAST=1/3` 对应日志中的 `1ringM/2ringM`。源码、矩阵规模及核心求解过程没有修改。

```bash
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
# 在配置好的 HPL_ROOT/bin/WSL 中执行
mpirun -np 4 --map-by core --bind-to core --mca btl self,sm ./xhpl
```

## 文件用途

| 文件 | 用途 |
|---|---|
| `results.csv` | 全部 12 次参数、顺序、时间、GFLOPS、残差、状态和日志路径 |
| `logs/` | 12 份 HPL 原始文本输出 |
| `environment.txt` | 初始软硬件、动态链接库、配置/程序哈希、命令和线程记录 |
| `software_versions_followup.txt` | 对初始 MPI 版本查询失败的后续只读核查 |
| `recovery_block3_4_provenance.txt` | 中断后末次补跑时间、日志哈希及原配置恢复情况 |
| `summary.csv` | 四组全量均值、中位数、范围、样本标准差和 CV |
| `comparisons.csv` | 每个 block 固定另一因素时的对比、组合候选对比，以及是否涉及补跑 |
| `uninterrupted_blocks_summary.csv` | 中断前两个完整 block 的敏感性检查；不替代全量统计 |

## 结果与边界

| BCAST | DEPTH | Mean time (s) | Mean GFLOPS | CV |
|---:|---:|---:|---:|---:|
| 1 | 0 | 70.777 | 59.861 | 15.14% |
| 1 | 1 | 70.463 | 59.582 | 9.33% |
| 3 | 0 | 65.413 | 64.200 | 9.16% |
| 3 | 1 | 59.913 | 70.530 | 13.89% |

最后一格 `3/1` 在初始实验停止后约 14 分钟单独补跑，得到 `51.02 s / 81.838 GFLOPS`。它与前两次同配置的 `65.167 / 64.584 GFLOPS` 有明显差异。保留该真实观测，但不能把全部均值的表观 `+17.82%` 视为稳定加速。前两个完整 block 中 `3/1` 相对 `1/0` 分别为 `-6.77% / +12.49%`，方向不一致。本轮没有确立稳定赢家。

未同步采集频率、功耗、温度和宿主负载，无法断言具体波动原因。原始 `environment.txt` 的 `mpirun --version` 查询报帮助文件缺失；后续 `ompi_info` 和包元数据确认 Open MPI 5.0.10，见版本补充记录。查询异常没有阻止实际 12 次 HPL 求解。

`software_versions_followup.txt` 同时记录 GCC/GFortran 15.2.0 和 OpenBLAS 0.3.32 的查询结果。12 次 scaled residual 均为 `2.20938038e-3 < 16`；本轮没有确立稳定收益，因此不把表观 17.82% 当作有效优化结论。

历史 `NB=128→192` 的三轮配对数据仍单独保存在 [`../fixedN_validation.csv`](../fixedN_validation.csv)：平均 HPL 时间 `53.547→50.827 s`，平均 GFLOPS `78.204→82.189`，提升 5.10%。本机同日的单轮 NB 复测另见 [`../local_rerun_20261007.csv`](../local_rerun_20261007.csv)，为 `56.06 s / 74.472 GFLOPS` 和 `57.43 s / 72.696 GFLOPS`，两次均 `PASSED`。它们说明历史均值不是每次运行的保证；这三份数据不能混合计算收益。

## 复现与绘图口径

在仓库根目录运行：

```bash
export REPO_ROOT="$(pwd)"
python3 analysis/analyze_local_factorial.py \
  --results "$REPO_ROOT/results/local_factorial_20261007" \
  --figures "$REPO_ROOT/figures"
```

需要 Python 和 Matplotlib。脚本核对全部 CSV/raw log 参数、固定参数、时间、GFLOPS、残差、`PASSED` 及恢复日志哈希；再生成统计和 PNG/SVG。`--results` 和 `--figures` 可指定新实验目录和图目录。新数据没有恢复记录时不会自动标成“补跑”。

图表用途：展示四种组合的全部观测、重复波动和补跑限制。每点为一次完整求解；横线为算术平均，颜色和点形区分 block。每组 n=3，没有误差棒、置信区间或显著性检验。使用 Python/Matplotlib，6.5×3.5 英寸、300 DPI PNG 和可编辑文字 SVG；布局和灰度预览已检查。临时预览不作为公开证据。

新一轮测量应使用仓库根目录下的脚本和新的输出目录：

```bash
cd "$REPO_ROOT"
export HPL_ROOT=/path/to/hpl-2.3
export RESULT_ROOT="$REPO_ROOT/results/factorial_new_run"
export COOLDOWN_S=15
bash scripts/run_local_factorial_validation.sh
python3 analysis/analyze_local_factorial.py \
  --results "$RESULT_ROOT" --figures "$REPO_ROOT/figures/new_run"
```

`HPL_ROOT` 应指向已经构建出 `bin/WSL/xhpl` 的 HPL 2.3 目录；`REPO_ROOT` 由脚本位置自动推导或使用上述保存的值。`RESULT_ROOT` 必须尚不存在，脚本拒绝覆盖既有证据；不要指向本目录。脚本会恢复原 `HPL.dat`，但没有通用断点续跑功能。本次末格补跑保留独立 provenance，不作为通用续跑入口。换一台机器或重跑同一机器，都不能保证得到相同 GFLOPS。
