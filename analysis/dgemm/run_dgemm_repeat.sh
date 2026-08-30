#!/usr/bin/env bash
set -euo pipefail

export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1

for i in 1 2 3; do
    echo "===== DGEMM repeat $i ====="
    date

    mpirun -np 4 \
      --map-by core \
      --bind-to core \
      --mca btl self,sm \
      ./mpi_dgemm_ceiling 4096 2

    if [ "$i" -lt 3 ]; then
        sleep 180
    fi
done
