# Hi-COLA

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/logos/Hi-COLA-dark.png">
  <source media="(prefers-color-scheme: light)" srcset="assets/logos/Hi-COLA-light.png">
  <img alt="Hi-COLA logo" src="assets/logos/Hi-COLA-light.png" width="160">
</picture>

**Fast, approximate N-body simulations of structure formation in reduced Horndeski gravity.**

[User manual](Documentation/Hi-COLA_User_manual.pdf) · [Quickstart](Documentation/Hi-COLA_Quickstart_guide.pdf) · [Contributing](CONTRIBUTING.md)

[![Cite Hi-COLA](https://img.shields.io/badge/Cite-Hi--COLA-blue)](CITATION.md)

Hi-COLA takes an input Lagrangian and constructs the field equations for reduced Horndeski theories with luminal gravitational waves. Its Python frontend solves the cosmological background, linear growth, and screened fifth force, then exports tables for a C++ backend adapted from the FML library. The backend evolves particles using the COLA approximation, allowing researchers to study non-linear structure formation at reduced computational cost.

## Capabilities

- Construct model equations from user-supplied Horndeski functions.
- Generate consistent background and fifth-force tables.
- Run approximate N-body simulations with Vainshtein screening; K-mouflage models require the settings described in the associated paper and documentation.
- Analyse particle snapshots and matter power spectra.

Hi-COLA is an approximate simulation tool. Accuracy depends on the model, scale, and simulation settings; consult the validation papers below before choosing a research configuration.

## Get started

From a repository checkout, install the Python frontend in an isolated environment:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Generate input tables for a supplied cubic Galileon model:

```sh
MPLBACKEND=Agg python -m HiCOLA.Frontend.generate_simulation_input \
  HiCOLA/Parameter_files/Frontend_parameter_files/examples/cubic_Galileon/cuGal_f0p2.ini \
  HiCOLA/Parameter_files/Frontend_parameter_files/examples/WMAP_cosmological_parameters.ini
```

This writes expansion and fifth-force tables to `Hi-COLA_Output/`. Follow the [quickstart guide](Documentation/Hi-COLA_Quickstart_guide.pdf) and [user manual](Documentation/Hi-COLA_User_manual.pdf) to configure, build, and run the C++ simulator. The backend requires separate compiler and library dependencies; installing the Python package does not build it.

The [quickstart guide](Documentation/Hi-COLA_Quickstart_guide.pdf) and [user manual](Documentation/Hi-COLA_User_manual.pdf) describe the workflow and scientific background.

## Scientific references and citation

Please cite the [Hi-COLA introduction paper](https://doi.org/10.1088/1475-7516/2023/03/040) when using the code. The [citation guide](CITATION.md) includes BibTeX, model-specific references, and guidance for recording the software revision. Machine-readable citation metadata is available in [CITATION.cff](CITATION.cff).

- **Method and initial validation:** [Hi-COLA: Fast, approximate simulations of structure formation in Horndeski gravity](https://arxiv.org/abs/2209.01666).
- **K-mouflage extension:** [K-mouflage at high k: extending the reach of Hi-COLA](https://arxiv.org/abs/2407.00855).
- **Comparison with other methods:** [Matter Power Spectra in Modified Gravity: A Comparative Study of Approximations and N-Body Simulations](https://arxiv.org/abs/2406.13667).

## Development and support

Hi-COLA is under active development. See [CONTRIBUTING.md](CONTRIBUTING.md) to report a reproducible issue or propose a change. For scientific questions, contact the team at [team.hicola@gmail.com](mailto:team.hicola@gmail.com).

Hi-COLA is provided under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), as stated by the project. Bundled dependencies retain their own licensing terms.
