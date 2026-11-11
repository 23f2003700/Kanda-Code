"""Download NASA POWER monthly weather for Lasalgaon (Nashik district), 1996-2024, and save raw JSON + tidy CSV.

Source: NASA Langley Research Center POWER project, https://power.larc.nasa.gov (free, no key).
Satellite-derived and reanalysis estimates (MERRA-2 for temperature/humidity, IMERG-corrected for rain)
on a ~0.5 degree grid. Parameters: T2M (deg C), RH2M (%), PRECTOTCORR (mm/day).
"""
import json
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "raw" / "nasa_power"
LAT, LON = 20.15, 74.23  # Lasalgaon APMC, Niphad taluka, Nashik
URL = ("https://power.larc.nasa.gov/api/temporal/monthly/point?parameters=T2M,RH2M,PRECTOTCORR"
       f"&community=AG&longitude={LON}&latitude={LAT}&start=1996&end=2024&format=JSON")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(URL, timeout=120) as r:
        raw = json.loads(r.read().decode("utf-8"))
    (OUT / "lasalgaon_power_monthly_1996_2024.json").write_text(json.dumps(raw, indent=1), encoding="utf-8")
    par = raw["properties"]["parameter"]
    rows = []
    for key in par["T2M"]:
        if key.endswith("13"):  # annual mean row
            continue
        rows.append({"ym": f"{key[:4]}-{key[4:]}", "t2m_c": par["T2M"][key], "rh2m_pct": par["RH2M"][key],
                     "rain_mm_per_day": par["PRECTOTCORR"][key]})
    df = pd.DataFrame(rows).sort_values("ym")
    df.to_csv(OUT / "lasalgaon_power_monthly_1996_2024.csv", index=False)
    print(len(df), "months;", df["ym"].iloc[0], "to", df["ym"].iloc[-1], "; source:", URL)


if __name__ == "__main__":
    main()
