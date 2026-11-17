"""Check packaging metadata against the CI test matrix.

The required Python versions in .github/ci-matrix.json are the supported
versions: they must match the pyproject.toml version classifiers, and the
oldest must match the requires-python lower bound.
"""
import json
import logging
import unittest
from pathlib import Path

try:
    import tomllib
except ImportError:  # Python 3.10 has no tomllib.
    tomllib = None

ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'Programming Language :: Python :: '


def version_key(version):
    return tuple(int(part) for part in version.split('.'))


@unittest.skipIf(tomllib is None, 'tomllib requires Python 3.11 or later')
class TestCIMatrixMetadata(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(ROOT / 'pyproject.toml', 'rb') as stream:
            cls.project = tomllib.load(stream)['project']
        matrix = json.loads((ROOT / '.github' / 'ci-matrix.json').read_text())
        cls.required = sorted(matrix['python']['required'], key=version_key)
        logging.debug('Required Python versions: %s', cls.required)

    def test_classifiers_match_required_versions(self):
        classified = sorted(
            (c[len(PREFIX):] for c in self.project['classifiers']
             if c.startswith(PREFIX) and c[len(PREFIX):].startswith('3.')),
            key=version_key)
        self.assertEqual(classified, self.required)

    def test_requires_python_matches_oldest_required(self):
        self.assertEqual(self.project['requires-python'], f'>={self.required[0]}')


if __name__ == '__main__':
    unittest.main()
