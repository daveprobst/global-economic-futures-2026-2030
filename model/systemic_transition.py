"""Calibrated equity-to-banking-crisis transition model.

The model deliberately uses a small feature set and leave-country-out validation.
It answers a narrow question: given a two-year equity drawdown and the balance
sheet state at its start, how often did a systemic banking crisis begin within
three years?  It is a transition model, not an equity-crash probability model.
"""
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score

FEATURES = ["drawdown2y", "runup3", "credit", "credit5", "debt", "short"]


def build_panel(root: Path) -> pd.DataFrame:
    jst = pd.read_csv(root / "data/derived/panels/JST_ANNUAL_PANEL.csv")
    rows = []
    for iso in sorted(jst.iso.unique()):
        path = root / f"data/derived/series/WB_CM.MKT.INDX.ZG_{iso}.csv"
        if not path.exists():
            continue
        market = pd.read_csv(path)
        market["year"] = market.date.astype(str).str[:4].astype(int)
        market["ret"] = pd.to_numeric(market.value, errors="coerce") / 100
        market = market.dropna(subset=["ret"]).sort_values("year")
        market["level"] = (1 + market.ret).cumprod()
        wm = market.set_index("year")
        country = jst[jst.iso == iso].sort_values("year").copy()
        country["credit5"] = country.creditToGdpPct - country.creditToGdpPct.shift(5)
        for _, r in country.iterrows():
            year = int(r.year)
            if not all(y in wm.index for y in [year - 3, year, year + 1, year + 2]):
                continue
            runup = wm.loc[year, "level"] / wm.loc[year - 3, "level"] - 1
            drawdown = wm.loc[year:year + 2, "level"].min() / wm.loc[year, "level"] - 1
            future = country[country.year.between(year, year + 2)].crisisJST.fillna(0).max() > 0
            rows.append({"iso": iso, "year": year, "runup3": runup,
                         "drawdown2y": drawdown, "credit": r.creditToGdpPct,
                         "credit5": r.credit5, "debt": r.debtToGdpPct,
                         "short": r.stir, "crisis": int(future)})
    return pd.DataFrame(rows)


def _model(c=.2):
    return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                         LogisticRegression(C=c, max_iter=5000, random_state=20261015))


def fit(root: Path):
    panel = build_panel(root)
    oof = np.zeros(len(panel))
    splitter = LeaveOneGroupOut()
    for train, test in splitter.split(panel, panel.crisis, panel.iso):
        m = _model().fit(panel.iloc[train][FEATURES], panel.iloc[train].crisis)
        oof[test] = m.predict_proba(panel.iloc[test][FEATURES])[:, 1]
    base = np.full(len(panel), panel.crisis.mean())
    final = _model().fit(panel[FEATURES], panel.crisis)
    latest_us = panel[panel.iso == "USA"].sort_values("year").iloc[-1][FEATURES].to_dict()
    # Comparable JST loan/GDP and five-year credit change stay on the JST perimeter;
    # current debt, policy-rate and run-up values are overlaid by the release model.
    latest_us.update({"runup3": 2.17, "debt": 118.8, "short": 4.25})
    curve = []
    for dd in [-.20, -.35, -.50, -.65, -.75]:
        x = pd.DataFrame([{**latest_us, "drawdown2y": dd}])[FEATURES]
        curve.append({"drawdown": dd, "probability": float(final.predict_proba(x)[0, 1])})
    audit = {
        "rows": int(len(panel)), "countries": int(panel.iso.nunique()),
        "crises": int(panel.crisis.sum()), "crisisRate": float(panel.crisis.mean()),
        "severeRows": int((panel.drawdown2y <= -.5).sum()),
        "severeCrisisRows": int(panel.loc[panel.drawdown2y <= -.5, "crisis"].sum()),
        "validation": {
            "scheme": "leave-one-country-out",
            "brier": float(brier_score_loss(panel.crisis, oof)),
            "baseRateBrier": float(brier_score_loss(panel.crisis, base)),
            "logLoss": float(log_loss(panel.crisis, oof)),
            "auc": float(roc_auc_score(panel.crisis, oof)),
        },
        "features": FEATURES, "regularizationC": .2,
        "currentBalanceSheetCurve": curve,
        "warning": "Annual equity closes understate intrayear drawdowns. The panel ranks transition risk well, but it contains few independent global crash clusters and no historical AI-capex analogue."
    }
    return final, panel, latest_us, audit


def predict(model, template, drawdowns):
    x = pd.DataFrame([{**template, "drawdown2y": float(d)} for d in np.asarray(drawdowns)])[FEATURES]
    return model.predict_proba(x)[:, 1]
