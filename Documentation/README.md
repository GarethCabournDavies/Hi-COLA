# Hi-COLA documentation

Hi-COLA connects a Python solver for reduced Horndeski models to a C++ COLA N-body simulator. The frontend exports background and fifth-force tables; the backend uses those tables with an initial matter spectrum to evolve particles.

## Start here

1. [Install the frontend and backend](installation.md).
2. [Generate tables with a supplied model](quickstart.md).
3. [Configure your theory and cosmology](frontend.md).
4. [Run a small simulation, then scale up](backend.md).
5. [Inspect outputs](outputs.md) and [troubleshoot problems](troubleshooting.md).

These pages describe the checked-in implementation. Paths in shell examples are relative to the repository root unless stated otherwise. The original [quickstart PDF](Hi-COLA_Quickstart_guide.pdf) and [user manual PDF](Hi-COLA_User_manual.pdf) remain available for theoretical background and historical guidance. Where template comments disagree with executable code, these pages follow the code.

## Reference and development

- [FML COLA solver documentation](repo:HiCOLA/FML/COLASolver/README.md)
- [Frontend model examples](repo:HiCOLA/Parameter_files/Frontend_parameter_files/examples)
- [Backend parameter template](repo:HiCOLA/Parameter_files/Backend_parameter_files/Hi-COLA_params.lua)

For papers, citation guidance, licence, and team contact details, see the [project README](repo:README.md) and user manual. Keep model inputs, generated tables, backend parameters, logs, and the Git revision together so a simulation can be reproduced.

```{toctree}
:maxdepth: 2
:caption: Documentation

installation
quickstart
frontend
backend
outputs
troubleshooting
api/index
publishing
```
