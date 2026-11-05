"""Check that summary statistics are collected from a synthetic run folder."""
import json
from pathlib import Path
import struct
import tempfile
import unittest

import numpy as np
from artifacts import export_summary
from plots import axis_scale, column_labels, table_plots


def write_gadget(path, ids, positions, velocities):
    def record(payload):
        size = struct.pack('<I', len(payload))
        return size+payload+size
    header = bytearray(256)
    struct.pack_into('<6I', header, 0, len(ids), 0, 0, 0, 0, 0)
    struct.pack_into('<2d', header, 72, 1.0, 0.0)
    with open(path, 'wb') as stream:
        stream.write(record(bytes(header)))
        stream.write(record(positions.astype('<f4').tobytes()))
        stream.write(record(velocities.astype('<f4').tobytes()))
        stream.write(record(ids.astype('<u4').tobytes()))


class ExportTests(unittest.TestCase):
    def test_tables_statistics_and_plots_are_exported(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            k = np.logspace(-2, 0, 8)
            for label, scale in (('baseline', 1.0), ('candidate', 1.01)):
                output = work/label/'gr-np1'/'output'
                output.mkdir(parents=True)
                np.savetxt(output/'pofk_z0.000.txt', np.c_[k, scale*k**-1])
                np.savetxt(output/'gravitymodel_gr.txt', np.c_[k, k])
                (work/label/'frontend'/'kmouflage').mkdir(parents=True)
                np.savetxt(work/label/'frontend'/'kmouflage'/'km_expansion.txt', np.c_[k, k])
                ids = np.arange(16**3)
                velocities = np.tile([3.0, 0.0, 4.0], (len(ids), 1))
                write_gadget(output/'gadget_z0.000.0', ids, np.zeros((len(ids), 3)), velocities)
            index = export_summary(work, ['gr'], [1])
            out = work/'summary-artifacts'
            self.assertTrue((out/'baseline'/'gr-np1'/'pofk_z0.000.txt').is_file())
            self.assertTrue((out/'candidate'/'gr-np1'/'gravitymodel_gr.txt').is_file())
            self.assertTrue((out/'frontend'/'candidate'/'kmouflage'/'km_expansion.txt').is_file())
            plots = index['cases']['gr-np1']['plots']
            self.assertEqual(sorted(Path(plot).name for plot in plots), [
                'gravitymodel_gr.png', 'pofk_z0.000.png', 'power_evolution.png',
                'velocity_statistics.png'])
            for plot in plots+index['frontend']['plots']+[index['overview']]:
                self.assertTrue((out/plot).read_bytes().startswith(b'\x89PNG'), plot)
            self.assertEqual(index['frontend']['plots'], ['plots/frontend/kmouflage/km_expansion.png'])
            # The 1% power difference is 100 tolerance units and must still be plotted.
            self.assertGreater(index['checks']['gr-np1 / power spectra'], 1)
            self.assertEqual(index['checks']['gr-np1 / growth tables'], 0)
            self.assertIn('gr-np1 / power spectra', (out/'README.md').read_text())
            self.assertTrue((out/'README.md').is_file())
            json.loads((out/'statistics.json').read_text())
            stats = index['cases']['gr-np1']['velocity_statistics']['candidate']
            self.assertEqual(stats['particles'], 16**3)
            self.assertAlmostEqual(stats['mean_vx'], 3.0)
            self.assertAlmostEqual(stats['rms_speed'], 5.0)
            self.assertEqual(index['errors'], {})

    def test_missing_outputs_are_recorded_not_raised(self):
        with tempfile.TemporaryDirectory() as directory:
            index = export_summary(Path(directory), ['gr'], [1])
            self.assertIn('baseline/gr-np1', index['errors'])

    def test_mismatched_table_is_recorded_and_other_plots_continue(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            for label, rows in (('baseline', 4), ('candidate', 3)):
                output = work/label/'gr-np1'/'output'
                output.mkdir(parents=True)
                np.savetxt(output/'pofk_gr.txt', np.c_[np.arange(1., rows+1), np.ones(rows)])
                np.savetxt(output/'gravitymodel_gr.txt', np.c_[np.arange(1., 5.), np.ones(4)])
            index = export_summary(work, ['gr'], [1])
            self.assertIn('plot/gr-np1/pofk_gr.txt', index['errors'])
            self.assertEqual([Path(plot).name for plot in index['cases']['gr-np1']['plots']],
                             ['gravitymodel_gr.png'])


class PlotTests(unittest.TestCase):
    def test_every_column_is_plotted_across_as_many_figures_as_needed(self):
        with tempfile.TemporaryDirectory() as directory:
            table = np.c_[np.arange(1., 6.), np.ones((5, 13))]
            paths = table_plots(table, table, 'tables', 'title', Path(directory)/'table.png')
            self.assertEqual([path.name for path in paths],
                             [f'table_{page}of3.png' for page in (1, 2, 3)])
            self.assertTrue(all(path.is_file() for path in paths))

    def test_labels_come_from_output_headers(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'table.txt'
            path.write_text('# k  (h/Mpc)    P(k)  (Mpc/h)^3    P_linear(k)  (Mpc/h)^3     '
                            'P_NL(k)  ShotnoiseSubtracted = true\n1 2 3 4\n')
            self.assertEqual(column_labels(path, 4),
                             ['k (h/Mpc)', 'P(k) (Mpc/h)^3', 'P_linear(k) (Mpc/h)^3', 'P_NL(k)'])
            self.assertEqual(column_labels(path, 3), ['column 0', 'column 1', 'column 2'])

    def test_wide_ranges_use_log_axes(self):
        self.assertEqual(axis_scale([1e-2, 1e3])[0], 'log')
        self.assertEqual(axis_scale([1., 2.])[0], 'linear')
        self.assertEqual(axis_scale([1., 2.], prefer_log=True)[0], 'log')
        self.assertEqual(axis_scale([-1e-2, 1e3])[0], 'symlog')
        self.assertEqual(axis_scale([0., 0.])[0], 'linear')


if __name__ == '__main__':
    unittest.main()
