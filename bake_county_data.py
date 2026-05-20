"""
One-time bake of county-level ACS base data into a static JSON file.

Replaces the live Census API call in index.html (loadCensusData), which broke
when the Census Bureau began requiring an API key. Output mirrors the `merged`
object the page used to build at runtime: { fips: { name, <E var>: value, ... } }
with non-numeric values stored as -1.

Run once. The API key is used only here and is NOT written into the output.
"""
import json
import sys
import urllib.request
import urllib.parse

ACS_YEAR = "2024"
KEY = sys.argv[1] if len(sys.argv) > 1 else ""

# Country E vars the page renders (from COUNTRY_VARS, read live from the page),
# minus the three sourced from county-supp-data.json (050/051/052).
COUNTRY_VARS = ["B05006_160E","B05006_158E","B05006_157E","B05006_159E","B05006_156E","B05006_155E","B05006_161E","B05006_162E","B05006_143E","B05006_145E","B05006_147E","B05006_148E","B05006_141E","B05006_142E","B05006_146E","B05006_149E","B05006_150E","B05006_151E","B05006_165E","B05006_166E","B05006_167E","B05006_168E","B05006_169E","B05006_170E","B05006_171E","B05006_172E","B05006_173E","B05006_174E","B05006_177E","B05006_050E","B05006_051E","B05006_052E","B05006_053E","B05006_054E","B05006_060E","B05006_064E","B05006_058E","B05006_063E","B05006_065E","B05006_059E","B05006_062E","B05006_066E","B05006_057E","B05006_061E","B05006_074E","B05006_077E","B05006_069E","B05006_070E","B05006_071E","B05006_072E","B05006_073E","B05006_075E","B05006_076E","B05006_080E","B05006_081E","B05006_082E","B05006_083E","B05006_084E","B05006_085E","B05006_086E","B05006_087E","B05006_088E","B05006_089E","B05006_090E","B05006_091E","B05006_092E","B05006_044E","B05006_042E","B05006_040E","B05006_017E","B05006_008E","B05006_005E","B05006_023E","B05006_016E","B05006_018E","B05006_015E","B05006_019E","B05006_014E","B05006_026E","B05006_024E","B05006_022E","B05006_004E","B05006_006E","B05006_007E","B05006_029E","B05006_030E","B05006_031E","B05006_032E","B05006_033E","B05006_034E","B05006_035E","B05006_036E","B05006_037E","B05006_038E","B05006_039E","B05006_041E","B05006_043E","B05006_124E","B05006_098E","B05006_099E","B05006_100E","B05006_117E","B05006_112E","B05006_113E","B05006_111E","B05006_114E","B05006_097E","B05006_101E","B05006_102E","B05006_103E","B05006_106E","B05006_107E","B05006_108E","B05006_120E","B05006_121E","B05006_122E","B05006_123E","B05006_125E","B05006_126E","B05006_127E","B05006_132E","B05006_134E","B05006_135E","B05006_136E"]

SUPP_SOURCED = {"B05006_050E", "B05006_051E", "B05006_052E"}
existing = [v for v in COUNTRY_VARS if v not in SUPP_SOURCED]
base = ["B05002_001E", "B05006_001E"]
all_vars = base + existing


def chunk(arr, size):
    return [arr[i:i + size] for i in range(0, len(arr), size)]


def fetch_batch(vars_):
    get = ",".join(["NAME"] + vars_)
    qs = urllib.parse.urlencode({
        "get": get, "for": "county:*", "in": "state:*",
    })
    url = f"https://api.census.gov/data/{ACS_YEAR}/acs/acs5?{qs}"
    if KEY:
        url += f"&key={KEY}"
    with urllib.request.urlopen(url, timeout=120) as r:
        return json.load(r)


def main():
    merged = {}
    for i, batch in enumerate(chunk(all_vars, 46), 1):
        print(f"batch {i}: {len(batch)} vars ...", flush=True)
        rows = fetch_batch(batch)
        headers = rows[0]
        si, ci, ni = headers.index("state"), headers.index("county"), headers.index("NAME")
        for r in rows[1:]:
            fips = r[si] + r[ci]
            d = merged.setdefault(fips, {"name": r[ni]})
            for j, h in enumerate(headers):
                if h in ("NAME", "state", "county"):
                    continue
                try:
                    v = int(r[j])
                except (ValueError, TypeError):
                    v = -1
                d[h] = v
    with open("county-base-data.json", "w") as f:
        json.dump(merged, f, separators=(",", ":"))
    print(f"wrote county-base-data.json: {len(merged)} counties")


if __name__ == "__main__":
    main()
