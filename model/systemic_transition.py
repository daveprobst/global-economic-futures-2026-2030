"""Calibrated equity-loss -> banking-crisis transition model on the same four-year window.

Question answered: given the worst real equity drawdown at annual closes over the next
four years and the balance-sheet state at the start, how often did a systemic banking
crisis begin inside that window? Panel: every country-year in the JST Macrohistory
database (17 economies, 1870-2016 origins) with a consistent annual equity record.
It is a transition model, not an equity-crash probability model.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
import equity_panel as EP

FEATURES = ["drawdown", "runup3", "credit", "credit5", "debt", "short"]
HORIZON = EP.HORIZON


def build_panel(root: Path, horizon: int = HORIZON) -> pd.DataFrame:
    j = EP.jst_frame()
    j["credit"] = 100 * j.tloans / j.gdp
    j["debt"] = 100 * j.debtgdp
    rows = []
    for iso, g in j.groupby("iso"):
        g = g.sort_values("year").set_index("year")
        g["credit5"] = g.credit - g.credit.shift(5)
        ok = g.real_ret.dropna()
        years = ok.index.to_numpy(); ret = ok.to_numpy(); infl = g.infl.reindex(ok.index).to_numpy()
        index = np.cumprod(1 + ret)
        for i in range(3, len(ok) - horizon):
            if np.any(np.diff(years[i - 3:i + horizon + 1]) != 1): continue
            if np.any(np.isnan(infl[i - 3:i + horizon + 1])) or np.any(infl[i - 3:i + horizon + 1] > EP.INFLATION_CAP): continue
            y = int(years[i]); fwd = index[i:i + horizon + 1]
            crisis = g.loc[y:y + horizon, "crisisJST"].fillna(0).max() > 0
            rows.append({"iso": iso, "year": y, "runup3": float(index[i] / index[i - 3] - 1),
                         "drawdown": float(fwd.min() / fwd[0] - 1), "credit": g.credit.get(y, np.nan),
                         "credit5": g.credit5.get(y, np.nan), "debt": g.debt.get(y, np.nan),
                         "short": g.stir.get(y, np.nan), "crisis": int(crisis)})
    return pd.DataFrame(rows)


def _model(c=.2):
    return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                         LogisticRegression(C=c, max_iter=5000, random_state=20261015))


def fit(root: Path):
    panel = build_panel(root)
    oof = np.zeros(len(panel))
    for train, test in LeaveOneGroupOut().split(panel, panel.crisis, panel.iso):
        m = _model().fit(panel.iloc[train][FEATURES], panel.iloc[train].crisis)
        oof[test] = m.predict_proba(panel.iloc[test][FEATURES])[:, 1]
    # Time-block check: leave one 25-year block out so no era trains its own test.
    block = (panel.year // 25).to_numpy(); oob = np.zeros(len(panel))
    for b in np.unique(block):
        tr, te = block != b, block == b
        m = _model().fit(panel[tr][FEATURES], panel[tr].crisis)
        oob[te] = m.predict_proba(panel[te][FEATURES])[:, 1]
    base = np.full(len(panel), panel.crisis.mean())
    final = _model().fit(panel[FEATURES], panel.crisis)
    us = panel[panel.iso == "USA"].sort_values("year").iloc[-1][FEATURES].to_dict()
    # Current US overlays: public debt/GDP and policy rate; the run-up is overridden by the caller.
    us.update({"debt": 118.8, "short": 4.25})
    curve = [{"drawdown": dd, "probability": float(final.predict_proba(pd.DataFrame([{**us, "drawdown": dd}])[FEATURES])[0, 1])}
             for dd in (-.20, -.35, -.50, -.65, -.75)]
    sev = panel.drawdown <= -.5
    audit = {
        "rows": int(len(panel)), "countries": int(panel.iso.nunique()), "firstOrigin": int(panel.year.min()), "lastOrigin": int(panel.year.max()),
        "crisisWindows": int(panel.crisis.sum()), "crisisRate": float(panel.crisis.mean()),
        "severeRows": int(sev.sum()), "severeCrisisRows": int(panel.loc[sev, "crisis"].sum()),
        "validation": {
            "leaveOneCountryOut": {"brier": float(brier_score_loss(panel.crisis, oof)), "baseRateBrier": float(brier_score_loss(panel.crisis, base)),
                                    "logLoss": float(log_loss(panel.crisis, oof)), "auc": float(roc_auc_score(panel.crisis, oof))},
            "leaveOneEraOut": {"brier": float(brier_score_loss(panel.crisis, oob)), "baseRateBrier": float(brier_score_loss(panel.crisis, base)),
                                "auc": float(roc_auc_score(panel.crisis, oob)), "blocks": "25-year blocks"}},
        "features": FEATURES, "regularizationC": .2, "currentBalanceSheetCurve": curve,
        "warning": "Annual closes understate intrayear drawdowns. Credit inputs are the latest JST vintage; independent global crash clusters are few."}
    return final, panel, us, audit


def predict(model, template, drawdowns):
    x = pd.DataFrame([{**template, "drawdown": float(d)} for d in np.asarray(drawdowns)])[FEATURES]
    return model.predict_proba(x)[:, 1]
