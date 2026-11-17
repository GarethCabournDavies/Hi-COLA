"""Build GitHub Actions matrices from .github/ci-matrix.json.

The configuration lists required and optional Python versions and operating
systems. Each matrix entry carries a ``required`` flag: jobs set
``continue-on-error`` for optional entries, so gate jobs fail only when a
required entry fails.
"""
import argparse
import json
import logging
import os
from pathlib import Path

CONFIG = Path(__file__).resolve().parents[1] / 'ci-matrix.json'


def entries(values):
    """Return (value, required) pairs, required values first."""
    return ([(v, True) for v in values['required']]
            + [(v, False) for v in values['optional']])


def build_matrix(config, os_mode):
    """Return a matrix include list for the given operating-system mode.

    ``primary`` uses only the first required OS; ``all`` crosses every OS
    with every Python version. The first required Python version on the
    primary OS is flagged ``primary`` for single-run steps such as coverage
    upload.
    """
    systems = entries(config['os'])
    if os_mode == 'primary':
        systems = systems[:1]
    include = []
    for os_name, os_required in systems:
        for version, py_required in entries(config['python']):
            include.append({
                'os': os_name,
                'python-version': version,
                'required': os_required and py_required,
                'primary': not include,
            })
    logging.debug('Matrix (%s): %s', os_mode, include)
    return {'include': include}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--os-mode', choices=['primary', 'all'], default='primary')
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG)
    matrix = json.dumps(build_matrix(json.loads(CONFIG.read_text()), args.os_mode))
    output = os.environ.get('GITHUB_OUTPUT')
    if output:
        with open(output, 'a', encoding='utf-8') as stream:
            stream.write(f'matrix={matrix}\n')
    print(matrix)


if __name__ == '__main__':
    main()
