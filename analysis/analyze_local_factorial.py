"""Validate all 12 HPL logs, summarize the repeat experiment, and plot every run.

Only matplotlib is required. Optional --qa-tools enables local figure QA helpers;
it is not required to reproduce the statistics or final figure.
"""

import argparse
import csv
import hashlib
import math
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CELLS = [(1, 0), (1, 1), (3, 0), (3, 1)]
BCAST_LABELS = {1: "1ringM", 3: "2ringM"}
ORDERS = {1: [(1, 0), (3, 1), (1, 1), (3, 0)],
          2: [(3, 0), (1, 1), (3, 1), (1, 0)],
          3: [(1, 1), (1, 0), (3, 0), (3, 1)]}


def read_verified_results(folder):
    with (folder / "results.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 12:
        raise ValueError(f"Expected 12 completed runs; found {len(rows)}")
    seen = set()
    for row in rows:
        for key in ("block", "position", "bcast", "depth", "N", "NB", "P", "Q", "np", "openblas_threads"):
            row[key] = int(row[key])
        for key in ("time_s", "gflops", "residual"):
            row[key] = float(row[key])
            if not math.isfinite(row[key]) or row[key] <= 0:
                raise ValueError(f"Invalid {key}: {row}")
        identity = (row["block"], row["bcast"], row["depth"])
        if identity in seen or identity[0] not in (1, 2, 3) or identity[1:] not in CELLS:
            raise ValueError(f"Invalid or duplicate cell: {identity}")
        seen.add(identity)
        position = row["position"]
        if position not in (1, 2, 3, 4) or ORDERS[row["block"]][position - 1] != identity[1:]:
            raise ValueError(f"Unexpected run order: {row}")
        if tuple(row[k] for k in ("N", "NB", "P", "Q", "np", "openblas_threads")) != (18432, 192, 2, 2, 4, 1):
            raise ValueError(f"Workload/runtime changed: {row}")
        if row["status"] != "PASSED" or row["residual"] >= 16:
            raise ValueError(f"Failed correctness: {row}")
        raw = (folder / row["log"]).read_text(encoding="utf-8")
        # HPL prints symbolic broadcast names, while HPL.dat/CSV use codes.
        for key, expected in (("BCAST", BCAST_LABELS[row["bcast"]]),
                              ("DEPTH", str(row["depth"]))):
            logged = re.findall(rf"^{key}\s*:\s*(\S+)\s*$", raw, re.M)
            if logged != [expected]:
                raise ValueError(f"Log/CSV {key} mismatch: {row['log']}")
        for key, expected in (("PMAP", "Row-major process mapping"),
                              ("PFACT", "Right"), ("NBMIN", "4"),
                              ("NDIV", "2"), ("RFACT", "Crout"),
                              ("SWAP", "Mix (threshold = 64)"),
                              ("L1", "transposed form"), ("U", "transposed form"),
                              ("EQUIL", "yes"), ("ALIGN", "8 double precision words")):
            logged = re.findall(rf"^{key}\s*:\s*(.*?)\s*$", raw, re.M)
            if logged != [expected]:
                raise ValueError(f"Uncontrolled {key} change: {row['log']}")
        outputs = re.findall(r"^WR\S*\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\S+)\s+(\S+)\s*$", raw, re.M)
        if len(outputs) != 1:
            raise ValueError(f"Expected exactly one HPL result in {row['log']}")
        n, nb, p, q, elapsed, throughput = outputs[0]
        if tuple(map(int, (n, nb, p, q))) != (row["N"], row["NB"], row["P"], row["Q"]):
            raise ValueError(f"Log/config mismatch: {row['log']}")
        if not math.isclose(float(elapsed), row["time_s"], abs_tol=1e-9) or not math.isclose(float(throughput), row["gflops"], abs_tol=1e-9):
            raise ValueError(f"Log/CSV time or GFLOPS mismatch: {row['log']}")
        check = re.findall(r"=\s*([\d.eE+-]+)\s+\.{6}\s+(PASSED|FAILED)", raw)
        if len(check) != 1 or check[0][1] != "PASSED" or not math.isclose(float(check[0][0]), row["residual"], abs_tol=1e-12):
            raise ValueError(f"Log/CSV residual mismatch: {row['log']}")
        if not re.search(r"^\s*0 tests completed and failed residual checks", raw, re.M):
            raise ValueError(f"Failure count missing/nonzero: {row['log']}")
    return rows


def read_recovery(folder, rows):
    """Use retained provenance to identify a resumed run, if one exists.

    A fresh uninterrupted campaign must not inherit the interruption label
    merely because it has the same configuration and repeat numbers.
    """
    provenance = list(folder.glob("recovery_*_provenance.txt"))
    if not provenance:
        return None
    if len(provenance) != 1:
        raise ValueError("Expected at most one recovery provenance record")
    fields = dict(line.split("=", 1) for line in provenance[0].read_text(encoding="utf-8").splitlines() if "=" in line)
    match = re.fullmatch(r"block(\d+)_position(\d+)_bcast(\d+)_depth(\d+)", fields.get("recovery", ""))
    if not match:
        raise ValueError("Recovery provenance does not identify a run")
    block, position, bcast, depth = map(int, match.groups())
    row = next((r for r in rows if (r["block"], r["position"], r["bcast"], r["depth"]) == (block, position, bcast, depth)), None)
    if row is None:
        raise ValueError("Recovery provenance has no matching result")
    log_hash = hashlib.sha256((folder / row["log"]).read_bytes()).hexdigest()
    if log_hash != fields.get("log_sha256") or fields.get("result") != "PASSED":
        raise ValueError("Recovery provenance/log checksum or status mismatch")
    return block, bcast, depth


def write_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def summarize(folder, rows, recovery=None):
    summaries = []
    baseline = [r["gflops"] for r in rows if (r["bcast"], r["depth"]) == (1, 0)]
    base_mean = statistics.mean(baseline)
    for bcast, depth in CELLS:
        group = [r for r in rows if (r["bcast"], r["depth"]) == (bcast, depth)]
        values = [r["gflops"] for r in group]
        mean = statistics.mean(values)
        summaries.append(dict(bcast=bcast, depth=depth, repeats=len(group),
                              mean_time_s=statistics.mean(r["time_s"] for r in group),
                              mean_gflops=mean, median_gflops=statistics.median(values),
                              min_gflops=min(values), max_gflops=max(values),
                              sample_sd_gflops=statistics.stdev(values),
                              cv_pct=statistics.stdev(values) / mean * 100,
                              mean_gflops_change_vs_b1d0_pct=(mean / base_mean - 1) * 100,
                              passed=len(group)))
    write_csv(folder / "summary.csv", summaries)

    # Fixed-other-factor comparisons isolate BCAST and DEPTH. The combined
    # candidate comparison is labeled separately; its effect is not attributed
    # to either factor alone. Report every block, including negative effects.
    comparisons = []
    contrasts = [("DEPTH_at_BCAST1", (1, 0), (1, 1)),
                 ("DEPTH_at_BCAST3", (3, 0), (3, 1)),
                 ("BCAST_at_DEPTH0", (1, 0), (3, 0)),
                 ("BCAST_at_DEPTH1", (1, 1), (3, 1)),
                 ("combined_candidate", (1, 0), (3, 1))]
    for name, base, candidate in contrasts:
        for block in (1, 2, 3):
            lookup = {(r["bcast"], r["depth"]): r for r in rows if r["block"] == block}
            a, b = lookup[base], lookup[candidate]
            comparisons.append(dict(contrast=name, block=block, baseline_bcast=base[0],
                                    baseline_depth=base[1], candidate_bcast=candidate[0],
                                    candidate_depth=candidate[1], baseline_gflops=a["gflops"],
                                    candidate_gflops=b["gflops"],
                                    includes_resumed_run=(recovery in ((block, *base), (block, *candidate))),
                                    gflops_change_pct=(b["gflops"] / a["gflops"] - 1) * 100,
                                    runtime_speedup=a["time_s"] / b["time_s"]))
    write_csv(folder / "comparisons.csv", comparisons)
    print("Validated 12/12 raw logs and CSV rows; all residual checks PASSED.")
    for row in summaries:
        print(f"BCAST={row['bcast']} DEPTH={row['depth']}: mean={row['mean_gflops']:.3f} GFLOPS, "
              f"mean time={row['mean_time_s']:.3f} s, CV={row['cv_pct']:.2f}%, "
              f"change={row['mean_gflops_change_vs_b1d0_pct']:+.2f}%")
    for name, _, _ in contrasts:
        values = [r["gflops_change_pct"] for r in comparisons if r["contrast"] == name]
        print(f"{name}: block changes=" + ", ".join(f"{v:+.2f}%" for v in values))
    # Retain every observation above. If a run was recovered, show complete
    # blocks before that interruption as a separately labeled sensitivity check.
    if recovery is None:
        return summaries
    prior_blocks = sorted({r["block"] for r in rows if r["block"] < recovery[0]})
    if not prior_blocks:
        return summaries
    uninterrupted = []
    for bcast, depth in CELLS:
        group = [r for r in rows if r["block"] in prior_blocks and (r["bcast"], r["depth"]) == (bcast, depth)]
        uninterrupted.append(dict(bcast=bcast, depth=depth, repeats=len(group),
                                  mean_time_s=statistics.mean(r["time_s"] for r in group),
                                  mean_gflops=statistics.mean(r["gflops"] for r in group)))
    write_csv(folder / "uninterrupted_blocks_summary.csv", uninterrupted)
    print(f"Complete blocks before interruption {prior_blocks}; resumed run remains in full summary:")
    for row in uninterrupted:
        print(f"BCAST={row['bcast']} DEPTH={row['depth']}: mean={row['mean_gflops']:.3f} GFLOPS")
    return summaries


def plot(rows, summaries, output, qa_tools=None, preview_only=False, recovery=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if qa_tools:
        sys.path.insert(0, str(qa_tools))
        from setup_style import setup_style
        setup_style(journal="general", lang="en")
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9,
                         "axes.labelsize": 10, "xtick.labelsize": 9,
                         "ytick.labelsize": 9, "legend.fontsize": 8,
                         "svg.fonttype": "none", "pdf.fonttype": 42,
                         "axes.unicode_minus": False})
    # The QA helper measures at 100 dpi. Keep the canvas at the same dpi to
    # avoid mixing cached text positions from a 100-dpi render with a
    # higher-dpi renderer. Final exports still use 300 dpi below.
    fig, ax = plt.subplots(figsize=(6.5, 3.5), dpi=100, constrained_layout=True)
    colors = ["#0072B2", "#D55E00", "#009E73"]
    markers = ["o", "s", "^"]
    offsets = [-0.13, 0, 0.13]
    for block, color, marker, offset in zip((1, 2, 3), colors, markers, offsets):
        vals = [next(r["gflops"] for r in rows if r["block"] == block and (r["bcast"], r["depth"]) == cell) for cell in CELLS]
        ax.scatter([i + offset for i in range(4)], vals, s=40, color=color,
                   marker=marker, linewidth=0.4, edgecolor="black", label=f"Block {block}", zorder=3)
    for i, summary in enumerate(summaries):
        ax.plot([i - 0.23, i + 0.23], [summary["mean_gflops"]] * 2, color="black",
                linewidth=1.5, label="Mean" if i == 0 else None, zorder=2)
    if recovery:
        resumed = next(r for r in rows if (r["block"], r["bcast"], r["depth"]) == recovery)
        point_x = CELLS.index(recovery[1:]) + offsets[recovery[0] - 1]
        ax.annotate("Resumed run", xy=(point_x, resumed["gflops"]),
                    xytext=(point_x - 0.63, max(r["gflops"] for r in rows) * 1.10),
                    fontsize=8, arrowprops={"arrowstyle": "->", "linewidth": 0.7})
    ax.set_xticks(range(4), [f"BCAST={b}\nDEPTH={d}" for b, d in CELLS])
    ax.set_xlabel("HPL parameter configuration (3 repeats each)")
    ax.set_ylabel("HPL performance (GFLOPS)")
    ax.set_title("Local CPU repeats: N=18432, NB=192, 4 ranks", fontsize=10)
    ax.set_ylim(0, max(r["gflops"] for r in rows) * 1.25)
    ax.set_xlim(-0.5, 3.5)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.25, linewidth=0.5)
    ax.legend(loc="upper center", ncol=4, frameon=False)
    if recovery:
        fig.supxlabel("Final run resumed after interruption; see provenance note.", fontsize=8)
    output.mkdir(parents=True, exist_ok=True)
    basename = output / "fig_hpl_local_factorial_20261007"
    if qa_tools:
        from visual_qa import audit_layout, print_report, render_preview
        issues = audit_layout(fig)
        print_report(issues)
        if any(level in ("WARN", "FAIL") for level, _ in issues):
            raise ValueError("Figure layout QA failed")
        render_preview(fig, str(output / "preview" / "factorial.png"))
    if preview_only:
        if not qa_tools:
            fig.savefig(output / "factorial_preview.png", dpi=150)
    elif qa_tools:
        from export_figure import export_figure
        export_figure(fig, basename=str(basename), formats=["png", "svg"],
                      size_inches=(6.5, 3.5), dpi=300, grayscale_preview=False, tight=False)
        # Keep QA previews separate and preserve the final PNG's exact size.
        from PIL import Image
        with Image.open(basename.with_suffix(".png")) as source:
            source.convert("L").save(output / "preview" / "factorial_grayscale.png", dpi=(300, 300))
    else:
        fig.savefig(basename.with_suffix(".png"), dpi=300)
        fig.savefig(basename.with_suffix(".svg"))
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=ROOT / "results" / "local_factorial_20261007")
    parser.add_argument("--figures", type=Path, default=ROOT / "figures")
    parser.add_argument("--qa-tools", type=Path)
    parser.add_argument("--preview-only", action="store_true")
    args = parser.parse_args()
    data = read_verified_results(args.results)
    recovery = read_recovery(args.results, data)
    summary = summarize(args.results, data, recovery)
    plot(data, summary, args.figures, args.qa_tools, args.preview_only, recovery)
