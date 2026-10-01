"""Build data/neighbourhood_income_2021.csv: income per Toronto neighbourhood, for the fairness check.

Source: City of Toronto Neighbourhood Profiles, 2021 Census, 158-neighbourhood model (XLSX).
Usage: python scripts/build_neighbourhood_income.py [nbhd_2021_census_profile_full_158model.xlsx]
With no argument the file (about 1.7 MB) is downloaded. Needs openpyxl (a dev dependency).
"""

import csv
import sys
import tempfile
from datetime import date
from pathlib import Path

import httpx
import openpyxl

URL = ("https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/6e19a90f-971c-46b3-852c-0c48c436d1fc/resource/"
       "19d4a806-7385-4889-acf2-256f1e079060/download/nbhd_2021_census_profile_full_158model.xlsx")
OUT = Path(__file__).resolve().parents[1] / "data" / "neighbourhood_income_2021.csv"
ROWS = {
    "Neighbourhood Number": "external_id",
    "Median total income of household in 2020 ($)": "median_household_income",
    "Prevalence of low income based on the Low-income measure, after tax (LIM-AT) (%)": "low_income_pct",
}


def main(xlsx: Path) -> None:
    sheet = openpyxl.load_workbook(xlsx, read_only=True)["hd2021_census_profile"]
    rows = sheet.iter_rows(values_only=True)
    names = next(rows)[1:]
    found = {}
    for r in rows:
        label = str(r[0] or "").strip()
        if label in ROWS and ROWS[label] not in found:  # the first match is the all-households figure
            found[ROWS[label]] = r[1:]
    missing = set(ROWS.values()) - set(found)
    if missing:
        raise SystemExit(f"Rows not found in the spreadsheet: {sorted(missing)}")
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        f.write("# Income by Toronto neighbourhood, 2021 Census (income year 2020).\n"
                "# Source: City of Toronto Neighbourhood Profiles, 158-neighbourhood model,\n"
                "#   nbhd_2021_census_profile_full_158model.xlsx (https://open.toronto.ca/dataset/neighbourhood-profiles/).\n"
                f"# Retrieved: {date.today().isoformat()}. Regenerate with scripts/build_neighbourhood_income.py.\n")
        w = csv.writer(f)
        w.writerow(["external_id", "name", "median_household_income", "low_income_pct"])
        for i, name in enumerate(names):
            w.writerow([int(found["external_id"][i]), name, found["median_household_income"][i], found["low_income_pct"][i]])
    print(f"Wrote {OUT}: {len(names)} neighbourhoods")


if __name__ == "__main__":
    if len(sys.argv) == 2:
        main(Path(sys.argv[1]))
    else:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "profile.xlsx"
            path.write_bytes(httpx.get(URL, timeout=120, follow_redirects=True, headers={"User-Agent": "uavert-demo/0.1"}).content)
            main(path)
