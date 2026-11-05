"""Headless baseline/candidate overlays with signed differences in tolerance units.

Every lower panel shows (candidate - baseline) / (atol + rtol*|baseline|), so the
dotted lines at +/-1 are the limits applied by the summary comparison.
"""
import logging
from pathlib import Path
import re

import numpy as np
from compare import TOLERANCES

BASELINE_COLOR = '#2a78d6'
CANDIDATE_COLOR = '#eb6834'
EXCEEDED_COLOR = '#e34948'
INK = '#52514e'
QUANTITIES_PER_FIGURE = 6
DPI = 110
# Exactly reproduced checks have a ratio of zero, which a log axis cannot show.
OVERVIEW_FLOOR = 1e-3


def _pyplot():
    # Imported on first use so simulation-only runs do not need a plotting backend.
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    return plt


def tolerance_ratio(actual, reference, kind):
    """Return the signed difference in units of the comparison's allowance."""
    rtol, atol = TOLERANCES[kind]
    return (actual-reference)/(atol+rtol*np.abs(reference))


def worst_ratio(actual, reference, kind):
    """Return the largest |difference| / allowance; above 1 the comparison fails."""
    if actual.shape != reference.shape or actual.size == 0:
        raise ValueError(f'Cannot compare shapes {actual.shape} and {reference.shape}')
    return float(np.max(np.abs(tolerance_ratio(actual, reference, kind))))


def column_labels(path, columns):
    """Name table columns from a '#' header, keeping '(unit)' tokens with their name."""
    with Path(path).open() as stream:
        header = stream.readline()
    labels = []
    if header.startswith('#'):
        # Power spectrum headers end in a 'ShotnoiseSubtracted = true' flag.
        for token in re.sub(r'\S+\s*=.*$', '', header[1:]).split():
            if token.startswith('(') and labels:
                labels[-1] += f' {token}'
            else:
                labels.append(token)
    if len(labels) != columns:
        logging.debug('Using numbered columns for %s: header gave %s names for %s columns',
                      path, len(labels), columns)
        return [f'column {column}' for column in range(columns)]
    return labels


def axis_scale(values, prefer_log=False):
    """Choose log axes for quantities spanning two decades, or for any range if preferred."""
    values = np.asarray(values, dtype=float)
    magnitudes = np.abs(values[values != 0])
    if magnitudes.size == 0 or (not prefer_log and magnitudes.max()/magnitudes.min() < 100):
        return 'linear', {}
    if (values > 0).all():
        return 'log', {}
    return 'symlog', dict(linthresh=float(magnitudes.min()))


def _set_scale(setter, values, prefer_log=False):
    scale, options = axis_scale(values, prefer_log)
    setter(scale, **options)


def _difference_panel(axis, x, ratio, color=None):
    """Draw differences in tolerance units, always keeping the +/-1 limits in view."""
    worst = float(np.max(np.abs(ratio))) if ratio.size else 0.
    axis.plot(x, ratio, color=color or (EXCEEDED_COLOR if worst > 1 else INK), lw=1.5,
              marker='o' if len(x) <= 50 else None, ms=4)
    for limit in (-1, 1):
        axis.axhline(limit, color='black', ls=':', lw=1)
    axis.set_ylim(*(np.array([-1, 1])*max(1.25, 1.1*worst)))
    axis.set_ylabel('Δ / tolerance', fontsize='small')
    axis.grid(alpha=.25)
    return worst


def _overlay(axis, x, reference, actual):
    marker = 'o' if len(x) <= 50 else None
    axis.plot(x, reference, color=BASELINE_COLOR, lw=2, marker=marker, ms=4, label='baseline')
    axis.plot(x, actual, color=CANDIDATE_COLOR, lw=1.5, ls='--', label='candidate')
    axis.grid(alpha=.25)


def _quantity_title(label, worst):
    status = '  EXCEEDS TOLERANCE' if worst > 1 else ''
    return f'{label}   (max |Δ|/tol {worst:.3g}{status})'


def _page_path(path, page, pages):
    path = Path(path)
    return path if pages == 1 else path.with_name(f'{path.stem}_{page+1}of{pages}.png')


def table_plots(actual, reference, kind, title, path, labels=None):
    """Plot every column against the first, using as many figures as the table needs.

    The first column is only given a panel if it differs between revisions.
    Returns the paths of the figures written.
    """
    actual, reference = np.atleast_2d(actual), np.atleast_2d(reference)
    if actual.shape != reference.shape or actual.size == 0:
        raise ValueError(f'Cannot plot shapes {actual.shape} and {reference.shape}')
    columns = reference.shape[1]
    labels = labels or [f'column {column}' for column in range(columns)]
    tabular = columns > 1
    x = reference[:, 0] if tabular else np.arange(len(reference))
    quantities = list(range(1, columns)) if tabular else [0]
    if tabular and np.any(actual[:, 0] != reference[:, 0]):
        quantities.insert(0, 0)
    pages = int(np.ceil(len(quantities)/QUANTITIES_PER_FIGURE))
    plt = _pyplot()
    written = []
    for page in range(pages):
        chosen = quantities[page*QUANTITIES_PER_FIGURE:(page+1)*QUANTITIES_PER_FIGURE]
        rows = int(np.ceil(len(chosen)/2))
        cols = 2 if len(chosen) > 1 else 1
        figure, axes = plt.subplots(2*rows, cols, figsize=(6*cols, 1+3.6*rows), squeeze=False,
                                    height_ratios=[2, 1]*rows, sharex='col', constrained_layout=True)
        try:
            for position, column in enumerate(chosen):
                row, col = position//2, position % 2
                top, bottom = axes[2*row, col], axes[2*row+1, col]
                _overlay(top, x, reference[:, column], actual[:, column])
                # Power spectra are always read on log-log axes.
                _set_scale(top.set_xscale, x, kind == 'power')
                _set_scale(top.set_yscale, np.r_[reference[:, column], actual[:, column]], kind == 'power')
                worst = _difference_panel(bottom, x, tolerance_ratio(
                    actual[:, column], reference[:, column], kind))
                top.set_title(_quantity_title(labels[column], worst), fontsize='small')
                bottom.set_xlabel(labels[0] if tabular else 'row', fontsize='small')
            if len(chosen) % 2 and cols == 2:
                axes[-2, 1].axis('off')
                axes[-1, 1].axis('off')
            handles, names = axes[0, 0].get_legend_handles_labels()
            figure.legend(handles, names, loc='outside upper right', ncol=2, fontsize='small')
            figure.suptitle(f'{title}' + (f' ({page+1} of {pages})' if pages > 1 else ''))
            target = _page_path(path, page, pages)
            target.parent.mkdir(parents=True, exist_ok=True)
            figure.savefig(target, dpi=DPI)
            written.append(target)
        finally:
            plt.close(figure)
    return written


def power_evolution_plot(spectra, title, path):
    """Overlay P(k) at every output redshift; ``spectra`` maps file name to (candidate, baseline)."""
    def redshift(name):
        match = re.search(r'_z(\d+\.\d+)', name)
        return float(match[1]) if match else 0.
    names = sorted((name for name, pair in spectra.items() if pair[0].shape == pair[1].shape),
                   key=redshift, reverse=True)
    if not names:
        raise ValueError('No power spectra with matching shapes')
    plt = _pyplot()
    # Later epochs are darker, on one sequential hue.
    shades = plt.get_cmap('Blues')(np.linspace(.4, 1, len(names)))
    figure, (top, bottom) = plt.subplots(2, 1, figsize=(8, 7), sharex=True, height_ratios=[2, 1],
                                         constrained_layout=True)
    try:
        for name, shade in zip(names, shades):
            actual, reference = spectra[name]
            match = re.search(r'_z(\d+\.\d+)', name)
            label = f'z = {match[1]}' if match else name
            top.plot(reference[:, 0], reference[:, 1], color=shade, lw=2, label=label)
            top.plot(actual[:, 0], actual[:, 1], color=shade, lw=1, ls='--', marker='o', ms=3)
            bottom.plot(reference[:, 0], tolerance_ratio(actual[:, 1], reference[:, 1], 'power'),
                        color=shade, lw=1.5, marker='o', ms=3)
        everything = np.concatenate([spectra[name][index][:, 1] for name in names for index in (0, 1)])
        _set_scale(top.set_yscale, everything, prefer_log=True)
        _set_scale(top.set_xscale, np.concatenate([spectra[name][1][:, 0] for name in names]), prefer_log=True)
        ratio = np.concatenate([tolerance_ratio(spectra[name][0][:, 1], spectra[name][1][:, 1], 'power')
                                for name in names])
        worst = float(np.max(np.abs(ratio)))
        for limit in (-1, 1):
            bottom.axhline(limit, color='black', ls=':', lw=1)
        bottom.set_ylim(*(np.array([-1, 1])*max(1.25, 1.1*worst)))
        top.grid(alpha=.25)
        bottom.grid(alpha=.25)
        top.set_ylabel('P(k)  (Mpc/h)$^3$')
        top.set_title(f'{title}: solid baseline, dashed candidate', fontsize='medium')
        top.legend(fontsize='small', title='Output', loc='upper left', bbox_to_anchor=(1.01, 1))
        bottom.set_xlabel('k  (h/Mpc)')
        bottom.set_ylabel('ΔP / tolerance')
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        figure.savefig(path, dpi=DPI)
    finally:
        plt.close(figure)
    return Path(path)


def velocity_plot(actual, reference, title, path):
    """Compare mean velocity components and RMS speed from the z = 0 snapshot."""
    names = ('mean $v_x$', 'mean $v_y$', 'mean $v_z$', 'RMS speed')
    actual, reference = np.asarray(actual), np.asarray(reference)
    x = np.arange(len(names))
    plt = _pyplot()
    figure, (top, bottom) = plt.subplots(2, 1, figsize=(7, 5.5), sharex=True, height_ratios=[2, 1],
                                         constrained_layout=True)
    try:
        top.plot(x, reference, ls='none', marker='o', ms=9, color=BASELINE_COLOR, label='baseline')
        top.plot(x, actual, ls='none', marker='x', ms=9, mew=2, color=CANDIDATE_COLOR, label='candidate')
        # Linear axis: the means are consistent with zero next to the RMS speed.
        top.set_ylabel('km/s')
        top.grid(alpha=.25)
        top.legend(fontsize='small')
        worst = _difference_panel(bottom, x, tolerance_ratio(actual, reference, 'velocity_statistics'))
        top.set_title(_quantity_title(title, worst), fontsize='medium')
        bottom.set_xticks(x, names)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        figure.savefig(path, dpi=DPI)
    finally:
        plt.close(figure)
    return Path(path)


def overview_plot(checks, path):
    """Show how close each group of checks came to its tolerance, worst per group."""
    plt = _pyplot()
    names = list(checks)[::-1]
    values = np.array([checks[name] for name in names])
    figure, axis = plt.subplots(figsize=(8, 1.5+.26*len(names)), constrained_layout=True)
    try:
        exceeded = values > 1
        shown = np.maximum(values, OVERVIEW_FLOOR)
        y = np.arange(len(names))
        axis.scatter(shown[~exceeded], y[~exceeded], s=50, color=BASELINE_COLOR, label='within tolerance')
        if exceeded.any():
            axis.scatter(shown[exceeded], y[exceeded], s=60, marker='X', color=EXCEEDED_COLOR,
                         label='exceeds tolerance')
        axis.axvline(1, color='black', ls=':', lw=1)
        axis.set_xscale('log')
        axis.set_xlim(OVERVIEW_FLOOR/2, max(5, 2*float(shown.max())))
        axis.set_yticks(y, names, fontsize='small')
        axis.set_ylim(-1, len(names))
        axis.grid(axis='x', alpha=.25)
        axis.set_xlabel(f'worst |candidate − baseline| / tolerance (values below {OVERVIEW_FLOOR:g} '
                        'drawn at that value)')
        axis.set_title('Summary checks against their tolerances', fontsize='medium')
        axis.legend(fontsize='small', loc='lower right')
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        figure.savefig(path, dpi=DPI)
    finally:
        plt.close(figure)
    return Path(path)
