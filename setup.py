from setuptools import setup, find_packages
setup(
    name = 'Hi_COLA',
    packages = find_packages(
    ),
    extras_require = {
        # Test-only dependencies (installed via `pip install -e '.[tests]'`).
        # Ranges are chosen so CI resolves to the same major generation as a
        # modern local environment; relax or tighten together if that drifts.
        'tests': [
            # Core numerical stack. >=1.26 is the floor pandas 2.x/3.x and
            # scipy 1.11+ build against
            'numpy>=1.26',
            # Used for integrals/ODEs (scipy.integrate.solve_ivp etc.).
            # >=1.11 matches the numpy floor
            'scipy>=1.11',
            # Symbolic algebra (sympy.lambdify)
            'sympy>=1.12',
            # Plotting for diagnostics; >=3.8 is a stable modern floor,
            'matplotlib>=3.8',
            # INI-style config parsing (configobj.ConfigObj). 5.x is the current
            # stable line
            'configobj>=5.0',
            # Only imported in support.py for read_csv/concat; >=2.0 allows both
            # pandas 2.x and 3.x so it tracks the numpy 2.x line above.
            'pandas>=2.0',
            # Test coverage reporting (coverage run -m unittest). >=7.6 is a
            # stable modern floor.
            'coverage>=7.6',
        ],
    },
)
