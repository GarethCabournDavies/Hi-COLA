"""Collect the summary statistics compared by the regression job into one artifact folder.

The folder holds, for both baseline and candidate:
  - matter power spectra (pofk*.txt) and expansion/growth tables (gravitymodel_*, cosmology_*)
    written by each case and MPI rank count;
  - frontend expansion/force tables for the modified-gravity models;
  - velocity statistics (mean v_x, v_y, v_z and RMS speed, km/s) from the z=0 snapshot;
plus comparison plots of all of the above and an index (README.md, statistics.json).
"""
import json
import logging
from pathlib import Path
import shutil

import numpy as np
from compare import numeric, particles, velocity_statistics
from plots import (column_labels, overview_plot, power_evolution_plot, table_plots,
                   velocity_plot, worst_ratio)

LABELS = ('baseline', 'candidate')
GROUPS = (('pofk', 'power spectra'), ('gravitymodel', 'growth tables'), ('cosmology', 'expansion table'))
WORST_LISTED = 10
# The frontend writes no header for this table; its columns are fixed by the writer.
FRONTEND_EXPANSION_LABELS = ['a', 'E', "E'/E"]


def _copy_tables(source, destination):
    copied = []
    for path in sorted(source.rglob('*.txt')):
        target = destination/path.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        copied.append(target)
    return copied


def _group(name):
    for prefix, group in GROUPS:
        if name.startswith(prefix):
            return group
    return 'other tables'


class _Export:
    """Accumulate plots, tolerance ratios and recorded errors for one export."""

    def __init__(self, out):
        self.out = out
        self.index = dict(cases={}, frontend={}, checks={}, errors={}, overview=None)

    def relative(self, paths):
        return [str(Path(path).relative_to(self.out)) for path in paths]

    def attempt(self, key, action):
        # A problem with one output is recorded and must not stop the remaining plots.
        try:
            return action()
        except Exception as error:
            logging.debug('Summary export problem for %s', key, exc_info=True)
            self.index['errors'][key] = f'{type(error).__name__}: {error}'
            return None

    def plot_table(self, key, group_key, candidate_path, baseline_path, kind, target, labels=None):
        """Plot one table pair, returning the (candidate, baseline) arrays when readable."""
        actual, reference = numeric(candidate_path), numeric(baseline_path)
        ratio = worst_ratio(actual, reference, kind)
        self.index['checks'][group_key] = max(ratio, self.index['checks'].get(group_key, 0.))
        labels = labels or column_labels(baseline_path, reference.shape[1])
        return (actual, reference), table_plots(actual, reference, kind, key, target, labels)


def export_summary(work, cases, ranks, destination=None):
    """Write summary statistics and plots for every case into ``work/summary-artifacts``.

    Missing outputs are recorded rather than raised, so the export never masks
    the pass/fail result of the comparison itself.
    """
    work = Path(work)
    out = Path(destination or work/'summary-artifacts')
    out.mkdir(parents=True, exist_ok=True)
    export = _Export(out)
    index = export.index

    for label in LABELS:
        frontend = work/label/'frontend'
        if frontend.is_dir():
            index['frontend'][label] = export.relative(_copy_tables(frontend, out/'frontend'/label))
    index['frontend']['plots'] = _frontend_plots(work, out, export)

    for n in ranks:
        for case in cases:
            _case_export(work, out, export, f'{case}-np{n}')

    if index['checks']:
        export.attempt('plot/overview', lambda: index.update(
            overview=str(overview_plot(index['checks'], out/'plots'/'overview.png').relative_to(out))))
    (out/'statistics.json').write_text(json.dumps(index, indent=2)+'\n')
    (out/'README.md').write_text(_readme(index))
    return index


def _frontend_plots(work, out, export):
    baseline, candidate = work/'baseline'/'frontend', work/'candidate'/'frontend'
    plots = []
    for reference in sorted(baseline.rglob('*.txt')) if baseline.is_dir() else ():
        name = reference.relative_to(baseline)
        labels = FRONTEND_EXPANSION_LABELS if reference.stem.endswith('_expansion') else None
        result = export.attempt(f'plot/frontend/{name}', lambda: export.plot_table(
            f'frontend/{name}', f'frontend / {name.parts[0]}', candidate/name, reference, 'tables',
            out/'plots'/'frontend'/name.with_suffix('.png'), labels))
        if result:
            plots += export.relative(result[1])
    return plots


def _case_export(work, out, export, key):
    index = export.index
    entry = index['cases'][key] = dict(tables={}, velocity_statistics={}, plots=[])
    velocities = {}
    for label in LABELS:
        output = work/label/key/'output'

        def collect(label=label, output=output):
            entry['tables'][label] = export.relative(_copy_tables(output, out/label/key))
            _, _, values = particles(sorted(output.rglob('gadget_z0.000.*')))
            velocities[label] = velocity_statistics(values)
            mean_x, mean_y, mean_z, rms = velocities[label]
            entry['velocity_statistics'][label] = dict(
                particles=len(values), mean_vx=float(mean_x), mean_vy=float(mean_y),
                mean_vz=float(mean_z), rms_speed=float(rms))
        export.attempt(f'{label}/{key}', collect)

    baseline, candidate = work/'baseline'/key/'output', work/'candidate'/key/'output'
    spectra = {}
    for reference in sorted(baseline.rglob('*.txt')) if baseline.is_dir() else ():
        name = reference.relative_to(baseline)
        kind = 'power' if 'pofk' in reference.name else 'tables'
        result = export.attempt(f'plot/{key}/{name}', lambda: export.plot_table(
            f'{key}: {name}', f'{key} / {_group(reference.name)}', candidate/name, reference, kind,
            out/'plots'/key/name.with_suffix('.png')))
        if result:
            entry['plots'] += export.relative(result[1])
            # Snapshot folders repeat the z = 0 spectrum, so only top-level files give the evolution.
            if kind == 'power' and name.parent == Path('.'):
                spectra[str(name)] = result[0]

    plots = out/'plots'/key
    if spectra:
        path = export.attempt(f'plot/{key}/power_evolution', lambda: power_evolution_plot(
            spectra, key, plots/'power_evolution.png'))
        if path:
            entry['plots'] += export.relative([path])
    if set(velocities) == set(LABELS):
        path = export.attempt(f'plot/{key}/velocity_statistics', lambda: _velocity(
            export, key, velocities, plots/'velocity_statistics.png'))
        if path:
            entry['plots'] += export.relative([path])


def _velocity(export, key, velocities, path):
    actual, reference = velocities['candidate'], velocities['baseline']
    export.index['checks'][f'{key} / velocity statistics'] = worst_ratio(
        np.asarray(actual), np.asarray(reference), 'velocity_statistics')
    return velocity_plot(actual, reference, f'{key}: velocity statistics at z = 0', path)


def _readme(index):
    plot_count = sum(len(entry['plots']) for entry in index['cases'].values())+len(index['frontend'].get('plots', []))
    lines = ['# Regression summary statistics', '',
             'Baseline and candidate outputs used by the `summary` comparison. '
             'Per-comparison errors and tolerances are in `summary-report.json`.', '']
    if index['checks']:
        worst = sorted(index['checks'].items(), key=lambda item: -item[1])[:WORST_LISTED]
        lines += ['## Checks closest to their tolerance', '',
                  '`max |Δ| / tolerance`: values above 1 fail the comparison. '
                  f"The artifact's `{index['overview'] or 'plots/'}` shows every check.", '',
                  '| Check | max \\|Δ\\| / tolerance |', '|---|---|']
        lines += [f'| {name} | {value:.3g} |' for name, value in worst]
        lines.append('')
    lines += ['## Velocity statistics at z = 0 (km/s)', '',
              '| Case | Revision | N | mean v_x | mean v_y | mean v_z | RMS speed |',
              '|---|---|---|---|---|---|---|']
    for key, entry in index['cases'].items():
        for label, s in entry['velocity_statistics'].items():
            lines.append(f"| {key} | {label} | {s['particles']} | {s['mean_vx']:.6g} | "
                         f"{s['mean_vy']:.6g} | {s['mean_vz']:.6g} | {s['rms_speed']:.6g} |")
    lines += ['', '## Contents', '',
              f'- `plots/` ({plot_count} case and frontend figures, plus the overview):',
              '  - `overview.png`: every group of checks against its tolerance',
              '  - `<case>-np<ranks>/power_evolution.png`: P(k) at every output redshift',
              '  - `<case>-np<ranks>/velocity_statistics.png`: mean velocities and RMS speed',
              '  - `<case>-np<ranks>/<table>.png`: every column of every output table; large tables span several figures',
              '  - `frontend/<model>/<table>.png`: every column of the frontend tables',
              '- `baseline/<case>-np<ranks>/`, `candidate/<case>-np<ranks>/`: power spectra and expansion/growth tables',
              '- `frontend/<revision>/<model>/`: frontend expansion and force tables',
              '- `statistics.json`: machine-readable index of the above']
    if index['errors']:
        lines += ['', '## Missing or unreadable outputs', '']
        lines += [f'- `{k}`: {v}' for k, v in index['errors'].items()]
    return '\n'.join(lines)+'\n'
