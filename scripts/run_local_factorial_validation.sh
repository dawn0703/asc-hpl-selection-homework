#!/usr/bin/env bash
# Repeat the four existing BCAST/DEPTH cells at the same workload.
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
HPL_ROOT="${HPL_ROOT:?Set HPL_ROOT to the HPL 2.3 source/build directory}"
RESULT_ROOT="${RESULT_ROOT:?Set RESULT_ROOT to a NEW output directory}"
COOLDOWN_S="${COOLDOWN_S:-15}"
RUN="$HPL_ROOT/bin/WSL"

[[ -x "$RUN/xhpl" ]] || { echo "Missing executable: $RUN/xhpl" >&2; exit 1; }
[[ ! -e "$RESULT_ROOT" ]] || { echo "Refusing to overwrite: $RESULT_ROOT" >&2; exit 1; }
mkdir -p "$RESULT_ROOT/logs"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1

# Preserve the user's original working HPL.dat, including on failure.
ORIGINAL_CONFIG="$(mktemp)"
cp "$RUN/HPL.dat" "$ORIGINAL_CONFIG"
trap 'cp "$ORIGINAL_CONFIG" "$RUN/HPL.dat"; rm -f "$ORIGINAL_CONFIG"' EXIT

{
  date -Is
  uname -a
  lscpu
  free -h
  cat /etc/os-release
  mpirun --version
  ldd "$RUN/xhpl"
  sha256sum "$RUN/xhpl" "$REPO_ROOT"/configs/HPL_bcast*.dat
  echo "OMP_NUM_THREADS=$OMP_NUM_THREADS OPENBLAS_NUM_THREADS=$OPENBLAS_NUM_THREADS"
  echo "COOLDOWN_S=$COOLDOWN_S"
  echo 'command: mpirun -np 4 --map-by core --bind-to core --mca btl self,sm ./xhpl'
} > "$RESULT_ROOT/environment.txt" 2>&1

printf 'block,position,bcast,depth,N,NB,P,Q,np,openblas_threads,time_s,gflops,residual,status,log\n' > "$RESULT_ROOT/results.csv"

run_cell() {
  local block="$1" position="$2" bcast="$3" depth="$4"
  local config="$REPO_ROOT/configs/HPL_bcast${bcast}_depth${depth}.dat"
  local logfile="$RESULT_ROOT/logs/block${block}_${position}_bcast${bcast}_depth${depth}.log"
  cp "$config" "$RUN/HPL.dat"
  echo "START block=$block position=$position BCAST=$bcast DEPTH=$depth $(date -Is)"
  (cd "$RUN" && mpirun -np 4 --map-by core --bind-to core --mca btl self,sm ./xhpl) > "$logfile" 2>&1
  awk -v block="$block" -v pos="$position" -v b="$bcast" -v d="$depth" -v log_path="logs/$(basename "$logfile")" '
    /^WR/ { n=$2; nb=$3; p=$4; q=$5; t=$6; g=$7; rows++ }
    /\.\.\.\.\.\. (PASSED|FAILED)/ { residual=$(NF-2); status=$NF }
    /tests completed and failed residual checks/ { failures=$1 }
    END {
      if (rows != 1 || status != "PASSED" || failures != 0) exit 1;
      printf "%s,%s,%s,%s,%s,%s,%s,%s,4,1,%s,%.3f,%s,%s,%s\n", block,pos,b,d,n,nb,p,q,t,g,residual,status,log_path
    }' "$logfile" >> "$RESULT_ROOT/results.csv"
  if command -v rg >/dev/null 2>&1; then
    rg '^WR|\.\.\.\.\.\. (PASSED|FAILED)' "$logfile" || true
  else
    grep -E '^WR|\.\.\.\.\.\. (PASSED|FAILED)' "$logfile" || true
  fi
  echo "END block=$block position=$position $(date -Is)"
  sleep "$COOLDOWN_S"
}

# Three blocks; change the order between blocks rather than testing one cell
# repeatedly first. Existing configs differ only in BCAST and DEPTH.
run_cell 1 1 1 0
run_cell 1 2 3 1
run_cell 1 3 1 1
run_cell 1 4 3 0
run_cell 2 1 3 0
run_cell 2 2 1 1
run_cell 2 3 3 1
run_cell 2 4 1 0
run_cell 3 1 1 1
run_cell 3 2 1 0
run_cell 3 3 3 0
run_cell 3 4 3 1
echo "COMPLETE: $RESULT_ROOT/results.csv"
