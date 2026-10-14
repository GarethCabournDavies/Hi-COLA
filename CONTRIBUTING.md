# Contributing to Hi-COLA

Contributions to the science, implementation, examples, and documentation are welcome. For substantial changes to equations, screening approximations, interfaces, or dependencies, discuss the proposal with the maintainers before implementing it.

## Questions and bug reports

Use the [project issue tracker](https://github.com/Hi-COLACode/Hi-COLA/issues) for reproducible software problems and feature proposals. Scientific questions can be sent to [team.hicola@gmail.com](mailto:team.hicola@gmail.com).

A useful bug report includes:

- The Git revision, operating system, and Python and dependency versions.
- For backend problems, the compiler, library versions, build command, and MPI/OpenMP settings.
- A minimal set of theory, cosmology, numerical, and Lua inputs needed to reproduce the problem.
- The exact command, relevant log or traceback, expected behaviour, and observed result.
- For numerical discrepancies, units, tolerances, reference results, and simulation resolution and seed.

Attach small reproducing inputs rather than full particle snapshots. Remove credentials and private filesystem or host details from logs before sharing them.

## Development setup

Work in a branch of your fork or checkout. From the repository root:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Runtime dependencies are declared in `pyproject.toml`; the Python package currently uses the development version `0.0.dev0`. Follow the [user manual](Documentation/Hi-COLA_User_manual.pdf) for the separately built C++ backend. The frontend [quickstart guide](Documentation/Hi-COLA_Quickstart_guide.pdf) provides a runnable starting model.

## Making a change

Keep changes focused and match the surrounding code style. Explain non-obvious numerical assumptions, units, and conventions in docstrings or comments. Use `logging.debug` for diagnostic details where runtime visibility is useful; keep comments about what the code does rather than its edit history.

For scientific changes, describe the affected equations or approximation and provide the derivation or reference. Preserve reproducible inputs and show how numerical results compare with a relevant baseline, including tolerances and any expected differences. Add focused tests when they can meaningfully check the changed behaviour.

Update user documentation and examples when commands, parameters, outputs, or scientific assumptions change. Avoid including generated simulation outputs, build products, or unrelated reformatting.

## Checking your work

First reproduce the affected workflow and check the result against the expected behaviour. For numerical changes, successful execution alone is insufficient: inspect the scientific outputs and comparison tolerances.

For documentation changes, check local links, example commands, and scientific terminology. Keep instructions consistent with the checked-in implementation.

Run relevant scientific tests available on your branch and report the exact commands and outcomes. State any checks you could not run, especially backend or MPI checks requiring unavailable dependencies.

## Submitting a contribution

Open a pull request against the repository and branch agreed with its maintainers. Describe the problem, resulting behaviour, scientific implications, and validation performed. Include a small reproducer or before/after comparison where useful, and identify related issues. Keep scientific claims separate from what your checks actually demonstrate.

Please communicate respectfully and give maintainers enough detail to reproduce and review your work.
