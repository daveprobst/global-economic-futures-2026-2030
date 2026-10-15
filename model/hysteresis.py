"""Empirical hysteresis targets from the JST Macrohistory panel and calibration of the engine.

Output shortfall = real GDP per head, four years after an origin, relative to the log-linear
trend of the ten years up to and including the origin (so the same geometry as end-2026
-> 2030). Grouped by the worst real equity drawdown at annual closes inside the window and
by whether a systemic banking crisis started inside it. War years are excluded.
"""
from __future__ import annotations
import numpy as np, pandas as pd
import equity_panel as EP
import engine as E

GROUPS = {  # model scenario -> empirical class
    "continued_boom": "no_decline", "no_burst_sideways": "minor_decline",
    "mild_adjustment": "mild_moderate_no_crisis", "moderate_burst": "mild_moderate_no_crisis",
    "deep_drawdown_no_vacuum": "severe_no_crisis", "severe_burst": "severe_no_crisis",
    "severe_burst_with_financial_crisis": "deep_with_crisis"}
CLASS_LABEL = {"no_decline": "Drawdown under 10%", "minor_decline": "Drawdown 10–20%",
               "mild_moderate_no_crisis": "Drawdown 20–50%, no banking crisis", "severe_no_crisis": "Drawdown 50%+, no banking crisis",
               "deep_with_crisis": "Drawdown 35%+ with a banking crisis"}


def shortfall_panel() -> pd.DataFrame:
    j = EP.jst_frame(); rows = []
    for iso, g in j.groupby("iso"):
        g = g.set_index("year"); y = np.log(g.rgdpmad)
        ok = g.real_ret.dropna(); years = ok.index.to_numpy(); idx = np.cumprod(1 + ok.to_numpy())
        infl = g.infl.reindex(ok.index).to_numpy()
        for i in range(3, len(ok) - 4):
            t = int(years[i])
            if t < 1900 or t > 2016 or (1914 <= t <= 1920) or (1939 <= t <= 1947): continue
            if np.any(np.diff(years[i - 3:i + 5]) != 1) or np.any(np.isnan(infl[i - 3:i + 5])) or np.any(infl[i - 3:i + 5] > EP.INFLATION_CAP): continue
            pre = y.loc[t - 9:t].dropna()
            if len(pre) < 8 or t + 4 not in y.index or np.isnan(y[t + 4]): continue
            b = np.polyfit(pre.index.to_numpy(), pre.to_numpy(), 1)
            fwd = idx[i:i + 5]
            lv = np.exp(y.loc[t:t + 4].to_numpy() - y[t]) if all(k in y.index for k in range(t, t + 5)) else None
            if lv is None or np.isnan(lv).any(): continue
            rows.append({"iso": iso, "year": t, "trough": float(100 * (lv.min() - 1)), "drawdown": EP.drawdown_of(fwd),
                         "crisis": bool(g.loc[t:t + 4, "crisisJST"].fillna(0).max() > 0),
                         "shortfall": float(100 * (np.exp(y[t + 4] - np.polyval(b, t + 4)) - 1))})
    d = pd.DataFrame(rows)
    def klass(r):
        if r.crisis and r.drawdown <= -.35: return "deep_with_crisis"
        if r.drawdown <= -.50: return "severe_no_crisis"
        if r.drawdown <= -.20: return "mild_moderate_no_crisis"
        if r.drawdown <= -.10: return "minor_decline"
        return "no_decline"
    d["klass"] = d.apply(klass, axis=1)
    return d


def class_table(d: pd.DataFrame) -> dict:
    out = {}
    for k, g in d.groupby("klass"):
        q = g.shortfall.quantile([.1, .25, .5, .75, .9]).to_dict()
        out[k] = {"label": CLASS_LABEL[k], "n": int(len(g)), "troughP50": float(g.trough.median()), "troughMean": float(g.trough.mean()), "troughP25": float(g.trough.quantile(.25)), "countries": int(g.iso.nunique()), "mean": float(g.shortfall.mean()),
                  "p10": float(q[.1]), "p25": float(q[.25]), "p50": float(q[.5]), "p75": float(q[.75]), "p90": float(q[.9])}
    return out


def crisis_cohorts() -> dict:
    """Post-crisis shortfall paths for named cohorts and Japan after 1990."""
    j = pd.read_stata(EP.JST_DTA).sort_values(["iso", "year"]); rows = []
    for iso, g in j.groupby("iso"):
        g = g.set_index("year"); y = np.log(g.rgdpmad)
        starts = [t for t in g.index[g.crisisJST == 1] if g.crisisJST.get(t - 1, 0) != 1 and t >= 1946]
        for t in starts:
            pre = y.loc[t - 10:t - 1].dropna()
            if len(pre) < 8: continue
            b = np.polyfit(pre.index.to_numpy(), pre.to_numpy(), 1)
            row = {"iso": iso, "start": int(t)}
            for h in (3, 5, 7, 10):
                row[f"h{h}"] = float(100 * (np.exp(y[t + h] - np.polyval(b, t + h)) - 1)) if t + h in y.index and not np.isnan(y.get(t + h, np.nan)) else np.nan
            rows.append(row)
    d = pd.DataFrame(rows)
    stat = {f"h{h}": {"n": int(d[f"h{h}"].notna().sum()), "p25": float(d[f"h{h}"].quantile(.25)), "p50": float(d[f"h{h}"].median()),
                       "p75": float(d[f"h{h}"].quantile(.75))} for h in (3, 5, 7, 10)}
    g = j[j.iso == "JPN"].set_index("year"); y = np.log(g.rgdpmad); pre = y.loc[1980:1989]; b = np.polyfit(pre.index.to_numpy(), pre.to_numpy(), 1)
    japan = [{"yearsAfter": k, "shortfall": float(100 * (np.exp(y[1989 + k] - np.polyval(b, 1989 + k)) - 1))} for k in range(0, 31) if (1989 + k) in y.index]
    sens = []
    for lo in (1980, 1975, 1970, 1960):
        for label, ser in (("per head", np.log(g.rgdpmad)), ("total", np.log(g.rgdpmad * g["pop"]))):
            pre = ser.loc[lo:1989]; bb = np.polyfit(pre.index.to_numpy(), pre.to_numpy(), 1)
            sens.append({"trendYears": f"{lo}–1989", "measure": label, "h4": float(100 * (np.exp(ser[1993] - np.polyval(bb, 1993)) - 1)), "h10": float(100 * (np.exp(ser[1999] - np.polyval(bb, 1999)) - 1)),
                         "trendGrowth": float(100 * (np.exp(bb[0]) - 1))})
    gfc = d[d.start.isin([2007, 2008])]
    gfc_rows = [{"iso": r.iso, "h3": r.h3, "h5": r.h5, "h7": r.h7} for r in gfc.itertuples()]
    return {"postwarBankingCrises": stat, "japanAfter1989": japan, "japanSensitivity": sens, "gfcCohort": gfc_rows, "trendWindow": "10 years before the crisis start"}


def pava(y):
    """Isotonic (non-increasing in severity) fit; targets must worsen with severity."""
    y = list(y); w = [1] * len(y); i = 0
    while i < len(y) - 1:
        if y[i] < y[i + 1]:  # severity increases left to right, shortfall must not improve
            tot = y[i] * w[i] + y[i + 1] * w[i + 1]; w[i] += w[i + 1]; y[i] = tot / w[i]; del y[i + 1], w[i + 1]; i = max(i - 1, 0)
        else: i += 1
    out = []
    for v, ww in zip(y, w): out += [v] * ww
    return out


def calibrate(fins: dict, targets: dict, cohorts: dict, cn_base, cn_defl) -> tuple[dict, dict]:
    order = list(E.SEVERITY); sysm = "severe_burst_with_financial_crisis"
    raw = [targets[GROUPS[s]]["p50"] if s != "continued_boom" else 0.0 for s in order]
    raw[-1] = targets["deep_with_crisis"]["mean"]   # long left tail: calibrate the median to the class mean
    raw[5] = .5 * (targets["severe_no_crisis"]["p50"] + targets["deep_with_crisis"]["mean"])
    tgt = pava(raw)
    traw = [0.0 if s == "continued_boom" else targets[GROUPS[s]]["troughP50"] for s in order]
    traw[-1] = targets["deep_with_crisis"]["troughMean"]; traw[5] = .5 * (targets["severe_no_crisis"]["troughP50"] + targets["deep_with_crisis"]["troughMean"])
    ttr = [min(v, 0.0) for v in pava([min(v, 0) for v in traw])]
    pb = cohorts["postwarBankingCrises"]; persist = pb["h10"]["p50"] / pb["h5"]["p50"]   # share of the 5-year shortfall still present at 10 years
    best = (1e9, None)
    for phi in (.30, .40, .50, .60, .70, .85, 1.0, 1.2):
        for kap in (0, .5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0):
            for catch in (.20, .30):
                p = {**E.DEFAULT_PARAMS, "phi": phi, "kappa_us": kap, "catch_us": catch}
                err = 0; ms = {}
                for s, tg in zip(order, tgt):
                    ms[s] = E.macro(fins[s], p, cn_base, cn_defl)
                    err += (np.median(ms[s]["US"]["level"][:, 4]) - tg) ** 2
                    cum = np.cumsum(ms[s]["US"]["growth"][:, 1:], axis=1)
                    err += (8.0 if s == order[-1] else 3.0 if s == order[-2] else .5) * (np.median(np.minimum(cum.min(axis=1), 0)) - ttr[order.index(s)]) ** 2
                m = ms[sysm]; lvl = np.median(m["US"]["level"][:, 4]); ext = np.median(m["ext"]["US"][0])
                rebound = np.median(m["US"]["growth"][:, 3:5].mean(axis=1)) - (E.US_G0 - .5)
                err += (ext - persist * lvl) ** 2 + max(0, rebound) ** 2
                if err < best[0]: best = (err, p)
    p = best[1]; japan10 = [x for x in cohorts["japanAfter1989"] if x["yearsAfter"] == 10][0]["shortfall"]
    japan4 = [x for x in cohorts["japanAfter1989"] if x["yearsAfter"] == 4][0]["shortfall"]
    t4 = targets["deep_with_crisis"]["mean"]   # China crisis flags in ~9 of 10 paths of this branch
    bestc = (1e9, None)
    for pc in (.05, .10, .15, .20, .30, .45, .60):
        for kc in (0, .5, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0):
            q = {**p, "phi_cn": pc, "kappa_cn": kc, "catch_cn": .05}
            m = E.macro(fins[sysm], q, cn_base, cn_defl)
            err = (np.median(m["China"]["level"][:, 4]) - t4) ** 2 + (np.median(m["ext"]["China"][0]) - japan10) ** 2
            if err < bestc[0]: bestc = (err, q)
    return bestc[1], {"usTargets": dict(zip(order, [float(x) for x in tgt])), "usTroughTargets": dict(zip(order, [float(x) for x in ttr])), "usFitError": float(best[0]), "persistenceShare": float(persist),
                      "chinaFitError": float(bestc[0]), "chinaTarget2030": float(t4), "japanTarget10y": float(japan10)}
