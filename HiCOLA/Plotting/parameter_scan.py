"""hicola_plot_parameter_scan: the viability categories of a Hi-COLA parameter scan.

Reads the <date>_<model>_<category>s.txt files written by the parameter scanner
(HiCOLA/Utilities/Scanner/parameter_scanner.py) and plots each scanned point in two
chosen quantities, coloured by the viability criterion it failed (or as viable).
Besides the scanned columns, E_dS = 1/Hubble0 and f_phi = 1 - Omega_l0/Omega_DE0
are available as axes; these give the (f_phi, E_dS) map of the Hi-COLA paper.
"""
import logging
import re
import sys

import numpy as np

from HiCOLA.Plotting import common

# Scanner file category -> (meaning, colour), in the order the scanner tests them;
# a point is filed under the first criterion it fails.
CATEGORIES = {
    'blacks': ('density fraction outside [0, 1]', 'black'),
    'greys': ('numerical failure', 'tab:gray'),
    'yellows': ('negative alpha factor', 'tab:olive'),
    'blues': ('tracker condition violated', 'tab:cyan'),
    'pinks': ('early dark energy', 'tab:pink'),
    'reds': ('dark energy peaks before today', 'tab:red'),
    'magentas': ('no matter domination', 'tab:purple'),
    'greens': ('viable', 'tab:green'),
}
FILE = re.compile(r'^(?P<scan>.+)_(?P<category>' + '|'.join(CATEGORIES) + r')\.txt$')
# numpy 2 writes values as np.float64(...) inside the scanner's list reprs.
WRAPPED = re.compile(r'np\.\w+\(([^()]*)\)')
DERIVED = ('E_dS', 'f_phi')
LABELS = {'E_dS': '$E_{\\rm dS}$', 'f_phi': '$f_\\phi$', 'Hubble0': '$H_0$ (code units)',
          'Scalar0': '$\\phi_0$', 'Scalarprime0': "$\\phi'_0$", 'Omega_r0': '$\\Omega_{r0}$',
          'Omega_m0': '$\\Omega_{m0}$', 'Omega_l0': '$\\Omega_{\\Lambda 0}$'}


def axis_label(name):
    """Typeset a scan column name, for example g_31 as $g_{31}$."""
    if name in LABELS:
        return LABELS[name]
    match = re.fullmatch(r'([A-Za-z]+)_\{?(\w+?)\}?', name)
    return f'${match[1]}_{{{match[2]}}}$' if match else name


def scans(folder):
    """Map each scan (file-name prefix) in ``folder`` to its category files."""
    found = {}
    for path in sorted(folder.glob('*.txt')):
        match = FILE.match(path.name)
        if match:
            found.setdefault(match['scan'], {})[match['category']] = path
    return found


def read_category(path):
    """Read one category file: a '#' header naming columns, then one list repr per point."""
    with open(path) as stream:
        header = stream.readline()
        rows = []
        for line in stream:
            line = WRAPPED.sub(r'\1', line.strip())
            if line.startswith('[') and line.endswith(']'):
                rows.append([float(value) for value in line[1:-1].split(',')])
    names = header.lstrip('#').split()
    if not names:
        logging.warning('Skipping %s: it has no column header', path)
        return {}
    data = np.array(rows, dtype=float).reshape(-1, len(rows[0]) if rows else len(names))
    table = {name: data[:, column] for column, name in enumerate(names[:data.shape[1]])}
    if {'Hubble0', 'Omega_l0', 'Omega_m0', 'Omega_r0'} <= set(table):
        with np.errstate(divide='ignore', invalid='ignore'):
            table['E_dS'] = 1/table['Hubble0']
            table['f_phi'] = 1-table['Omega_l0']/(1-table['Omega_m0']-table['Omega_r0'])
    return table


def candidates(tables):
    """Quantities that can be plotted, model parameters first, then derived and cosmological ones."""
    # Column names from every category, since an unreadable file gives an empty table
    names = list(dict.fromkeys(name for table in tables.values() for name in table))
    parameters = names[names.index('fsolve_ier')+1:] if 'fsolve_ier' in names else names
    found = [name for name in parameters if not name.startswith('max[') and name not in DERIVED]
    found += [*DERIVED, 'Omega_m0', 'Omega_r0', 'Omega_l0', 'Scalarprime0', 'Scalar0', 'Hubble0']
    return [name for name in dict.fromkeys(found) if any(name in table for table in tables.values())]


def varying(tables):
    """Return the candidate quantities that take more than one value across the scan."""
    def spread(name):
        # Failed points can hold NaN, which must not hide variation elsewhere.
        values = np.concatenate([table[name] for table in tables.values() if name in table])
        values = values[np.isfinite(values)]
        return values.max()-values.min() if values.size else 0.

    found = [name for name in candidates(tables) if spread(name) > 0]
    logging.debug('Varying scan quantities: %s', found)
    return found


def default_axes(tables):
    """Pick the first two quantities that vary across the scan, preferring model parameters."""
    chosen = (varying(tables) + candidates(tables))[:2]
    logging.debug('Default scan axes: %s', chosen)
    return chosen


def add_scan_arguments(tool):
    tool.add_argument('--scan', help='Which scan to plot when the folder holds several (the file-name '
                                     'prefix, for example 2026-11-12_16-20-22_test); default: the latest')


def load(tool, args):
    """Return the chosen scan's name and its category tables, or exit with a usage error."""
    if args.reference:
        tool.error('--reference is not supported for parameter scans')
    found = scans(args.input)
    if not found:
        tool.error(f'No parameter scan files in {args.input}')
    name = args.scan or sorted(found)[-1]
    if name not in found:
        tool.error(f'No scan {name!r} in {args.input}; found: {", ".join(sorted(found))}')
    if len(found) > 1 and not args.scan:
        logging.warning('Several scans in %s; plotting the latest, %s', args.input, name)
    tables = {category: read_category(path) for category, path in found[name].items()}
    if not sum(len(next(iter(table.values()), ())) for table in tables.values()):
        tool.error(f'Scan {name} has no points')
    return name, tables


def check_quantities(tool, tables, names):
    for name in names:
        if not any(name in table for table in tables.values()):
            tool.error(f'Unknown quantity {name!r}; available: {", ".join(candidates(tables))}')


def points(tables, *names):
    """Yield (category, meaning, colour, columns) for each category holding points."""
    for category, (meaning, color) in CATEGORIES.items():
        table = tables.get(category)
        if table is not None and all(name in table for name in names) and len(table[names[0]]):
            yield category, meaning, color, [table[name] for name in names]


def main(argv=None):
    tool = common.parser(__doc__.splitlines()[0], 'Scanner output folder containing <scan>_<category>s.txt files')
    add_scan_arguments(tool)
    tool.add_argument('--x', help='Quantity on the x axis (a column name from the scan files, E_dS or f_phi)')
    tool.add_argument('--y', help='Quantity on the y axis')
    args = common.parse(tool, argv)
    name, tables = load(tool, args)
    x, y = default_axes(tables)
    x, y = args.x or x, args.y or y
    check_quantities(tool, tables, (x, y))

    with common.style() as plt:
        figure, axis = plt.subplots(figsize=(9, 5.5))
        total = 0
        for _, meaning, color, (xs, ys) in points(tables, x, y):
            total += len(xs)
            axis.scatter(xs, ys, s=30, color=color, label=f'{meaning} ({len(xs)})', lw=0)
        axis.set(xlabel=axis_label(x), ylabel=axis_label(y), title=f'{args.label}: parameter scan ({total} points)')
        axis.legend(loc='upper left', bbox_to_anchor=(1.01, 1), title='Category')
        common.save(figure, args, 'parameter_scan')
        plt.close(figure)
    return 0


if __name__ == '__main__':
    sys.exit(main())
