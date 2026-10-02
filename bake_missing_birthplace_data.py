"""Complete birthplace estimates/MOEs from the official 2024 ACS 5-year file.

Usage: python3 bake_missing_birthplace_data.py /path/to/acsdt5y2024-b05006.dat
Source: https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/acsdt5y2024-b05006.dat

Preserves every existing value, checks it against Census, and adds only missing
fields. Puerto Rico uses separate tables and is outside this map's coverage.
"""
import csv
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent

def main(source):
    variables = re.findall(r"\['(B05006_\d+E)',", (ROOT / 'index.html').read_text())
    assert len(variables) == len(set(variables)) == 124
    files = {name: json.loads((ROOT / name).read_text()) for name in (
        'county-base-data.json', 'county-supp-data.json',
        'city-tracts-data.json', 'tract-supp-data.json')}
    targets = {
        '0500000US': ('county-base-data.json', 'county-supp-data.json'),
        '1400000US': ('city-tracts-data.json', 'tract-supp-data.json'),
    }
    seen = {prefix: set() for prefix in targets}
    added = {name: 0 for _, name in targets.values()}
    with Path(source).open() as stream:
        rows = csv.reader(stream, delimiter='|')
        columns = {re.sub(r'_(E|M)(\d+)$', r'_\2\1', h): i for i, h in enumerate(next(rows))}
        for row in rows:
            if not row:
                continue
            prefix = row[0][:9]
            if prefix not in targets:
                continue
            base_name, supp_name = targets[prefix]
            geoid = row[0][9:]
            if geoid.startswith('72') or geoid not in files[base_name]:
                continue
            seen[prefix].add(geoid)
            base = files[base_name][geoid]
            supp = files[supp_name][geoid]
            for estimate in variables:
                for var in (estimate, estimate[:-1] + 'M'):
                    raw = row[columns[var]]
                    try:
                        value = int(raw)
                    except ValueError:
                        value = -1
                    if value < 0:
                        value = -1
                    if var in base or var in supp:
                        current = base.get(var, supp.get(var))
                        assert current == value, (geoid, var, current, value)
                    else:
                        supp[var] = value
                        added[supp_name] += 1
    for prefix, (base_name, supp_name) in targets.items():
        expected = {g for g in files[base_name] if not g.startswith('72')}
        assert seen[prefix] == expected, (prefix, len(seen[prefix]), len(expected))
        for geoid in expected:
            combined = files[base_name][geoid] | files[supp_name][geoid]
            assert all(v in combined and v[:-1] + 'M' in combined for v in variables)
    # Write only after every existing value and geography has been checked.
    for name, count in added.items():
        (ROOT / name).write_text(json.dumps(files[name], separators=(',', ':')))
        print(f'{name}: added {count:,} fields')

if __name__ == '__main__':
    main(sys.argv[1])
