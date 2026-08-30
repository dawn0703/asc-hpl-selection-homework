HPL Figures
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
