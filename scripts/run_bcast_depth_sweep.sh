#!/usr/bin/env bash
set -euo pipefail

ROOT="$HOME/asc-selection/hpl-2.3"
RUN="$ROOT/bin/WSL"
CFG="$ROOT/asc-results/configs"
LOG="$ROOT/asc-results/logs"
CSV="$ROOT/asc-results/bcast_depth_sweep.csv"

BASE="$CFG/HPL_nb192_confirm.dat"

export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1

mkdir -p "$CFG" "$LOG"

echo "experiment,bcast,depth,N,NB,P,Q,np,time_s,gflops,status" > "$CSV"

make_config () {
    bcast="$1"
    depth="$2"
    out="$3"

    python3 - "$BASE" "$out" "$bcast" "$depth" <<'PY'
from pathlib import Path
import sys
import re

src = Path(sys.argv[1])
dst = Path(sys.argv[2])
bcast = sys.argv[3]
depth = sys.argv[4]

lines = src.read_text().splitlines()

found_bcast = False
found_depth = False

for i, line in enumerate(lines):
    if re.match(r'^\s*\d+\s+BCASTs\b', line):
        suffix = line[line.index("BCASTs"):]
        lines[i] = f"{bcast:<12} {suffix}"
        found_bcast = True

    if re.match(r'^\s*\d+\s+DEPTHs\b', line):
        suffix = line[line.index("DEPTHs"):]
        lines[i] = f"{depth:<12} {suffix}"
        found_depth = True

if not found_bcast or not found_depth:
    raise RuntimeError(
        f"Failed to locate BCAST/DEPTH lines: "
        f"BCAST={found_bcast}, DEPTH={found_depth}"
    )

dst.write_text("\n".join(lines) + "\n")
PY
}

run_case () {
    name="$1"
    bcast="$2"
    depth="$3"

    config="$CFG/HPL_${name}.dat"
    logfile="$LOG/${name}.log"

    make_config "$bcast" "$depth" "$config"

    echo
    echo "=================================================="
    echo "START $name: $(date)"
    echo "BCAST=$bcast DEPTH=$depth"
    echo "=================================================="

    echo "----- CONFIG -----"
    grep -E 'Ns|NBs|Ps|Qs|BCASTs|DEPTHs' "$config"

    echo "----- MEMORY BEFORE -----"
    free -h

    cp "$config" "$RUN/HPL.dat"

    cd "$RUN"

    mpirun -np 4 \
      --map-by core \
      --bind-to core \
      --mca btl self,sm \
      ./xhpl \
      > "$logfile" 2>&1

    result="$(grep '^WR' "$logfile" | tail -n 1)"

    if grep -q 'PASSED' "$logfile"; then
        status="PASSED"
    else
        status="FAILED"
    fi

    echo "----- RESULT -----"
    echo "$result"
    grep -E 'PASSED|FAILED' "$logfile" || true

    echo "$result" | awk \
      -v name="$name" \
      -v bcast="$bcast" \
      -v depth="$depth" \
      -v status="$status" \
      '{
        printf "%s,%s,%s,%s,%s,%s,%s,4,%s,%s,%s\n",
        name,bcast,depth,$2,$3,$4,$5,$6,$7,status
      }' >> "$CSV"

    echo "END $name: $(date)"
}

# 先冷却，降低此前工作负载对第一组的影响
sleep 180

# 交错顺序，避免参数取值完全与时间顺序绑定
run_case bcast1_depth0 1 0

sleep 120
run_case bcast3_depth1 3 1

sleep 120
run_case bcast1_depth1 1 1

sleep 120
run_case bcast3_depth0 3 0

echo
echo "=================================================="
echo "BCAST × DEPTH SWEEP COMPLETE"
echo "=================================================="
cat "$CSV"
