# Regression tests

End-to-end checks that a candidate revision of the Hi-COLA backend reproduces a
pinned baseline. The workflow is `.github/workflows/regression-tests.yml`; the
top-level `README.md` has a short overview and branch-protection advice.

## What is run

The baseline commit is pinned in `baseline.json` (tag
`regression-baseline-d8cd89b`). `run.py` clones the baseline and the candidate
through Git, builds `nbody` plus `force_probe` (`force_probe.cpp`, linked against
the real compiled solver objects), and runs every combination of:

| Case | Model inputs | Force probe |
|---|---|---|
| `gr` | GR | unscreened |
| `cubic_galileon` | Hi-COLA frontend (Horndeski cubic Galileon) | unscreened and screened |
| `kmouflage` | Fixed manufactured background/force tables, not a calibrated cosmology | unscreened and screened, with a stressed gradient-screening coefficient (1e4) |

Each case runs on 1 and 2 MPI ranks, with 16³ particles, to z = 0.

## Comparisons

Tolerances (`rtol`, `atol`) are in `compare.py` (`TOLERANCES`). They are
migration gates for the same inputs and toolchain, not physics accuracy targets.

### Summary statistics: `Regression summary statistics` job (required)

| Check | Report key | Tolerance kind |
|---|---|---|
| Frontend expansion, force and full tables (cubic Galileon); expansion and force (K-mouflage) | `<model>/frontend/<table>` | `tables` (2e-5, 1e-8) |
| Output file inventory identical and non-empty; growth table and P(k) present | `<case>-np<n>/valid_outputs` | — |
| Matter power spectra `pofk*.txt` | `<case>-np<n>/<file>` | `power` (1e-4, 1e-6) |
| Expansion/growth tables `gravitymodel_*` and other text outputs | `<case>-np<n>/<file>` | `tables` |
| Particle count across rank files | `<case>-np<n>/particle_count` | `counts` (exact) |
| Mean velocity components and RMS speed | `<case>-np<n>/velocity_statistics` | `velocity_statistics` (2e-5, 2e-3 km/s) |
| Snapshot sanity: reached z = 0, finite values, 16³ unique IDs, one file per rank, force-probe files present | part of `valid_outputs` | — |

**Artifacts:**
- `regression-summary-report`: `summary-report.json`, with the max absolute error per check and each failure message.
- `regression-summary-statistics`: the compared data, written by `artifacts.py`:
  - `baseline/` and `candidate/<case>-np<n>/`: P(k) and expansion/growth tables
  - `frontend/<revision>/<model>/`: frontend tables
  - `plots/`: figures for every compared quantity (see below)
  - `statistics.json` and `README.md`: velocity statistics table and index. The README is also added to the job summary.

**Plots** (`plots.py`) overlay baseline and candidate. Their lower panels show
`(candidate − baseline) / (atol + rtol × |baseline|)`, so the dotted lines at ±1 are
the pass limits. They are written even when a comparison fails; a plotting problem is
listed in the artifact's `README.md` and never changes the job result.

| Figure | Shows |
|---|---|
| `overview.png` | Worst difference over tolerance for each group of checks |
| `<case>-np<n>/power_evolution.png` | P(k) at every output redshift |
| `<case>-np<n>/velocity_statistics.png` | Mean velocity components and RMS speed |
| `<case>-np<n>/<table>.png` | Every column of each `pofk*`, `gravitymodel_*` and `cosmology_*` table, six per figure; larger tables continue in `<table>_<page>of<pages>.png` |
| `frontend/<model>/<table>.png` | Every column of each frontend table |

Particle counts and snapshot sanity checks are pass/fail, so they are reported rather than plotted.

### Particle reproducibility: `Regression particle reproducibility` job (advisory)

| Check | Report key | Tolerance kind |
|---|---|---|
| Particle IDs identical after sorting | `<case>-np<n>/particle_ids` | exact |
| Positions per particle | `<case>-np<n>/positions` | `positions` (0, 2e-4 Mpc/h) |
| Velocities per particle | `<case>-np<n>/velocities` | `velocities` (2e-5, 2e-3 km/s) |
| Force-probe grid coordinates | `<case>-np<n>/force-<screened>/grid` | exact |
| Force-probe values | `<case>-np<n>/force-<screened>` | `force` (1e-8, 1e-11) |

Artifact: `regression-particles-report` (`particles-report.json`). Raw
simulation outputs and logs for both revisions are in `regression-results`.

## Unit tests of the harness

These run before the simulations (`python -m unittest discover -s tests/regression_tests`):

| File | Covers |
|---|---|
| `test_compare.py` | Tolerance boundaries; rejection of NaN, empty or mismatched arrays; GADGET record parsing and truncation; snapshot epoch and particle identity; force-grid completeness |
| `test_velocity_statistics.py` | Mean/RMS on constant, opposing and reordered velocities; invalid inputs |
| `test_flavours.py` | Which flavour detects which change: power drift, velocity-dispersion drift, missing P(k) and non-finite snapshots fail `summary`; particle translation, reassigned velocities and force drift affect only `particles`; `--compare-only` reuse |
| `test_baseline.py` | Pinned baseline fetchable into a fresh clone; ref/commit mismatch rejected |
| `test_runner.py` | Candidate branch resolution after a fresh clone |
| `test_artifacts.py` | Summary-statistics export (tables, velocity stats, every plot type, index); missing or mismatched outputs recorded rather than raised; multi-figure tables; column labels; axis scales |

## Running locally

```sh
python tests/regression_tests/run.py --work /tmp/hicola-regression --prefix "$CONDA_PREFIX"
# or compare an existing run directory:
python tests/regression_tests/run.py --compare-only --flavour summary --work /tmp/hicola-regression
```
