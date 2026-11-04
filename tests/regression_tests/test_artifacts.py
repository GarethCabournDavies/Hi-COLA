"""Check that summary statistics are collected from a synthetic run folder."""
import json
from pathlib import Path
import struct
import tempfile
import unittest

import numpy as np
from artifacts import export_summary


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
            self.assertEqual(len(index['cases']['gr-np1']['plots']), 1)
            self.assertTrue(Path(index['cases']['gr-np1']['plots'][0]).is_file())
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


if __name__ == '__main__':
    unittest.main()
