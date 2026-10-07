#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
HPL_ROOT="${HPL_ROOT:?Set HPL_ROOT to the extracted HPL 2.3 directory}"
RESULT_ROOT="${RESULT_ROOT:?Set RESULT_ROOT to a NEW output directory}"
RUN="$HPL_ROOT/bin/WSL"
RES="$RESULT_ROOT"
LOG="$RES/logs"
CFG="$REPO_ROOT/configs"

export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1

[[ -x "$RUN/xhpl" ]] || { echo "Missing executable: $RUN/xhpl" >&2; exit 1; }
[[ ! -e "$RESULT_ROOT" ]] || { echo "Refusing to overwrite: $RESULT_ROOT" >&2; exit 1; }
mkdir -p "$LOG"
ORIGINAL_CONFIG="$(mktemp)"
cp "$RUN/HPL.dat" "$ORIGINAL_CONFIG"
trap 'cp "$ORIGINAL_CONFIG" "$RUN/HPL.dat"; rm -f "$ORIGINAL_CONFIG"' EXIT

CSV="$RES/final_validation.csv"
echo "experiment,N,NB,P,Q,np,time_s,gflops,status" > "$CSV"

run_case () {
    name="$1"
    config="$2"

    echo "=================================================="
    echo "START $name: $(date)"
    echo "=================================================="

    echo "----- memory before -----"
    free -h

    cp "$config" "$RUN/HPL.dat"

    cd "$RUN"

    mpirun -np 4 \
      --map-by core \
      --bind-to core \
      --mca btl self,sm \
      ./xhpl \
      > "$LOG/${name}.log" 2>&1

    result="$(grep '^WR' "$LOG/${name}.log" | tail -n 1)"
    status="$(grep -q 'PASSED' "$LOG/${name}.log" && echo PASSED || echo FAILED)"

    echo "$result"
    grep -E 'PASSED|FAILED' "$LOG/${name}.log" || true

    echo "$result" | awk -v name="$name" -v status="$status" \
      '{printf "%s,%s,%s,%s,%s,4,%s,%s,%s\n",name,$2,$3,$4,$5,$6,$7,status}' \
      >> "$CSV"

    echo "----- memory after -----"
    free -h

    echo "END $name: $(date)"
}

BASE="$CFG/HPL_baseline.dat"
BEST="$CFG/HPL_n23040.dat"

sleep 90
run_case baseline_final1 "$BASE"

sleep 90
run_case best_final1 "$BEST"

sleep 90
run_case baseline_final2 "$BASE"

sleep 90
run_case best_final2 "$BEST"

sleep 90
run_case baseline_final3 "$BASE"

sleep 90
run_case best_final3 "$BEST"

echo
echo "===== FINAL VALIDATION COMPLETE ====="
cat "$CSV"
