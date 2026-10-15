"""Historical crash checks for the four-year outcome weights.

Every statistic uses the same window as the release: origin at an annual close after a
three-year real run-up of at least +50%, outcome measured over the next four annual closes.
"""
from __future__ import annotations
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
import equity_panel as EP
from models import blend_rows
from sklearn.metrics import roc_auc_score

OUTCOMES = ("boom", "sideways", "bust")
ERAS = [(1870, 1913), (1914, 1945), (1946, 1973), (1974, 1993), (1994, 2008), (2009, 2021)]


def freq(df: pd.DataFrame) -> dict:
    n = len(df)
    return {"n": int(n), **{k: float((df.outcome == k).mean()) for k in OUTCOMES}} if n else {"n": 0}


def year_cluster_ci(df: pd.DataFrame, reps: int = 2000, seed: int = 20261015) -> dict:
    """Bootstrap whole origin years: simultaneous global crashes are one draw, not thirty."""
    rng = np.random.default_rng(seed); groups = {y: g for y, g in df.groupby("originYear")}; ys = list(groups)
    draws = []
    for _ in range(reps):
        s = pd.concat([groups[y] for y in rng.choice(ys, len(ys))])
        draws.append([(s.outcome == k).mean() for k in OUTCOMES])
    q = np.percentile(draws, [10, 90], axis=0)
    return {k: [float(q[0][i]), float(q[1][i])] for i, k in enumerate(OUTCOMES)}


def year_weighted(df: pd.DataFrame) -> dict:
    w = 1 / df.groupby("originYear").originYear.transform("size")
    return {k: float(((df.outcome == k) * w).sum() / w.sum()) for k in OUTCOMES}


def _probs(train: pd.DataFrame, test: pd.DataFrame, c: float = 0.2) -> np.ndarray:
    sc = StandardScaler().fit(train[list(EP.PREDICTORS)])
    m = LogisticRegression(C=c, max_iter=3000, random_state=20261014).fit(sc.transform(train[list(EP.PREDICTORS)]), train.band)
    raw = m.predict_proba(sc.transform(test[list(EP.PREDICTORS)])); p = np.full((len(test), 4), 1e-9)
    for j, k in enumerate(m.classes_): p[:, EP.BANDS.index(k)] = raw[:, j]
    none = train[train.band == "none"]; boom = (none.outcome == "boom").sum()
    share = (boom + .5) / (len(none) + 1.0)
    bust = 1 - p[:, 0]
    return np.column_stack([p[:, 0] * share, p[:, 0] * (1 - share), bust])


def _score(y: np.ndarray, P: np.ndarray) -> float:
    return float(np.mean(np.sum((P - np.eye(3)[y]) ** 2, axis=1)))


def cross_validate(df: pd.DataFrame) -> dict:
    y = np.array([OUTCOMES.index(o) for o in df.outcome]); res = {}
    for name, groups in (("leaveOneCountryOut", df.country.to_numpy()),
                         ("leaveOneEraOut", np.array([next(i for i, (a, b) in enumerate(ERAS) if a <= t <= b) for t in df.originYear]))):
        P = np.zeros((len(df), 3)); B = np.zeros((len(df), 3))
        for g in np.unique(groups):
            te = groups == g; tr = ~te
            if tr.sum() < 20: continue
            P[te] = _probs(df[tr], df[te])
            B[te] = np.array([(df[tr].outcome == k).mean() for k in OUTCOMES])
        res[name] = {"brier": _score(y, P), "baseRateBrier": _score(y, B), "n": int(len(df)),
                     "meanPredictedBust": float(P[:, 2].mean()), "observedBust": float((y == 2).mean()),
                     "meanPredictedBoom": float(P[:, 0].mean()), "observedBoom": float((y == 0).mean())}
        bins = pd.qcut(P[:, 2], 4, duplicates="drop"); cal = []
        for b in sorted(set(bins)):
            mk = np.array(bins) == b
            cal.append({"predictedBust": float(P[mk, 2].mean()), "observedBust": float((y[mk] == 2).mean()), "n": int(mk.sum())})
        res[name]["calibrationBustQuartiles"] = cal
        if name == "leaveOneEraOut":
            res[name]["byEra"] = [{"era": f"{a}–{b}", "n": int(((df.originYear >= a) & (df.originYear <= b)).sum()),
                                   "observedBust": float((y[(df.originYear >= a) & (df.originYear <= b)] == 2).mean()) if ((df.originYear >= a) & (df.originYear <= b)).any() else None,
                                   "predictedBust": float(P[(df.originYear >= a) & (df.originYear <= b), 2].mean()) if ((df.originYear >= a) & (df.originYear <= b)).any() else None} for a, b in ERAS]
    return res


def run(df: pd.DataFrame, current: dict, model_probs: dict) -> dict:
    df = df.copy(); df["bucket"] = pd.cut(df.runup3, [0.49, 1.0, 1.5, 100], labels=["50–100%", "100–150%", "150%+"])
    big = df[df.runup3 >= 1.0]
    buckets = []
    for b, g in df.groupby("bucket", observed=True):
        buckets.append({"runup": str(b), **freq(g)})
    eras = [{"era": f"{a}–{b}", **freq(df[(df.originYear >= a) & (df.originYear <= b)])} for a, b in ERAS]
    cases = big.sort_values("runup3", ascending=False).head(18)
    cases = [{"country": r.country, "origin": int(r.originYear), "runup3": float(r.runup3), "worstDecline": float(r.drawdown),
              "realReturn4y": float(r.cumReturn), "outcome": r.outcome} for r in cases.itertuples()]
    F = list(EP.PREDICTORS); sd = df[F].std(); cur = np.array([current["runup3"], current["return1"]])
    dist = (((df[F] - cur) / sd) ** 2).sum(axis=1) ** .5
    near = df.assign(dist=dist).sort_values("dist").head(25)
    nearest = {**freq(near), "k": 25, "closest": [{"country": r.country, "origin": int(r.originYear), "runup3": float(r.runup3), "return1": float(r.return1),
                                                     "worstDecline": float(r.drawdown), "realReturn4y": float(r.cumReturn), "outcome": r.outcome} for r in near.head(10).itertuples()]}
    out = {
        "nearestAnalogs": nearest,
        "window": "Origin at an annual close; outcome = next four annual closes. Real (inflation-adjusted) equity returns.",
        "episodes": int(len(df)), "countries": int(df.country.nunique()), "originYears": int(df.originYear.nunique()),
        "boomHurdle": {"realPerYear": EP.BOOM_REAL_PER_YEAR, "fourYear": EP.boom_hurdle()},
        "all": {**freq(df), "yearWeighted": year_weighted(df), "yearClusterInterval80": year_cluster_ci(df)},
        "bySource": {s: freq(g) for s, g in df.groupby("source")},
        "byRunup": buckets, "byEra": eras,
        "runupAtLeast100": {**freq(big), "bySource": {k: freq(g) for k, g in big.groupby("source")}, "yearWeighted": year_weighted(big), "yearClusterInterval80": year_cluster_ci(big)},
        "largestRunups": cases, "current": current, "modelWeights": model_probs,
        "crossValidation": cross_validate(df)}
    return out


# ---------------------------------------------------------------- validation report
def waves(years, gap=2):
    ys = sorted(set(int(y) for y in years)); out = {}; k = 0
    for i, y in enumerate(ys):
        if i and y - ys[i - 1] > gap: k += 1
        out[y] = k
    return out


def _logit_bust(train, test, feats, c=.2):
    sc = StandardScaler().fit(train[feats]); y = (train.outcome == "bust").astype(int)
    return LogisticRegression(C=c, max_iter=3000, random_state=20261014).fit(sc.transform(train[feats]), y).predict_proba(sc.transform(test[feats]))[:, 1]


MODELS = {
    "Base rate (training frequency)": lambda tr, te: np.full(len(te), (tr.outcome == "bust").mean()),
    "Run-up only (ridge logit)": lambda tr, te: _logit_bust(tr, te, ["runup3"]),
    "Last-12-month return only (ridge logit)": lambda tr, te: _logit_bust(tr, te, ["return1"]),
    "Run-up + return (ridge logit)": lambda tr, te: _logit_bust(tr, te, ["runup3", "return1"]),
    "Full blend (logit + boosting + forest)": lambda tr, te: blend_rows(tr, te)[0]}


def _metrics(y, p):
    p = np.clip(p, 1e-4, 1 - 1e-4)
    return {"brier": float(np.mean((p - y) ** 2)), "logLoss": float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))),
            "auc": float(roc_auc_score(y, p)) if 0 < y.mean() < 1 and np.ptp(p) > 0 else None}


def validation_report(df: pd.DataFrame) -> dict:
    y = (df.outcome == "bust").astype(int).to_numpy(); wv = df.originYear.map(waves(df.originYear)).to_numpy()
    schemes = {"Leave one economy out": df.country.to_numpy(), "Leave one global wave out": wv}
    out = {"target": "a 20%+ peak-to-trough fall at annual closes within four years", "n": int(len(df)), "schemes": {}, "waveCount": int(len(set(wv))),
           "waveDefinition": "origin years within two years of each other form one global wave; a whole wave is held out together"}
    for sname, groups in schemes.items():
        res = {}
        for mname, fn in MODELS.items():
            P = np.zeros(len(df))
            for g in np.unique(groups):
                te = groups == g
                P[te] = fn(df[~te], df[te])
            res[mname] = {**_metrics(y, P)}
            if mname.startswith("Full blend"):
                q = pd.qcut(P, 5, duplicates="drop"); res[mname]["reliability"] = [
                    {"predicted": float(P[np.array(q) == b].mean()), "observed": float(y[np.array(q) == b].mean()), "n": int((np.array(q) == b).sum())} for b in sorted(set(q))]
        out["schemes"][sname] = res
    res = {}
    for name, (a, b) in {"Train before 1994, test 1994–2021": ((df.source == "history"), (df.source == "modern")),
                         "Train 1994–2021, test before 1994": ((df.source == "modern"), (df.source == "history"))}.items():
        tr, te = df[a], df[b]; r = {}
        for mname, fn in MODELS.items(): r[mname] = _metrics(y[b.to_numpy()], fn(tr, te))
        res[name] = {"n": int(b.sum()), "observedBust": float(y[b.to_numpy()].mean()), "models": r}
    out["outOfTime"] = res
    return out


# ---------------------------------------------------------------- parameter sensitivity
def sensitivity(current: dict) -> list[dict]:
    cur = pd.DataFrame([[current["runup3"], current["return1"]]], columns=["runup3", "return1"])
    variants = [("As released", {}, None), ("Drawdown measured from the origin level (earlier definition)", {"dd_mode": "origin"}, None),
                ("Run-up trigger +40%", {"threshold": .40}, None), ("Run-up trigger +75%", {"threshold": .75}, None), ("Run-up trigger +100%", {"threshold": 1.0}, None),
                ("Boom hurdle 3% a year", {"hurdle_per_year": .03}, None), ("Boom hurdle 7% a year", {"hurdle_per_year": .07}, None),
                ("Window of 3 annual closes", {"horizon": 3}, None), ("Window of 5 annual closes", {"horizon": 5}, None),
                ("Modern era only (1994–2021)", {"sources": ("modern",)}, None), ("Pre-1994 history only", {"sources": ("history",)}, None),
                ("Run-up as the only predictor", {}, ["runup3"])]
    rows = []
    for name, kw, feats in variants:
        d = EP.load_panel(**kw); F = feats or list(EP.PREDICTORS)
        sc = StandardScaler().fit(d[F]); ps = []
        for _, c in EP.MODEL_CONFIGS:
            m = LogisticRegression(C=c, max_iter=3000, random_state=20261014).fit(sc.transform(d[F]), d.band)
            pr = m.predict_proba(sc.transform(cur[F]))[0]; ps.append(1 - pr[list(m.classes_).index("none")])
        none = d[d.band == "none"]; boom = int((none.outcome == "boom").sum()); share = (boom + .5) / (len(none) + 1)
        pf = float(np.mean(ps))
        rows.append({"variant": name, "episodes": int(len(d)), "fall20": pf, "boom": float((1 - pf) * share), "observedFall": float((d.outcome == "bust").mean())})
    return rows


# ---------------------------------------------------------------- sampling-resolution bias
def resolution_check(path) -> dict:
    d = pd.read_csv(path, parse_dates=["Date"]); d = d[d["Real Price"] > 0].reset_index(drop=True)
    d["y"] = d.Date.dt.year; d["m"] = d.Date.dt.month
    real = d.set_index("Date")["Real Price"]; dec = d[d.m == 12].set_index("y")["Real Price"]
    rows = []
    for t in range(1871, 2019):
        if t not in dec.index or t + 4 not in dec.index: continue
        mon = real[(real.index >= pd.Timestamp(t, 12, 1)) & (real.index <= pd.Timestamp(t + 4, 12, 1))].to_numpy()
        ann = dec.loc[t:t + 4].to_numpy()
        if len(mon) < 49: continue
        dm = float((mon / np.maximum.accumulate(mon)).min() - 1); da = float((ann / np.maximum.accumulate(ann)).min() - 1)
        run = dec.get(t, np.nan) / dec.get(t - 3, np.nan) - 1 if (t - 3) in dec.index else np.nan
        rows.append({"t": t, "monthly": dm, "annual": da, "runup": run})
    r = pd.DataFrame(rows); hit = r[r.monthly <= -.20]
    big = r[r.runup >= .5]
    return {"source": "Shiller monthly real S&P 500 (1871–2022 origins), US only", "windows": int(len(r)),
            "monthlyFall20": float((r.monthly <= -.20).mean()), "annualFall20": float((r.annual <= -.20).mean()),
            "annualCatchesMonthlyFalls": float((hit.annual <= -.20).mean()), "medianDepthUnderstatedPp": float(100 * (hit.annual - hit.monthly).median()),
            "afterRunup50": {"windows": int(len(big)), "monthlyFall20": float((big.monthly <= -.20).mean()) if len(big) else None, "annualFall20": float((big.annual <= -.20).mean()) if len(big) else None}}
