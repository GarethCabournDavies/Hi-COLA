# Citing Hi-COLA

If you use Hi-COLA in research, please cite the introduction paper:

Bill S. Wright, Ashim Sen Gupta, Tessa Baker, Georgios Valogiannis, and Bartolomeo Fiorini, **Hi-COLA: Fast, approximate simulations of structure formation in Horndeski gravity**, JCAP 03 (2023) 040. [Published paper](https://doi.org/10.1088/1475-7516/2023/03/040) · [Preprint](https://arxiv.org/abs/2209.01666).

```bibtex
@article{Wright2023HiCOLA,
  author = {Wright, Bill S. and Sen Gupta, Ashim and Baker, Tessa
            and Valogiannis, Georgios and Fiorini, Bartolomeo},
  title = {{Hi-COLA}: Fast, approximate simulations of structure formation
           in {Horndeski} gravity},
  journal = {Journal of Cosmology and Astroparticle Physics},
  year = {2023},
  volume = {2023},
  number = {03},
  pages = {040},
  doi = {10.1088/1475-7516/2023/03/040},
  eprint = {2209.01666},
  archivePrefix = {arXiv},
  primaryClass = {astro-ph.CO}
}
```

## K-mouflage simulations

For work using the K-mouflage extension, also cite Ashim Sen Gupta, Bartolomeo Fiorini, and Tessa Baker, **K-mouflage at high k: extending the reach of Hi-COLA**, JCAP 11 (2024) 052. [Published paper](https://doi.org/10.1088/1475-7516/2024/11/052) · [Preprint](https://arxiv.org/abs/2407.00855).

```bibtex
@article{SenGupta2024Kmouflage,
  author = {Sen Gupta, Ashim and Fiorini, Bartolomeo and Baker, Tessa},
  title = {{K-mouflage} at high {$k$}: extending the reach of {Hi-COLA}},
  journal = {Journal of Cosmology and Astroparticle Physics},
  year = {2024},
  volume = {2024},
  number = {11},
  pages = {052},
  doi = {10.1088/1475-7516/2024/11/052},
  eprint = {2407.00855},
  archivePrefix = {arXiv},
  primaryClass = {astro-ph.CO}
}
```

When discussing the published comparison with other approximate methods, cite [Matter Power Spectra in Modified Gravity: A Comparative Study of Approximations and N-Body Simulations](https://arxiv.org/abs/2406.13667) where relevant. Consult the methods papers and user manual for references appropriate to the algorithms and dependencies used in your analysis.

## Identify the software used

Alongside the paper citation, report the repository URL and exact Git revision or release tag used. Obtain the revision with:

```sh
git rev-parse HEAD
```

Record any local modifications, the Python environment, backend compiler and build flags, input parameters, and random seeds with your results. The package version `0.0.dev0` is a development placeholder and does not uniquely identify a checkout.

The root [CITATION.cff](CITATION.cff) supplies machine-readable metadata and enables GitHub's **Cite this repository** button when present on the default branch. Its preferred citation is the introduction paper; its DOI identifies that paper, rather than a software archive.
