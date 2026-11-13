"""Run hicola_plot_parameter_scan on scan files written in the parameter scanner's format."""
import contextlib
import io
from pathlib import Path
import tempfile
import unittest

import numpy as np

from HiCOLA.Plotting import parameter_scan

SPACES = '          '
COLUMNS = ('Hubble0', 'Scalar0', 'Scalarprime0', 'Omega_r0', 'Omega_m0', 'Omega_l0', 'fsolve_ier')


def write_scan(folder, prefix, points, symbols=('k_1', 'k_2', 'g_31', 'g_32')):
    """Write category files as parameter_scanner.py does: header, blank line, list reprs."""
    folder.mkdir(parents=True, exist_ok=True)
    for category in parameter_scan.CATEGORIES:
        with open(folder/f'{prefix}_{category}.txt', 'a') as stream:
            print('# '+SPACES.join(COLUMNS), end=SPACES, file=stream)
            for symbol in symbols:
                print(symbol, end=SPACES, file=stream)
            if category == 'reds':
                print('max[Omega_DE]', end=SPACES, file=stream)
            print('\n', file=stream)
            for point in points.get(category, ()):
                stream.write(str(point)+'\n')


def point(k1, g31, extra=()):
    # numpy 2 values print as np.float64(...) inside the scanner's list reprs.
    return [np.float64(1.232), 1.0, 50.0, 8e-5, 0.28, 0.6, 1, np.float64(k1), -0.29, np.float64(g31), 1.04, *extra]


def run(*argv):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return parameter_scan.main([str(value) for value in argv])


class ParameterScanTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.points = {'greens': [point(-0.2, -1.0), point(-0.1, -1.5)],
                       'blacks': [point(0.1, 0.5)],
                       'reds': [point(-0.3, -2.0, extra=(0.9,))],
                       'greys': [[float('nan')]*11]}
        write_scan(self.root/'scans', '2026-01-01_10-00-00_test', self.points)

    def test_categories_are_read_with_header_names(self):
        tables = {category: parameter_scan.read_category(path) for category, path in
                  parameter_scan.scans(self.root/'scans')['2026-01-01_10-00-00_test'].items()}
        self.assertEqual(len(tables['greens']['k_1']), 2)
        np.testing.assert_allclose(tables['greens']['g_31'], [-1.0, -1.5])
        np.testing.assert_allclose(tables['reds']['max[Omega_DE]'], [0.9])
        np.testing.assert_allclose(tables['greens']['E_dS'], 1/1.232)
        np.testing.assert_allclose(tables['greens']['f_phi'], 1-0.6/(1-0.28-8e-5))
        self.assertEqual(len(tables['magentas']['k_1']), 0)

    def test_default_axes_are_the_varying_parameters(self):
        tables = {category: parameter_scan.read_category(path) for category, path in
                  parameter_scan.scans(self.root/'scans')['2026-01-01_10-00-00_test'].items()}
        self.assertEqual(parameter_scan.default_axes(tables), ['k_1', 'g_31'])

    def test_figure_with_default_and_chosen_axes(self):
        self.assertEqual(run(self.root/'scans'), 0)
        self.assertTrue((self.root/'scans'/'plots'/'parameter_scan.png').read_bytes().startswith(b'\x89PNG'))
        run(self.root/'scans', '--x', 'f_phi', '--y', 'E_dS', '--format', 'pdf', '--out', self.root/'out')
        self.assertTrue((self.root/'out'/'parameter_scan.pdf').is_file())

    def test_latest_scan_is_the_default_and_others_can_be_chosen(self):
        write_scan(self.root/'scans', '2026-02-01_10-00-00_test', {'greens': [point(0.0, 0.0)]})
        self.assertEqual(sorted(parameter_scan.scans(self.root/'scans')),
                         ['2026-01-01_10-00-00_test', '2026-02-01_10-00-00_test'])
        run(self.root/'scans', '--scan', '2026-01-01_10-00-00_test', '--out', self.root/'chosen')
        self.assertTrue((self.root/'chosen'/'parameter_scan.png').is_file())

    def test_file_without_header_is_skipped(self):
        # A scan stopped before its header writes were flushed leaves empty category files
        (self.root/'scans'/'2026-01-01_10-00-00_test_blacks.txt').write_text('')
        (self.root/'scans'/'2026-01-01_10-00-00_test_greens.txt').write_text('')
        with self.assertLogs(level='WARNING'):
            self.assertEqual(run(self.root/'scans', '--out', self.root/'partial'), 0)
        self.assertTrue((self.root/'partial'/'parameter_scan.png').is_file())

    def test_bins_follow_a_grid(self):
        np.testing.assert_allclose(parameter_scan.bin_edges(np.array([0., 1., 2., 1.])), [-.5, .5, 1.5, 2.5])
        self.assertEqual(len(parameter_scan.bin_edges(np.linspace(0, 1, 500))), parameter_scan.BINS+1)

    def test_cells_tile_the_plane_and_show_the_most_viable_category(self):
        import matplotlib
        matplotlib.use('Agg')
        from matplotlib import pyplot
        tables = {'blacks': {'a': np.array([0., 1.]), 'b': np.array([0., 0.])},
                  'greens': {'a': np.array([0., 2.]), 'b': np.array([0., 1.])}}
        figure, axis = pyplot.subplots()
        self.assertEqual(parameter_scan.draw_cells(axis, tables, 'a', 'b'), 4)
        self.assertEqual(len(axis.patches), 4)
        # The shared (0, 0) cell is drawn black first and green later, so green is on top
        at_origin = [patch.get_facecolor()[:3] for patch in axis.patches
                     if (patch.get_x(), patch.get_y()) == (-.5, -.5)]
        self.assertEqual(at_origin, [(0., 0., 0.), matplotlib.colors.to_rgb('tab:green')])
        self.assertEqual(axis.get_xlim(), (-.5, 2.5))
        pyplot.close(figure)

    def test_axis_labels_are_typeset(self):
        self.assertEqual(parameter_scan.axis_label('g_31'), '$g_{31}$')
        self.assertEqual(parameter_scan.axis_label('k_1'), '$k_{1}$')
        self.assertEqual(parameter_scan.axis_label('f_phi'), '$f_\\phi$')
        self.assertEqual(parameter_scan.axis_label('max[Omega_DE]'), 'max[Omega_DE]')

    def test_errors(self):
        (self.root/'empty').mkdir()
        for argv in ([self.root/'empty'], [self.root/'scans', '--x', 'unknown'],
                     [self.root/'scans', '--scan', 'missing'],
                     [self.root/'scans', '--reference', self.root/'scans']):
            with self.subTest(argv=argv), self.assertRaises(SystemExit):
                run(*argv)


if __name__ == '__main__':
    unittest.main()
