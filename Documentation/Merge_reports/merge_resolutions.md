# lightcone + kmou_forward: merge resolutions

This report covers branch selection and compatibility changes needed to combine the two features. Independent bug fixes are documented in `bug_fixes.md` and applied in the following commit. The merge commit alone intentionally retains those pre-existing defects; use the final bugfix commit for a working checkout.

The merge has the original feature tips as parents: lightcone `5629166` and kmou_forward `d6abeb3`. There were 30 text-conflict blocks in 15 files, plus two scanner modify/delete conflicts. None of the complete text-conflict blocks was whitespace-only.

## Choices and review priority

- **High — COLA and growth coupling:** retain lightcone's `get_cosmo()` interface and incorporate K-mouflage's `GG4_GN` factors in COLA evolution, growth and timestep weighting. These are intentional Hi-COLA physics additions absent from current upstream FML.
- **Medium — Gravity-model output:** retain lightcone's `output_header`/`output_row` helpers and add the K-mouflage `GG4_GN` column. Review scripts using fixed column positions.
- **Low — Matter/neutrino helpers:** retain lightcone's `get_fMNu()` helpers and existing scopes. Present-day `get_OmegaM()` and `get_OmegaM0()` are equivalent in these implementations; omit redundant declarations.
- **Medium — GR/Geff/JBD and NBody forces:** retain lightcone's finite-difference force and potential routines, alongside K-mouflage's gradient-screening routine. This preserves both capabilities. Check finite-difference model/stencil combinations separately.
- **Medium — Model dispatch:** retain both `mbeta` and `kmouflage`. Add unity `GG4_GN` to `mbeta` because the combined gravity-model interface requires it; this is integration compatibility, not a pre-existing standalone bug.
- **High — Symbolic expressions:** retain lightcone's simplification and K-mouflage's diagnostic tuple returns, expanded lambda dictionary and scalar-dependent expressions.
- **High — Numerical solver:** retain K-mouflage's six-component scalar-aware state and closure return tuple. Keep forward `odeint` and backward `solve_ivp`; rescale initial densities only for forward integration. Update tracking-helper callers for the scalar-aware signature and tuple return.
- **High — Parameter compatibility:** preserve older files without `phi0` or `forwards_flag`, including their closure-index meanings. Add `phi0=0` and use scalar-derivative closure index 2 in the scalar-independent ESS examples. Retain relative output paths.
- **Medium — Utilities and scanner:** combine support utilities; retain the scanner modified in kmou_forward despite its deletion in lightcone. Restore its package initializer and input template.
- **Low — Ancillary numerical-solver block:** retain K-mouflage's plotting settings and nearest-index helper. This conflict contained functionality, not just whitespace. The shared return statement differed by comments, but its conflict also contained additional tracking/growth functions.

## Upstream FML comparison

Compared with HAWinther/FML `f9f666ac3dfbab657f935e37ac86c197ca5d9f89` (20 April 2026), retrieved on 7 October 2026.

- Lightcone headers and GadgetUtils files exactly match upstream.
- Retained GR/Geff/JBD force routines and NBody finite-difference/potential routines match upstream ignoring whitespace.
- GG4_GN, K-mouflage screening and the Python frontend are Hi-COLA-specific.
- The separate `source_factor_2LPT_noalpha` treatment predates this merge in both feature branches and differs from upstream; review its modified-gravity derivation separately.
- An upstream MPI fix for enforced LPT trajectories is absent from both feature branches. It was not applied during this history separation; see the deferred item in the bugfix report.

## Validation of the combined result

The original combined implementation was tested in a new conda environment: frontend imports/syntax and example parsing; ESS-A and cubic Galileon generators; high-precision comparisons against lightcone; scalar-dependent forward smoke check; MPI backend build; small GR/HiCOLA/K-mouflage lightcone runs; and screened K-mouflage with batched ASCII/Gadget output on two MPI ranks.

High-precision comparisons passed at rtol=1e-5, atol=1e-8 with both integrators using atol=1e-10. Default tolerances do not produce bitwise-identical results. Full scanner runs, all closure choices, all finite-difference combinations, Healpix, OpenMP and production-scale simulations remain untested. On macOS, Math.cpp was compiled under C++14 to select its existing GSL implementation; other backend units used C++17. No compiler workaround was added to the source.
