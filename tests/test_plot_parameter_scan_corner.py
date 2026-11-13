"""Run hicola_plot_parameter_scan_corner on scan files written in the parameter scanner's format."""
import contextlib
import io
from pathlib import Path
import tempfile
import unittest

import numpy as np

from HiCOLA.Plotting import parameter_scan, parameter_scan_corner
from tests.test_plot_parameter_scan import point, write_scan


def run(*argv):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return parameter_scan_corner.main([str(value) for value in argv])


class ParameterScanCornerTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        write_scan(self.root/'scans', '2026-01-01_10-00-00_test',
                   {'greens': [point(-0.2, -1.0), point(-0.1, -1.5)], 'blacks': [point(0.1, 0.5)],
                    'reds': [point(-0.3, -2.0, extra=(0.9,))], 'greys': [[float('nan')]*11]})

    def tables(self):
        found = parameter_scan.scans(self.root/'scans')['2026-01-01_10-00-00_test']
        return {category: parameter_scan.read_category(path) for category, path in found.items()}

    def test_default_quantities_skip_duplicated_scan_columns(self):
        tables = self.tables()
        for table in tables.values():
            if len(table['Hubble0']):
                table['Hubble0'] = table['Hubble0']*np.linspace(1, 2, len(table['Hubble0']))
                table['E_dS'] = 1/table['Hubble0']
        names = parameter_scan_corner.default_quantities(tables)
        self.assertEqual(names[:2], ['k_1', 'g_31'])
        self.assertIn('E_dS', names)
        self.assertNotIn('Hubble0', names)

    def test_figure_with_default_and_chosen_quantities(self):
        self.assertEqual(run(self.root/'scans'), 0)
        self.assertTrue((self.root/'scans'/'plots'/'parameter_scan_corner.png').read_bytes().startswith(b'\x89PNG'))
        run(self.root/'scans', '--params', 'k_1', 'g_31', 'f_phi', '--format', 'pdf', '--out', self.root/'out')
        self.assertTrue((self.root/'out'/'parameter_scan_corner.pdf').is_file())

    def test_errors(self):
        for argv in ([self.root/'scans', '--params', 'k_1'], [self.root/'scans', '--params', 'k_1', 'unknown'],
                     [self.root/'scans', '--reference', self.root/'scans']):
            with self.subTest(argv=argv), self.assertRaises(SystemExit):
                run(*argv)


if __name__ == '__main__':
    unittest.main()
