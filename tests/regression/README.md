# Migration regression tests

Branch: `regression_tests`. The immutable pre-migration baseline is
`d8cd89b2a8118f99c7b71c4e7cf6963860073612` on
`lightcone_kmou_forward_integration`.

This suite complements the unit tests. The unit suite is included on this branch,
with its fixtures adapted to the integration branch's scalar-field API. Unit and
regression GitHub workflows run independently on pull requests and pushes to
`Hi-COLA_public` or `regression_tests`; the regression workflow also supports
manual dispatch.

## Run the same checks as CI

From this checkout, with Docker running:

```sh
docker build -t hicola-regression tests/regression
mkdir -p regression-results
docker run --rm \
  -v "$PWD:/repository:ro" \
  -v "$PWD/regression-results:/artifacts" \
  hicola-regression python /repository/tests/regression/run.py \
  --repository /repository --candidate-ref HEAD \
  --prefix /usr --make-arg LUA_INCLUDE=/usr/include/lua5.4 \
  --make-arg 'LUA_LINK=-llua5.4 -ldl' --work /artifacts/run
```

`--work` must be a **new** directory. Logs, exit codes, process IDs, commands,
inputs, outputs, compiler/MPI versions, Python package versions, fixture hashes,
commit IDs and submodule revisions are retained. `report.json` reports success
only after both complete runs and all comparisons pass. Timeouts terminate the
whole process group, including MPI children. A failed command or comparison is
a failed job, never a skipped regression. CI uploads reports and run artifacts
on failure as well as success. No baseline files are silently regenerated in Git.

The runner clones both revisions with `git clone --no-local --no-checkout`, checks
out their resolved commits, and runs `git submodule update --init --recursive`
before building. There is no separate clone/build smoke job: these steps are
prerequisites of the actual simulations. The baseline currently bundles FML;
its submodule command is a no-op where no gitlinks exist. Candidate submodules
introduced by a migration must initialise successfully.

Both trees are compiled with the same unmodified Makefile command:

```sh
make -C HiCOLA/FML/COLASolver -j2 \
  FML_INCLUDE="$PWD/HiCOLA" USE_MPI=true USE_OMP=false \
  FFTW_INCLUDE=/usr/include FFTW_LIB=/usr/lib \
  GSL_INCLUDE=/usr/include GSL_LIB=/usr/lib \
  LUA_INCLUDE=/usr/include/lua5.4 LUA_LIB=/usr/lib \
  'LUA_LINK=-llua5.4 -ldl'
```

The runner invokes this command in each clean checkout, with absolute paths.
After building the application it compiles a small force probe against those
same production headers and object files. It does not patch either checkout.
For a migrated directory layout, pass `--backend` and `--fml-include` for the
candidate; the pinned baseline layout stays fixed. Additional `--make-arg`
values apply identically to both builds. Uncommitted application edits are not
included: select a committed `--candidate-ref` to test them.

For a native Linux environment, `conda env create -f tests/regression/environment.yml`
provides the dependencies. Activate it and run
`python tests/regression/run.py --work /absolute/path/new-run`. Conda library
paths default to `$CONDA_PREFIX`; system builds can supply `--prefix` and explicit
Lua overrides as above. The reference CI environment is Linux/GCC. The baseline
has known Apple Clang `std::sph_bessel` incompatibility and unguarded MPI references
in lightcone headers, so the suite uses MPI builds with one and two ranks. It
does not claim to validate a build with MPI disabled or OpenMP enabled.

## Cases and evidence

Each model runs with `mpiexec -n 1` and `mpiexec -n 2` for **both** revisions.
All use 16³ particles, 32³ force/power grids, box length 256 Mpc/h, seed 1234,
fixed Fourier amplitudes, five COLA timesteps, initial redshift 49, and final
redshift zero. These are deterministic migration fixtures, not converged
scientific simulations or screening calibrations.

- **GR:** the production LCDM/GR backend and bundled input matter spectrum.
- **Horndeski:** the shipped cubic-Galileon `cuGal_f0p2` model. The real Python
  frontend generates expansion, scalar and force tables separately in each
  checkout, then the HiCOLA cosmology/gravity backend consumes those tables.
  Its 400 samples span redshift 9999 to zero, covering the backend growth
  integration domain down to scale factor 10⁻⁴. No extrapolated short table is
  used to initialise growth.
- **K-mouflage:** the real `GravityModelkmouflage` backend, analytic LCDM
  expansion on 200 samples, coupling 0.02 and screening coefficient 10⁴. These
  manufactured nonzero inputs deliberately exercise gradient screening. They
  are not presented as a calibrated K-mouflage cosmology, and do **not** test
  `generate_kmouflage_input.py`. A validated frontend preset is needed to add
  that separate physical-model check.
- **Lightcone:** GR with ASCII particle crossings enabled over z=0.05 to zero,
  observer at the box centre and no replicas. The complete cone must contain
  particles. Weak-lensing/HEALPix maps and chunkpix are outside this suite.

Every run must reach its final requested output. The comparison checks the full
numeric output-file inventory, cosmology/growth tables, initial and final power
spectra, and GADGET snapshots. Snapshots must reach z=0 and contain 4096 unique
particle IDs; positions and velocities are aligned by ID. Force probes exercise
an analytic trigonometric density field, compare each cell/component, and run
both linear and screened paths for modified gravity. Lightcone crossings are
combined over ranks/steps, sorted by position and compared with equal counts.
Comparisons are baseline versus candidate **at the same MPI rank count**;
rank-count-independent random-number generation is not assumed.

## Tolerances

Every value must satisfy `abs(candidate-baseline) <= atol + rtol*abs(baseline)`.
Shapes, particle IDs, file inventories and force-grid coordinates must match
exactly. Missing, empty or nonfinite required outputs fail.

| Quantity | Relative tolerance | Absolute tolerance | Reason |
| --- | ---: | ---: | --- |
| Frontend, cosmology and growth tables | 2e-5 | 1e-8 | Limited ASCII precision and small solver roundoff |
| Force components | 1e-8 | 1e-11 | Probe writes 17 significant digits; allow small FFT roundoff |
| Power spectra | 1e-4 | 1e-6 (Mpc/h)³ | Small FFT/particle-assignment differences |
| Snapshot positions | 0 | 2e-4 Mpc/h | Float32 GADGET coordinates in a 256 Mpc/h box |
| Snapshot velocities | 2e-5 | 2e-3 km/s | Float32 output and integration roundoff |
| Lightcone positions | 2e-5 | 2e-3 Mpc/h | ASCII crossing-coordinate precision |

These are explicit, initially conservative **migration acceptance thresholds**,
not a cosmological accuracy claim. A failed comparison requires investigation;
do not widen a threshold automatically. `report.json` records maximum absolute
errors for every comparison. Running baseline against itself establishes a
reproducibility control, not proof that a future migration is correct.

The comparison tests can be checked quickly without a compiler or simulations:

```sh
python -m unittest discover -s tests/regression -p 'test_*.py' -v
```

They deliberately inject excessive differences, nonfinite values, missing force
cells, duplicate grid coordinates, bad GADGET records/epochs and empty cones.

See [VALIDATION.md](VALIDATION.md) for the initial measured run and its limits.
