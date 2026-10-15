"""Historical crash checks for the four-year outcome weights.

Every statistic uses the same window as the release: origin at an annual close after a
three-year real run-up of at least +50%, outcome measured over the next four annual closes.
"""
from __future__ import annotations
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
import equity_panel as EP

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
