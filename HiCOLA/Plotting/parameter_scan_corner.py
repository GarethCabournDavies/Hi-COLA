"""hicola_plot_parameter_scan_corner: a corner plot of a Hi-COLA parameter scan's viability categories.

Reads the same scanner output as hicola_plot_parameter_scan and shows every pair of
the chosen quantities, with points coloured by the viability criterion they failed
(or as viable). The diagonal panels are histograms of each quantity, stacked by category.
"""
import logging
import sys

import numpy as np

from HiCOLA.Plotting import common
from HiCOLA.Plotting.parameter_scan import (add_scan_arguments, axis_label, bin_edges, check_quantities,
                                            draw_cells, load, points, varying)

# A derived quantity replaces the scanned one it is computed from in the default selection
DERIVED_FROM = {'E_dS': 'Hubble0', 'f_phi': 'Omega_l0'}


def default_quantities(tables):
    """Varying quantities, without scanned ones whose derived equivalent is also shown."""
    found = varying(tables)
    return [name for name in found if name not in {DERIVED_FROM[d] for d in DERIVED_FROM if d in found}]


def main(argv=None):
    tool = common.parser(__doc__.splitlines()[0], 'Scanner output folder containing <scan>_<category>s.txt files')
    add_scan_arguments(tool)
    tool.add_argument('--params', nargs='+', metavar='QUANTITY',
                      help='Quantities to plot (column names from the scan files, E_dS or f_phi); '
                           'default: every quantity that varies across the scan, using E_dS and f_phi '
                           'in place of Hubble0 and Omega_l0')
    args = common.parse(tool, argv)
    name, tables = load(tool, args)
    names = args.params or default_quantities(tables)
    check_quantities(tool, tables, names)
    if len(names) < 2:
        tool.error(f'A corner plot needs at least two varying quantities; found {names}. '
                   'Use hicola_plot_parameter_scan for a single pair, or choose them with --params')
    logging.debug('Corner plot quantities: %s', names)

    count = len(names)
    with common.style() as plt:
        size = max(2.2*count, 5)
        figure, axes = plt.subplots(count, count, figsize=(size+2.5, size), squeeze=False)
        total = 0
        for row in range(count):
            for column in range(count):
                axis = axes[row][column]
                if column > row:
                    axis.set_visible(False)
                    continue
                if row == column:
                    # Diagonal: histogram of one quantity, stacked by category on shared bins
                    found = [(meaning, color, values[np.isfinite(values)])
                             for _, meaning, color, (values,) in points(tables, names[row])]
                    finite = np.concatenate([values for *_, values in found]) if found else np.array([])
                    if finite.size:
                        bins = bin_edges(finite)
                        axis.hist([values for *_, values in found], bins=bins, stacked=True,
                                  color=[color for _, color, _ in found], histtype='stepfilled')
                    axis.set_yticks([])
                else:
                    shown = draw_cells(axis, tables, names[column], names[row])
                    if (row, column) == (1, 0):
                        total = shown
                    axis.set_ylabel(axis_label(names[row]) if column == 0 else '')
                    if column:
                        axis.tick_params(labelleft=False)
                axis.set_xlabel(axis_label(names[column]) if row == count-1 else '')
                if row < count-1:
                    axis.tick_params(labelbottom=False)
        # Share x limits down each column so the diagonal histograms line up with the scatter panels
        for column in range(count-1):
            axes[column][column].set_xlim(axes[count-1][column].get_xlim())
        figure.legend(*axes[1][0].get_legend_handles_labels(), loc='upper right', title='Category')
        figure.suptitle(f'{args.label}: parameter scan ({total} points)')
        common.save(figure, args, 'parameter_scan_corner')
        plt.close(figure)
    return 0


if __name__ == '__main__':
    sys.exit(main())
