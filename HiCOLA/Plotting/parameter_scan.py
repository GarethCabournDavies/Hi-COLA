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
    data = np.array(rows, dtype=float).reshape(-1, len(rows[0]) if rows else len(names))
    table = {name: data[:, column] for column, name in enumerate(names[:data.shape[1]])}
    if {'Hubble0', 'Omega_l0', 'Omega_m0', 'Omega_r0'} <= set(table):
        with np.errstate(divide='ignore', invalid='ignore'):
            table['E_dS'] = 1/table['Hubble0']
            table['f_phi'] = 1-table['Omega_l0']/(1-table['Omega_m0']-table['Omega_r0'])
    return table


def default_axes(tables):
    """Pick the first two quantities that vary across the scan, preferring model parameters."""
    columns = [name for table in tables.values() for name in table]
    first = next(iter(tables.values()))
    names = list(first)
    parameters = names[names.index('fsolve_ier')+1:] if 'fsolve_ier' in names else names
    candidates = [name for name in parameters if not name.startswith('max[') and name not in DERIVED]
    candidates += [*DERIVED, 'Omega_m0', 'Omega_r0', 'Omega_l0', 'Scalarprime0', 'Scalar0', 'Hubble0']
    def spread(name):
        # Failed points can hold NaN, which must not hide variation elsewhere.
        values = np.concatenate([table[name] for table in tables.values() if name in table])
        values = values[np.isfinite(values)]
        return values.max()-values.min() if values.size else 0.

    varying = [name for name in dict.fromkeys(candidates) if columns.count(name) and spread(name) > 0]
    chosen = (varying + [name for name in candidates if name in first])[:2]
    logging.debug('Default scan axes: %s', chosen)
    return chosen


def main(argv=None):
    tool = common.parser(__doc__.splitlines()[0], 'Scanner output folder containing <scan>_<category>s.txt files')
    tool.add_argument('--scan', help='Which scan to plot when the folder holds several (the file-name '
                                     'prefix, for example 2026-11-12_16-20-22_test); default: the latest')
    tool.add_argument('--x', help='Quantity on the x axis (a column name from the scan files, E_dS or f_phi)')
    tool.add_argument('--y', help='Quantity on the y axis')
    args = common.parse(tool, argv)
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
    x, y = default_axes(tables)
    x, y = args.x or x, args.y or y
    for axis_name in (x, y):
        if not any(axis_name in table for table in tables.values()):
            tool.error(f'Unknown quantity {axis_name!r}; available: {", ".join(next(iter(tables.values())))}')

    with common.style() as plt:
        figure, axis = plt.subplots(figsize=(9, 5.5))
        total = 0
        for category, (meaning, color) in CATEGORIES.items():
            table = tables.get(category)
            count = 0 if table is None or x not in table else len(table[x])
            total += count
            if count:
                axis.scatter(table[x], table[y], s=18, color=color, label=f'{meaning} ({count})', lw=0)
        if not total:
            tool.error(f'Scan {name} has no points')
        axis.set(xlabel=axis_label(x), ylabel=axis_label(y), title=f'{args.label}: parameter scan ({total} points)')
        axis.legend(loc='upper left', bbox_to_anchor=(1.01, 1), title='Category')
        common.save(figure, args, 'parameter_scan')
        plt.close(figure)
    return 0


if __name__ == '__main__':
    sys.exit(main())
