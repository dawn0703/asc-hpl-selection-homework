#include <mpi.h>
#include <cblas.h>

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

static double *alloc_matrix(size_t n)
{
    void *ptr = NULL;
    size_t bytes = n * n * sizeof(double);

    if (posix_memalign(&ptr, 64, bytes) != 0) {
        return NULL;
    }

    return (double *)ptr;
}

static void init_matrix(double *a, size_t n, double seed)
{
    size_t total = n * n;

    for (size_t i = 0; i < total; ++i) {
        a[i] = seed + (double)(i % 97) * 1.0e-4;
    }
}

int main(int argc, char **argv)
{
    MPI_Init(&argc, &argv);

    int rank, nranks;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &nranks);

    if (argc != 3) {
        if (rank == 0) {
            fprintf(stderr, "Usage: %s N REPS\n", argv[0]);
        }
        MPI_Finalize();
        return 1;
    }

    const size_t n = (size_t)strtoull(argv[1], NULL, 10);
    const int reps = atoi(argv[2]);

    double *A = alloc_matrix(n);
    double *B = alloc_matrix(n);
    double *C = alloc_matrix(n);

    if (!A || !B || !C) {
        fprintf(stderr, "Rank %d: allocation failed\n", rank);
        MPI_Abort(MPI_COMM_WORLD, 2);
    }

    init_matrix(A, n, 0.001 * (rank + 1));
    init_matrix(B, n, 0.002 * (rank + 1));
    init_matrix(C, n, 0.0);

    /*
     * Warm-up:
     * 让 OpenBLAS 初始化，并让 CPU 进入实际计算状态。
     */
    cblas_dgemm(
        CblasRowMajor,
        CblasNoTrans,
        CblasNoTrans,
        (int)n, (int)n, (int)n,
        1.0,
        A, (int)n,
        B, (int)n,
        0.0,
        C, (int)n
    );

    MPI_Barrier(MPI_COMM_WORLD);

    double start = MPI_Wtime();

    for (int r = 0; r < reps; ++r) {
        cblas_dgemm(
            CblasRowMajor,
            CblasNoTrans,
            CblasNoTrans,
            (int)n, (int)n, (int)n,
            1.0,
            A, (int)n,
            B, (int)n,
            0.0,
            C, (int)n
        );
    }

    MPI_Barrier(MPI_COMM_WORLD);

    double elapsed = MPI_Wtime() - start;
    double max_elapsed = 0.0;

    MPI_Reduce(
        &elapsed,
        &max_elapsed,
        1,
        MPI_DOUBLE,
        MPI_MAX,
        0,
        MPI_COMM_WORLD
    );

    /*
     * One n x n DGEMM ~= 2*n^3 FLOPs.
     * Aggregate across every MPI rank.
     */
    if (rank == 0) {
        double total_flops =
            (double)nranks *
            (double)reps *
            2.0 *
            (double)n *
            (double)n *
            (double)n;

        double gflops = total_flops / max_elapsed / 1.0e9;

        printf(
            "DGEMM_RESULT ranks=%d N=%zu reps=%d time=%.6f GFLOPS=%.3f\n",
            nranks, n, reps, max_elapsed, gflops
        );
    }

    /*
     * 简单触碰结果，保证结果确实被使用。
     */
    volatile double checksum = C[0] + C[n * n - 1];
    (void)checksum;

    free(A);
    free(B);
    free(C);

    MPI_Finalize();
    return 0;
}
