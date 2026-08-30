#!/usr/bin/env python3

from pathlib import Path
import csv
import statistics
import matplotlib.pyplot as plt

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
FIGDIR = ROOT / "figures"
FIGDIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# Utility functions
# ============================================================

def read_csv(filename):
    path = ROOT / "results" / filename
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")

    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def find_result(rows, experiment):
    for row in rows:
        if row["experiment"] == experiment:
            return row

    available = [r["experiment"] for r in rows]
    raise KeyError(
        f"Experiment {experiment!r} not found.\n"
        f"Available experiments: {available}"
    )


def savefig(filename):
    plt.tight_layout()
    out = FIGDIR / filename
    plt.savefig(out, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Generated: {out}")


# ============================================================
# Load raw experimental data
# ============================================================

results = read_csv("results.csv")
fixed = read_csv("fixedN_validation.csv")
advanced = read_csv("bcast_depth_sweep.csv")

dgemm_path = ROOT / "analysis" / "dgemm" / "dgemm_summary.csv"
dgemm = []

if dgemm_path.exists():
    with dgemm_path.open(newline="") as f:
        dgemm = list(csv.DictReader(f))


# ============================================================
# Figure 1
# NB coarse sweep
# ============================================================

nb_rows = [
    find_result(results, "nb_sweep_128"),
    find_result(results, "nb_sweep_192"),
    find_result(results, "nb_sweep_256"),
]

nb_values = [int(r["NB"]) for r in nb_rows]
nb_gflops = [float(r["gflops"]) for r in nb_rows]

plt.figure(figsize=(6.4, 4.2))
plt.plot(nb_values, nb_gflops, marker="o", linewidth=1.8)

plt.xlabel("Block size NB")
plt.ylabel("Performance (GFLOPS)")
plt.title("HPL block-size coarse sweep", pad=12)
plt.xticks(nb_values)
plt.grid(axis="y", alpha=0.25)

span = max(nb_gflops) - min(nb_gflops)
plt.ylim(
    min(nb_gflops) - 0.10 * span,
    max(nb_gflops) + 0.22 * span,
)

for i, (x, y) in enumerate(zip(nb_values, nb_gflops)):
    if i == 0:
        dx, ha = 8, "left"
    elif i == len(nb_values) - 1:
        dx, ha = -8, "right"
    else:
        dx, ha = 0, "center"

    plt.annotate(
        f"{y:.3f}",
        (x, y),
        xytext=(dx, 8),
        textcoords="offset points",
        ha=ha,
        va="bottom",
    )

savefig("fig1_nb_coarse_sweep.png")


# ============================================================
# Figure 2
# Fixed-N paired NB validation
# ============================================================

pairs = sorted({int(r["pair"]) for r in fixed})

nb128_by_pair = {}
nb192_by_pair = {}

for row in fixed:
    pair = int(row["pair"])
    value = float(row["gflops"])

    if row["experiment"] == "baseline":
        nb128_by_pair[pair] = value
    elif row["experiment"] == "nb192":
        nb192_by_pair[pair] = value

nb128 = [nb128_by_pair[p] for p in pairs]
nb192 = [nb192_by_pair[p] for p in pairs]

x = list(range(len(pairs)))
width = 0.36

plt.figure(figsize=(7.4, 4.4))

bars1 = plt.bar(
    [i - width / 2 for i in x],
    nb128,
    width=width,
    label="NB=128",
)

bars2 = plt.bar(
    [i + width / 2 for i in x],
    nb192,
    width=width,
    label="NB=192",
)

plt.xlabel("Validation pair")
plt.ylabel("Performance (GFLOPS)")
plt.title("Fixed-N paired validation", pad=12)
plt.xticks(x, [f"Pair {p}" for p in pairs])
plt.ylim(0, max(nb128 + nb192) * 1.15)
plt.grid(axis="y", alpha=0.25)

plt.legend(
    loc="upper left",
    bbox_to_anchor=(1.01, 1.0),
    borderaxespad=0.0,
)

for bars in (bars1, bars2):
    plt.bar_label(
        bars,
        fmt="%.2f",
        padding=4,
        fontsize=8,
    )

savefig("fig2_fixedN_nb_validation.png")


# ============================================================
# Figure 3
# Process-grid comparison
# ============================================================

grid_1x4 = float(
    find_result(results, "grid_1x4")["gflops"]
)

# nb192_confirm uses the same N, NB and 2x2 grid.
grid_2x2 = float(
    find_result(results, "nb192_confirm")["gflops"]
)

grid_labels = ["1×4", "2×2"]
grid_values = [grid_1x4, grid_2x2]

plt.figure(figsize=(5.5, 4.2))
bars = plt.bar(grid_labels, grid_values)

plt.xlabel("Process grid P×Q")
plt.ylabel("Performance (GFLOPS)")
plt.title("HPL process-grid comparison", pad=12)
plt.ylim(0, max(grid_values) * 1.16)
plt.grid(axis="y", alpha=0.25)

plt.bar_label(
    bars,
    fmt="%.3f",
    padding=5,
)

savefig("fig3_process_grid.png")


# ============================================================
# Figure 4
# Problem-size sensitivity
# ============================================================

n_rows = [
    find_result(results, "n_sweep_15360"),
    find_result(results, "nb192_confirm"),
    find_result(results, "n_sweep_23040"),
]

n_values = [int(r["N"]) for r in n_rows]
n_gflops = [float(r["gflops"]) for r in n_rows]

plt.figure(figsize=(6.4, 4.2))
plt.plot(n_values, n_gflops, marker="o", linewidth=1.8)

plt.xlabel("Problem size N")
plt.ylabel("Performance (GFLOPS)")
plt.title("HPL problem-size sensitivity", pad=12)
plt.xticks(n_values)
plt.grid(axis="y", alpha=0.25)

span = max(n_gflops) - min(n_gflops)
plt.ylim(
    min(n_gflops) - 0.10 * span,
    max(n_gflops) + 0.22 * span,
)

for i, (xval, yval) in enumerate(zip(n_values, n_gflops)):
    if i == 0:
        dx, ha = 8, "left"
    elif i == len(n_values) - 1:
        dx, ha = -8, "right"
    else:
        dx, ha = 0, "center"

    plt.annotate(
        f"{yval:.3f}",
        (xval, yval),
        xytext=(dx, 8),
        textcoords="offset points",
        ha=ha,
        va="bottom",
    )

savefig("fig4_problem_size.png")


# ============================================================
# Figure 5
# BCAST x DEPTH interaction
# ============================================================

adv = {}

for row in advanced:
    key = (int(row["bcast"]), int(row["depth"]))
    adv[key] = float(row["gflops"])

required_adv = [
    (1, 0),
    (1, 1),
    (3, 0),
    (3, 1),
]

for key in required_adv:
    if key not in adv:
        raise KeyError(f"Missing BCAST/DEPTH combination: {key}")

depths = [0, 1]

plt.figure(figsize=(6.4, 4.2))

plt.plot(
    depths,
    [adv[(1, d)] for d in depths],
    marker="o",
    linewidth=1.8,
    label="BCAST=1 (1ringM)",
)

plt.plot(
    depths,
    [adv[(3, d)] for d in depths],
    marker="o",
    linewidth=1.8,
    label="BCAST=3 (2ringM)",
)

plt.xlabel("Look-ahead depth")
plt.ylabel("Performance (GFLOPS)")
plt.title("BCAST × DEPTH interaction", pad=12)
plt.xticks(depths)
plt.legend(loc="upper left")
plt.grid(axis="y", alpha=0.25)

all_adv_values = list(adv.values())
span = max(all_adv_values) - min(all_adv_values)
plt.ylim(
    min(all_adv_values) - 0.10 * span,
    max(all_adv_values) + 0.20 * span,
)

for bcast in [1, 3]:
    for depth in depths:
        value = adv[(bcast, depth)]

        if depth == 0:
            dx, ha = 8, "left"
        else:
            dx, ha = -8, "right"

        plt.annotate(
            f"{value:.3f}",
            (depth, value),
            xytext=(dx, 7),
            textcoords="offset points",
            ha=ha,
            va="bottom",
            fontsize=8,
        )

savefig("fig5_bcast_depth_interaction.png")


# ============================================================
# Statistical summary
# ============================================================

mean128 = statistics.mean(nb128)
median128 = statistics.median(nb128)
stdev128 = statistics.stdev(nb128)
cv128 = stdev128 / mean128 * 100.0

mean192 = statistics.mean(nb192)
median192 = statistics.median(nb192)
stdev192 = statistics.stdev(nb192)
cv192 = stdev192 / mean192 * 100.0

mean_gain = (mean192 / mean128 - 1.0) * 100.0

pair_gains = [
    (nb192_by_pair[p] / nb128_by_pair[p] - 1.0) * 100.0
    for p in pairs
]

nominal_rpeak = 115.2
nominal_efficiency = mean192 / nominal_rpeak * 100.0

best_observed_hpl = max(
    [float(r["gflops"]) for r in results]
    + [float(r["gflops"]) for r in fixed]
    + [float(r["gflops"]) for r in advanced]
)

best_dgemm = None

if dgemm:
    best_dgemm = max(float(r["gflops"]) for r in dgemm)

dgemm_reference_efficiency = (
    mean192 / best_dgemm * 100.0
    if best_dgemm is not None
    else None
)

b10 = adv[(1, 0)]
b11 = adv[(1, 1)]
b30 = adv[(3, 0)]
b31 = adv[(3, 1)]

advanced_gain = (b31 / b10 - 1.0) * 100.0

depth_gain_bcast1 = (b11 / b10 - 1.0) * 100.0
depth_gain_bcast3 = (b31 / b30 - 1.0) * 100.0

bcast_gain_depth0 = (b30 / b10 - 1.0) * 100.0
bcast_gain_depth1 = (b31 / b11 - 1.0) * 100.0


# ============================================================
# Write final_statistics.csv
# ============================================================

stats_path = ROOT / "results" / "final_statistics.csv"

with stats_path.open("w", newline="") as f:
    writer = csv.writer(f)

    writer.writerow(
        ["metric", "value", "unit", "interpretation"]
    )

    writer.writerow([
        "nb128_mean",
        f"{mean128:.3f}",
        "GFLOPS",
        "Fixed-N repeated baseline mean",
    ])

    writer.writerow([
        "nb128_median",
        f"{median128:.3f}",
        "GFLOPS",
        "Fixed-N repeated baseline median",
    ])

    writer.writerow([
        "nb128_cv",
        f"{cv128:.2f}",
        "%",
        "Sample coefficient of variation",
    ])

    writer.writerow([
        "nb192_mean",
        f"{mean192:.3f}",
        "GFLOPS",
        "Fixed-N repeated optimized mean",
    ])

    writer.writerow([
        "nb192_median",
        f"{median192:.3f}",
        "GFLOPS",
        "Fixed-N repeated optimized median",
    ])

    writer.writerow([
        "nb192_cv",
        f"{cv192:.2f}",
        "%",
        "Sample coefficient of variation",
    ])

    writer.writerow([
        "fixedN_mean_improvement",
        f"{mean_gain:.2f}",
        "%",
        "NB=192 mean versus NB=128 mean",
    ])

    for pair, gain in zip(pairs, pair_gains):
        writer.writerow([
            f"fixedN_pair{pair}_improvement",
            f"{gain:.2f}",
            "%",
            "NB=192 versus NB=128 within pair",
        ])

    writer.writerow([
        "nominal_base_frequency_rpeak",
        f"{nominal_rpeak:.1f}",
        "GFLOPS",
        "4 cores × 1.8 GHz × 16 FP64 FLOP/cycle/core",
    ])

    writer.writerow([
        "hpl_mean_over_nominal_rpeak",
        f"{nominal_efficiency:.1f}",
        "%",
        "Validated HPL mean / nominal base-frequency Rpeak",
    ])

    writer.writerow([
        "highest_observed_hpl",
        f"{best_observed_hpl:.3f}",
        "GFLOPS",
        "Highest single HPL observation in retained datasets",
    ])

    if best_dgemm is not None:
        writer.writerow([
            "best_observed_dgemm",
            f"{best_dgemm:.3f}",
            "GFLOPS",
            "Empirical reference, not a strict ceiling",
        ])

        writer.writerow([
            "hpl_mean_over_best_observed_dgemm",
            f"{dgemm_reference_efficiency:.1f}",
            "%",
            "Empirical comparison only",
        ])

    writer.writerow([
        "bcast3_depth1_gain_vs_bcast1_depth0",
        f"{advanced_gain:.2f}",
        "%",
        "Single-session exploratory comparison",
    ])

    writer.writerow([
        "depth1_gain_at_bcast1",
        f"{depth_gain_bcast1:.2f}",
        "%",
        "Exploratory main effect within BCAST=1",
    ])

    writer.writerow([
        "depth1_gain_at_bcast3",
        f"{depth_gain_bcast3:.2f}",
        "%",
        "Exploratory main effect within BCAST=3",
    ])

    writer.writerow([
        "bcast3_gain_at_depth0",
        f"{bcast_gain_depth0:.2f}",
        "%",
        "Shows interaction: BCAST=3 is worse at DEPTH=0",
    ])

    writer.writerow([
        "bcast3_gain_at_depth1",
        f"{bcast_gain_depth1:.2f}",
        "%",
        "Shows interaction: BCAST=3 is better at DEPTH=1",
    ])


# ============================================================
# Write a machine-readable figure manifest
# ============================================================

manifest_path = FIGDIR / "README.txt"

manifest_path.write_text(
    """HPL Figures
===========

fig1_nb_coarse_sweep.png
  Coarse block-size search: NB=128, 192, 256.

fig2_fixedN_nb_validation.png
  Three paired fixed-N validation runs comparing NB=128 and NB=192.
  This is the primary figure supporting the validated optimization claim.

fig3_process_grid.png
  Comparison between 1x4 and 2x2 MPI process grids.

fig4_problem_size.png
  Problem-size sensitivity. N changes the workload, so this plot must not
  be interpreted as same-workload speedup.

fig5_bcast_depth_interaction.png
  Exploratory 2x2 BCAST x DEPTH experiment. Each cell has one observation;
  therefore it is evidence of an interaction pattern, not a validated
  stable speedup.
"""
)

print()
print("Final statistics:")
print(f"  NB=128 mean               : {mean128:.3f} GFLOPS")
print(f"  NB=192 mean               : {mean192:.3f} GFLOPS")
print(f"  Fixed-N mean improvement  : {mean_gain:.2f}%")
print(f"  NB=128 CV                 : {cv128:.2f}%")
print(f"  NB=192 CV                 : {cv192:.2f}%")
print(f"  Nominal Rpeak             : {nominal_rpeak:.1f} GFLOPS")
print(f"  HPL / nominal Rpeak       : {nominal_efficiency:.1f}%")
print(f"  Highest observed HPL      : {best_observed_hpl:.3f} GFLOPS")

if best_dgemm is not None:
    print(f"  Best observed DGEMM       : {best_dgemm:.3f} GFLOPS")
    print(
        "  HPL / DGEMM reference     : "
        f"{dgemm_reference_efficiency:.1f}%"
    )

print(f"  B3D1 vs B1D0              : {advanced_gain:.2f}%")

print()
print(f"Generated statistics: {stats_path}")
print(f"Generated manifest  : {manifest_path}")
