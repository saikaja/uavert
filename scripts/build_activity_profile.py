"""Build data/activity_by_hour.csv: how many people are out at each hour, relative to the daytime average.

Hours 6 am-7 pm come from City of Toronto 15-minute pedestrian counts (14-hour counts only, so every hour is
covered by the same counts). The City doesn't count at night, so the other hours are estimated from
Bike Share Toronto trip start times, lined up with the pedestrian counts where both exist.

Usage: python scripts/build_activity_profile.py [tmc_raw_2020_2029.csv] [bikeshare-ridership-2025.zip]
With no arguments the two files (about 315 MB) are downloaded to a temporary folder.
"""

import csv
import io
import sys
import tempfile
import zipfile
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import httpx

TMC_URL = ("https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/811c4c10-7e5d-4c76-8d42-dab4e31c8265/resource/"
           "88ea1329-1da3-4992-bae6-a821d609d45d/download/tmc_raw_data_2020_2029.csv")
BIKESHARE_URL = "https://opendata.toronto.ca/toronto.parking.authority/bike-share-toronto-ridership-data/bikeshare-ridership-2025.zip"
OUT = Path(__file__).resolve().parents[1] / "data" / "activity_by_hour.csv"
PED_COLUMNS = ("n_appr_peds", "s_appr_peds", "e_appr_peds", "w_appr_peds")


def download(url: str, folder: Path) -> Path:
    path = folder / url.rsplit("/", 1)[-1]
    with httpx.stream("GET", url, timeout=300, follow_redirects=True, headers={"User-Agent": "uavert-demo/0.1"}) as r:
        r.raise_for_status()
        with open(path, "wb") as f:
            for chunk in r.iter_bytes():
                f.write(chunk)
    return path


def pedestrian_profile(tmc_csv: Path) -> tuple[dict[int, float], int]:
    """Average pedestrians per 15 minutes by hour, from counts that cover 14 hours."""
    hours_by_count: dict[str, set] = defaultdict(set)
    rows = []
    with open(tmc_csv, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            hour = int(r["start_time"][11:13])
            hours_by_count[r["count_id"]].add(hour)
            rows.append((r["count_id"], hour, sum(int(float(r[c] or 0)) for c in PED_COLUMNS)))
    full = {c for c, hours in hours_by_count.items() if len(hours) >= 14}
    total, slots = Counter(), Counter()
    for count_id, hour, peds in rows:
        if count_id in full:
            total[hour] += peds
            slots[hour] += 1
    return {h: total[h] / slots[h] for h in slots}, len(full)


def bikeshare_profile(zip_path: Path) -> tuple[dict[int, float], int]:
    trips = Counter()
    with zipfile.ZipFile(zip_path) as z:
        for name in z.namelist():
            if not name.lower().endswith(".csv"):
                continue
            with z.open(name) as f:
                reader = csv.reader(io.TextIOWrapper(f, encoding="utf-8-sig", errors="replace"))
                i = next(reader).index("Start_Time")
                for row in reader:
                    t = row[i]
                    if len(t) >= 13 and t[11:13].isdigit():
                        trips[int(t[11:13])] += 1
    return {h: trips[h] for h in range(24)}, sum(trips.values())


def main(tmc_csv: Path, bikeshare_zip: Path) -> None:
    peds, n_counts = pedestrian_profile(tmc_csv)
    bikes, n_trips = bikeshare_profile(bikeshare_zip)
    measured = sorted(peds)  # 6..19
    ped_avg = sum(peds.values()) / len(peds)
    bike_avg = sum(bikes[h] for h in measured) / len(measured)
    ped_f = {h: peds[h] / ped_avg for h in measured}
    bike_f = {h: bikes[h] / bike_avg for h in range(24)}
    scale = sum(ped_f[h] / bike_f[h] for h in measured) / len(measured)  # line Bike Share up with the counts

    header = [
        "# How many people are out at each hour, relative to the 6 am-8 pm average (1.0).",
        f"# Measured hours: City of Toronto Turning Movement Counts, 15-minute pedestrian volumes, {n_counts:,} 14-hour counts",
        "#   (tmc_raw_data_2020_2029.csv, https://open.toronto.ca/dataset/traffic-volumes-at-intersections-for-all-modes/).",
        f"# Estimated hours (no counts at night): Bike Share Toronto ridership 2025, {n_trips:,} trips by start hour",
        f"#   (https://open.toronto.ca/dataset/bike-share-toronto-ridership-data/), scaled by {scale:.3f} to match the counts over 6 am-7 pm.",
        f"# Retrieved: {date.today().isoformat()}. Regenerate with scripts/build_activity_profile.py.",
    ]
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        f.write("\n".join(header) + "\n")
        w = csv.writer(f)
        w.writerow(["hour", "pedestrian_factor", "bikeshare_factor", "factor_used", "basis"])
        for h in range(24):
            if h in ped_f:
                w.writerow([h, f"{ped_f[h]:.3f}", f"{bike_f[h]:.3f}", f"{ped_f[h]:.3f}", "measured"])
            else:
                w.writerow([h, "", f"{bike_f[h]:.3f}", f"{bike_f[h] * scale:.3f}", "estimated"])
    print(f"Wrote {OUT} (scale {scale:.3f})")


if __name__ == "__main__":
    if len(sys.argv) == 3:
        main(Path(sys.argv[1]), Path(sys.argv[2]))
    else:
        with tempfile.TemporaryDirectory() as tmp:
            main(download(TMC_URL, Path(tmp)), download(BIKESHARE_URL, Path(tmp)))
