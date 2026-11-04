"""Collect the summary statistics compared by the regression job into one artifact folder.

The folder holds, for both baseline and candidate:
  - matter power spectra (pofk*.txt) and expansion/growth tables (gravitymodel_*)
    written by each case and MPI rank count;
  - frontend expansion/force tables for the modified-gravity models;
  - velocity statistics (mean v_x, v_y, v_z and RMS speed, km/s) from the z=0 snapshot;
plus P(k) comparison plots and an index (README.md, statistics.json).
"""
import json
import shutil
from pathlib import Path

import numpy as np
from compare import numeric, particles, velocity_statistics

LABELS = ('baseline', 'candidate')


def _copy_tables(source, destination):
    copied = []
    for path in sorted(source.rglob('*.txt')):
        target = destination/path.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        copied.append(str(target))
    return copied


def _plot_power(key, name, spectra, path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    figure, (top, bottom) = plt.subplots(2, 1, sharex=True, figsize=(6, 6),
                                         gridspec_kw=dict(height_ratios=(3, 1)))
    for label, data in spectra.items():
        top.loglog(data[:, 0], data[:, 1], label=label, ls='-' if label == 'baseline' else '--')
    top.set_ylabel('P(k)')
    top.set_title(f'{key}: {name}')
    top.legend()
    base, cand = spectra['baseline'], spectra['candidate']
    if base.shape == cand.shape:
        bottom.semilogx(base[:, 0], cand[:, 1]/base[:, 1]-1)
    bottom.axhline(0, color='k', lw=0.5)
    bottom.set_xlabel('k')
    bottom.set_ylabel('cand/base - 1')
    figure.tight_layout()
    figure.savefig(path, dpi=120)
    plt.close(figure)


def export_summary(work, cases, ranks, destination=None):
    """Write summary statistics for every case into ``work/summary-artifacts``.

    Missing outputs are recorded rather than raised, so the export never masks
    the pass/fail result of the comparison itself.
    """
    work = Path(work)
    out = Path(destination or work/'summary-artifacts')
    out.mkdir(parents=True, exist_ok=True)
    index = dict(cases={}, frontend={}, errors={})

    for label in LABELS:
        frontend = work/label/'frontend'
        if frontend.is_dir():
            index['frontend'][label] = _copy_tables(frontend, out/'frontend'/label)

    for n in ranks:
        for case in cases:
            key = f'{case}-np{n}'
            entry = index['cases'][key] = dict(tables={}, velocity_statistics={}, plots=[])
            spectra = {}
            for label in LABELS:
                output = work/label/key/'output'
                try:
                    entry['tables'][label] = _copy_tables(output, out/label/key)
                    for path in sorted(output.rglob('pofk*txt')):
                        spectra.setdefault(str(path.relative_to(output)), {})[label] = numeric(path)
                    snapshots = sorted(output.rglob('gadget_z0.000.*'))
                    _, _, velocities = particles(snapshots)
                    mean_x, mean_y, mean_z, rms = velocity_statistics(velocities)
                    entry['velocity_statistics'][label] = dict(
                        particles=len(velocities), mean_vx=float(mean_x), mean_vy=float(mean_y),
                        mean_vz=float(mean_z), rms_speed=float(rms))
                except Exception as error:
                    index['errors'][f'{label}/{key}'] = f'{type(error).__name__}: {error}'
            for name, pair in spectra.items():
                if set(pair) != set(LABELS):
                    continue
                plot = out/'plots'/f"{key}_{name.replace('/', '_').removesuffix('.txt')}.png"
                plot.parent.mkdir(parents=True, exist_ok=True)
                try:
                    _plot_power(key, name, pair, plot)
                    entry['plots'].append(str(plot))
                except Exception as error:
                    index['errors'][f'plot/{key}/{name}'] = f'{type(error).__name__}: {error}'

    (out/'statistics.json').write_text(json.dumps(index, indent=2)+'\n')
    (out/'README.md').write_text(_readme(index, out))
    return index


def _readme(index, out):
    lines = ['# Regression summary statistics', '',
             'Baseline and candidate outputs used by the `summary` comparison. '
             'Per-comparison errors and tolerances are in `summary-report.json`.', '',
             '## Velocity statistics at z = 0 (km/s)', '',
             '| Case | Revision | N | mean v_x | mean v_y | mean v_z | RMS speed |',
             '|---|---|---|---|---|---|---|']
    for key, entry in index['cases'].items():
        for label, s in entry['velocity_statistics'].items():
            lines.append(f"| {key} | {label} | {s['particles']} | {s['mean_vx']:.6g} | "
                         f"{s['mean_vy']:.6g} | {s['mean_vz']:.6g} | {s['rms_speed']:.6g} |")
    lines += ['', '## Contents', '',
              '- `baseline/<case>-np<ranks>/`, `candidate/<case>-np<ranks>/`: power spectra and expansion/growth tables',
              '- `frontend/<revision>/<model>/`: frontend expansion and force tables',
              '- `plots/`: P(k) for both revisions and the fractional difference',
              '- `statistics.json`: machine-readable index of the above']
    if index['errors']:
        lines += ['', '## Missing or unreadable outputs', '']
        lines += [f'- `{k}`: {v}' for k, v in index['errors'].items()]
    return '\n'.join(lines)+'\n'
