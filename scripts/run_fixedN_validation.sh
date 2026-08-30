#!/usr/bin/env bash
set -euo pipefail

ROOT="$HOME/asc-selection/hpl-2.3"
RUN="$ROOT/bin/WSL"
CFG="$ROOT/asc-results/configs"
LOG="$ROOT/asc-results/logs"
CSV="$ROOT/asc-results/fixedN_validation.csv"

export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1

mkdir -p "$LOG"

echo "pair,order,experiment,N,NB,P,Q,np,time_s,gflops,status" > "$CSV"

run_case () {
    pair="$1"
    order="$2"
    name="$3"
    config="$4"

    echo "=================================================="
    echo "START pair=$pair order=$order case=$name: $(date)"
    echo "=================================================="

    free -h

    cp "$config" "$RUN/HPL.dat"
    cd "$RUN"

    mpirun -np 4 \
      --map-by core \
      --bind-to core \
      --mca btl self,sm \
      ./xhpl \
      > "$LOG/fixedN_${pair}_${order}_${name}.log" 2>&1

    result="$(grep '^WR' "$LOG/fixedN_${pair}_${order}_${name}.log" | tail -n 1)"

    if grep -q 'PASSED' "$LOG/fixedN_${pair}_${order}_${name}.log"; then
        status="PASSED"
    else
        status="FAILED"
    fi

    echo "$result"
    grep -E 'PASSED|FAILED' "$LOG/fixedN_${pair}_${order}_${name}.log" || true

    echo "$result" | awk \
      -v pair="$pair" \
      -v order="$order" \
      -v name="$name" \
      -v status="$status" \
      '{printf "%s,%s,%s,%s,%s,%s,%s,4,%s,%s,%s\n",
        pair,order,name,$2,$3,$4,$5,$6,$7,status}' \
      >> "$CSV"
}

BASE="$CFG/HPL_baseline.dat"
OPT="$CFG/HPL_nb192_confirm.dat"

# Pair 1: baseline -> optimized
sleep 180
run_case 1 first baseline "$BASE"

sleep 180
run_case 1 second nb192 "$OPT"

# Pair 2: baseline -> optimized
sleep 180
run_case 2 first baseline "$BASE"

sleep 180
run_case 2 second nb192 "$OPT"

# Pair 3: reverse order
sleep 180
run_case 3 first nb192 "$OPT"

sleep 180
run_case 3 second baseline "$BASE"

echo
echo "===== FIXED-N VALIDATION COMPLETE ====="
cat "$CSV"
