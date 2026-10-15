"""Fetch the open historical inputs used by the release model.

Sources: World Bank WDI (CC BY 4.0) and the Jordà-Schularick-Taylor Macrohistory
database R6. Everything is written under data/derived so the model can be rebuilt
from scratch with `python model/fetch_data.py && python model/direct_release.py`.
"""
import json, sys, urllib.request
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1] if len(sys.argv) < 2 else Path(sys.argv[1])
RAW, SERIES, PANELS = ROOT/"data/raw", ROOT/"data/derived/series", ROOT/"data/derived/panels"
for p in (RAW, SERIES, PANELS): p.mkdir(parents=True, exist_ok=True)
JST_URL = "https://www.macrohistory.net/app/download/9834512469/JSTdatasetR6.dta?t=1763503850"

def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "gef-model/1.0"}), timeout=60) as r:
        return r.read()

def wb(indicator, countries="all"):
    url = f"https://api.worldbank.org/v2/country/{countries}/indicator/{indicator}?format=json&per_page=30000"
    meta, rows = json.loads(get(url))
    out = {}
    for r in rows:
        if r["value"] is None or len(r["countryiso3code"]) != 3: continue
        out.setdefault(r["countryiso3code"], []).append({"date": r["date"], "value": r["value"]})
    return out

def write(indicator, data):
    for iso, rows in data.items():
        pd.DataFrame(rows).sort_values("date").to_csv(SERIES/f"WB_{indicator}_{iso}.csv", index=False)

if __name__ == "__main__":
    eq = wb("CM.MKT.INDX.ZG"); write("CM.MKT.INDX.ZG", eq)
    cpi = wb("FP.CPI.TOTL.ZG"); write("FP.CPI.TOTL.ZG", cpi)
    gdp = wb("NY.GDP.MKTP.KD.ZG", "USA;EMU;JPN;CHN;DEU;GBR;KOR;CHE"); write("NY.GDP.MKTP.KD.ZG", gdp)
    dfl = wb("NY.GDP.DEFL.KD.ZG", "CHN;USA"); write("NY.GDP.DEFL.KD.ZG", dfl)
    lvl = wb("NY.GDP.MKTP.KD", "USA;EMU;JPN;CHN;DEU;GBR;KOR;CHE"); write("NY.GDP.MKTP.KD", lvl)
    dta = RAW/"JSTdatasetR6.dta"
    if not dta.exists(): dta.write_bytes(get(JST_URL))
    j = pd.read_stata(dta)
    j["creditToGdpPct"] = 100*j.tloans/j.gdp
    j["debtToGdpPct"] = 100*j.debtgdp
    panel = j[["iso","year","crisisJST","creditToGdpPct","debtToGdpPct","stir"]]
    panel.to_csv(PANELS/"JST_ANNUAL_PANEL.csv", index=False)
    print(len(eq), "equity series;", len(panel), "JST rows")
