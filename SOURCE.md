# HPL Source

This experiment uses HPL 2.3 from the official Netlib distribution:

https://www.netlib.org/benchmark/hpl/

The upstream HPL computational source code was not modified.

The local build configuration was adapted through `build/Make.WSL`,
and HPL runtime parameters were varied through the configuration files
under `configs/`.

The experiment focuses on environment construction, BLAS/MPI
configuration, HPL parameter tuning, reproducibility, correctness
validation, and performance analysis.
