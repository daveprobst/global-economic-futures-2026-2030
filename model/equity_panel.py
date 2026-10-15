"""Pooled equity run-up episode panel, in real terms, on one four-year outcome window.

An episode starts at the close of year t when the three-year real equity return is at
least +50% (origins at least three years apart within a country). Predictors use returns
through t only. The outcome window is the next four annual closes (t+1..t+4), i.e. the
same "origin to end of window" geometry as today (end-2026 to end-2030).

Sources
  modern   World Bank S&P Global equity indices (CM.MKT.INDX.ZG), deflated by WB CPI, 1994-2021 origins
  history  Jorda-Schularick-Taylor total equity returns, deflated by JST CPI, origins before 1994
Windows containing annual inflation above 25% are dropped: index returns are not comparable there.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SERIES = ROOT / "data/derived/series"
JST_DTA = ROOT / "data/raw/JSTdatasetR6.dta"
HORIZON = 4
THRESHOLD = 0.50
INFLATION_CAP = 25.0
MODERN_FROM = 1994
BANDS = ("none", "mild", "moderate", "severe")
# Volatility is stored but not used: an 8-stock basket is not comparable with national indices and adds no out-of-sample skill.
PREDICTORS = ("runup3", "return1")
MODEL_CONFIGS = (("ridge_logit_C0_2", 0.2), ("ridge_logit_C1", 1.0))
BOOM_REAL_PER_YEAR = 0.05


def boom_hurdle(horizon: int = HORIZON) -> float:
    return (1 + BOOM_REAL_PER_YEAR) ** horizon - 1


def band_of(depth: float) -> str:
    return "severe" if depth <= -0.50 else "moderate" if depth <= -0.35 else "mild" if depth <= -0.20 else "none"


def outcome(row_depth: float, row_cum: float, horizon: int = HORIZON) -> str:
    """Seven-way partition collapsed to the three observable groups used for checks."""
    if row_depth <= -0.20: return "bust"
    return "boom" if row_cum > boom_hurdle(horizon) else "sideways"


def _episodes(iso: str, real_ret: pd.Series, infl: pd.Series, horizon: int, lo: int, hi: int, source: str) -> list[dict]:
    """real_ret / infl are indexed by calendar year, with gaps where data are missing."""
    d = pd.DataFrame({"ret": real_ret, "infl": infl}).dropna().sort_index()
    years = d.index.to_numpy(); ret = d.ret.to_numpy(); inf = d.infl.to_numpy()
    index = np.cumprod(1 + ret); rows = []; last = -100
    for i in range(4, len(d) - horizon):
        y = int(years[i])
        if not (lo <= y <= hi): continue
        if np.any(np.diff(years[i - 4:i + horizon + 1]) != 1): continue
        if np.any(inf[i - 3:i + horizon + 1] > INFLATION_CAP): continue
        run = index[i] / index[i - 3] - 1
        if run < THRESHOLD or i - last < 3: continue
        fwd = index[i:i + horizon + 1]
        rows.append({"country": iso, "originYear": y, "runup3": float(run), "return1": float(ret[i]),
                     "volatility5": float(np.std(ret[i - 4:i + 1])), "drawdown": float(fwd.min() / fwd[0] - 1),
                     "cumReturn": float(fwd[-1] / fwd[0] - 1), "source": source})
        last = i
    return rows


def _wb(iso: str):
    eq = SERIES / f"WB_CM.MKT.INDX.ZG_{iso}.csv"; cp = SERIES / f"WB_FP.CPI.TOTL.ZG_{iso}.csv"
    if not (eq.exists() and cp.exists()): return None
    e = pd.read_csv(eq); c = pd.read_csv(cp)
    r = pd.Series(e.value.to_numpy() / 100, index=e.date.astype(str).str[:4].astype(int))
    p = pd.Series(c.value.to_numpy(), index=c.date.astype(str).str[:4].astype(int))
    return (1 + r) / (1 + p / 100) - 1, p


def jst_frame() -> pd.DataFrame:
    j = pd.read_stata(JST_DTA).sort_values(["iso", "year"])
    j["infl"] = j.groupby("iso").cpi.pct_change() * 100
    j["real_ret"] = (1 + j.eq_tr) / (1 + j.infl / 100) - 1
    j.loc[j.eq_tr <= -0.99, "real_ret"] = np.nan
    return j


def load_panel(horizon: int = HORIZON) -> pd.DataFrame:
    rows = []
    for path in sorted(SERIES.glob("WB_CM.MKT.INDX.ZG_*.csv")):
        iso = path.stem.rsplit("_", 1)[-1]; got = _wb(iso)
        if got is None: continue
        rows += _episodes(iso, got[0], got[1], horizon, MODERN_FROM, 2100, "modern")
    j = jst_frame()
    for iso, g in j.groupby("iso"):
        rows += _episodes(iso, g.set_index("year").real_ret, g.set_index("year").infl, horizon, 1870, MODERN_FROM - 1, "history")
    df = pd.DataFrame(rows)
    df["band"] = df.drawdown.map(band_of)
    df["outcome"] = [outcome(a, b, horizon) for a, b in zip(df.drawdown, df.cumReturn)]
    return df.reset_index(drop=True)
