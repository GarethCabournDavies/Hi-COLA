# lightcone + kmou_forward: independent bug fixes

These corrections are separated from branch-selection and integration decisions into the commit following the merge. The resulting executable source is unchanged from the previously tested final integration tree (`61bb651`); this operation reorganizes the existing changes rather than introducing further fixes.

## Applied corrections

- **Medium — Missing K argument in the K-mouflage generator**

  File: `HiCOLA/Frontend/generate_kmouflage_input.py`, line 74.

  ```diff
  -lambdified_kmou = eb.create_kmouflage(G4, symbol_list, mass_ratio_list)
  +lambdified_kmou = eb.create_kmouflage(G4, K, symbol_list, mass_ratio_list)
  ```

  The expression-builder signature already required K in kmou_forward. The old call fails argument binding; the corrected call matches that signature.

- **High — Missing scalar argument in radiation/matter closure calls**

  File: `HiCOLA/Frontend/numerical_solver.py`, lines 181 and 183, within `fried_RHS_wrapper`.

  ```diff
  -return fried_RHS_lambda(E,phi_prime,cl_variable,Omega_m,Omega_l,*parameters)
  +return fried_RHS_lambda(E,phi,phi_prime,cl_variable,Omega_m,Omega_l,*parameters)
  -return fried_RHS_lambda(E,phi_prime,Omega_r,cl_variable,Omega_l,*parameters)
  +return fried_RHS_lambda(E,phi,phi_prime,Omega_r,cl_variable,Omega_l,*parameters)
  ```

  These two calls in kmou_forward omitted phi despite its scalar-aware lambda signature. Both original missing-argument failures were reproduced with a six-argument closure function; corrected calls were checked for argument order and which density is replaced. This validates the wrapper only, not the full radiation/matter closure workflow through parameter readers.

- **Low — Stray conflict marker in the backend Lua template**

  File: `HiCOLA/Parameter_files/Backend_parameter_files/Hi-COLA_params.lua`, original first line.

  ```diff
  -<<<<<<< HEAD:HiCOLA/Parameter_files/Backend_parameter_files/Hi-COLA_params.lua
  ```

  This marker already existed in lightcone and makes the file invalid Lua. The original syntax failure was reproduced; the corrected template parses.

- **Medium — Missing emulator dependency under the backend include root**

  ```text
  FML/Emulator/EuclidEmulator2.h   -> HiCOLA/FML/Emulator/EuclidEmulator2.h
  FML/Emulator/EuclidEmulator2.dat -> HiCOLA/FML/Emulator/EuclidEmulator2.dat
  FML/Emulator/example/Main.cpp   -> HiCOLA/FML/Emulator/example/Main.cpp
  FML/Emulator/example/Makefile   -> HiCOLA/FML/Emulator/example/Makefile
  ```

  The backend includes FML/Emulator from an include root of HiCOLA. Its untracked local copy masked the missing committed dependency during the first build. All four added files are exact copies of lightcone's tracked content and also match the checked latest upstream FML files. No emulator implementation or data was changed.

## Validation

Focused checks reproduce the original missing generator argument, both closure-wrapper failures and the Lua syntax failure, and verify their corrected forms. Emulator copies are checked byte-for-byte. Final non-report tracked files are compared against `61bb651`; there is no executable-code change from the previously validated combined implementation.

The combined implementation previously passed the frontend and MPI checks described in `merge_resolutions.md`. This separation does not claim full scanner, all-closure-choice, Healpix, OpenMP or production-scale validation.

## Deferred upstream issue — not applied

Latest checked FML commit: [f9f666ac3dfbab657f935e37ac86c197ca5d9f89](https://github.com/HAWinther/FML/commit/f9f666ac3dfbab657f935e37ac86c197ca5d9f89), 20 April 2026.

Upstream adds this after the non-scale-dependent COLA kick/drift call in Simulation.h:

```cpp
if (simulation_enforce_LPT_trajectories) part.communicate_particles();
```

Neither input feature branch contains it. It remains unapplied, so no unrelated upstream behaviour is introduced by the separation. If enforced LPT trajectories under MPI are supported for this release, reproduce that path and handle the fix in a dedicated follow-up commit. Earlier smoke tests used simulation_enforce_LPT_trajectories=false.
