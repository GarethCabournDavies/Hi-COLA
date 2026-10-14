# Tests

Install `requirements-test.txt`, then run the fast Python suite:

```sh
MPLBACKEND=Agg python -m unittest discover -s tests -v
```

The tests exercise Hi-COLA Python functions and real SciPy solver boundaries.
The scalar-field callback signatures and file-layout expectations follow the
integration baseline, rather than the older public branch. The existing
`G3_func(..., 'phi')` derivative defect remains an expected failure; the Hubble
closure test passes on this baseline.

See [regression/README.md](regression/README.md) for the separate fresh-checkout,
C++ build, end-to-end simulations, MPI and pre-migration numerical comparisons.
