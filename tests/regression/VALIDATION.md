# Initial validation

Validated locally on 14 October 2026 using the committed Dockerfile's Linux/GCC
build environment, launched from macOS. The source repository was mounted
read-only and all generated checkouts and outputs were confined to a separate
artifact directory.

The full runner independently cloned and built the baseline and candidate.
Both resolved to `d8cd89b2a8118f99c7b71c4e7cf6963860073612`: this establishes the
baseline reproducibility control, not the equivalence of any future migration.
Neither application checkout was patched.

- Both fresh-clone/dependency-initialisation/build paths succeeded.
- GR, Horndeski, K-mouflage and lightcone completed with one and two MPI ranks
  in both checkouts: 16 complete simulations.
- All 155 comparisons passed, with zero measured differences between the two
  checkouts, including growth, force probes, spectra, particle snapshots and
  lightcone crossings.
- The original Python unit suite, adapted to this baseline API, passed 27 tests
  with one known expected failure (`G3_func(..., 'phi')`).
- Eight regression-harness tests passed, including intentional corrupt-output
  rejection and fresh-clone resolution of a named candidate branch.
- Both workflow YAML files and the conda YAML parsed successfully.

The complete run spent 46.5 seconds executing its logged commands. Backend
compilation took 11.7 seconds for baseline and 12.6 seconds for candidate.
Container image provisioning, CI checkout and artifact upload are additional.
Budget roughly 5–10 minutes on a GitHub-hosted runner, potentially 10–15 minutes
with cold downloads. This is an estimate until the first GitHub run, not an
observed GitHub duration. The workflow has a 45-minute hard timeout.

Local evidence: `/private/tmp/hicola-regression-artifacts/run-05/report.json`.
Commands, logs and numeric outputs remain beside that report; they are not
committed. The workflow retains equivalent artifacts for 14 days. No GitHub
workflow execution or migration validation is claimed by this local run.

Scope limits remain those in [README.md](README.md): the K-mouflage backend
uses manufactured input tables rather than an unvalidated frontend preset;
lightcone particle crossings are covered, HEALPix maps are not; and tests use
an MPI build at one/two ranks rather than testing a non-MPI build.
