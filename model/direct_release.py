"""Release model: scenario weights, connected stress paths, hysteresis and historical checks.

One window throughout: from the 31 Oct 2026 as-of date to 31 December 2030. Every scenario
probability is the probability of that outcome over the whole window; every macro path runs
2026 (baseline year) to 2030. Inputs are open data (World Bank, JST Macrohistory) fetched by
fetch_data.py plus the frozen state/US/China inputs in model/inputs. Outputs go to site/data.

Run:  python model/fetch_data.py && python model/direct_release.py
Outputs are model-conditional scenarios, not unconditional forecasts or investment advice.
"""
from __future__ import annotations
import json, math, sys
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.preprocessing import StandardScaler

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import equity_panel as EP
import systemic_transition as ST
import engine as E
import hysteresis as H
import checks as CK

OUT = ROOT / "site/data"
SEED = 20261014; DRAWS = 10_000; PATHS = 4000
ASOF = "2026-10-31"; WINDOW = "31 Oct 2026 – 31 Dec 2030"
STATES = [("calm", "ample"), ("calm", "neutral"), ("calm", "vacuum"), ("tense", "ample"), ("tense", "neutral"), ("tense", "vacuum"),
          ("crisis", "ample"), ("crisis", "neutral"), ("crisis", "vacuum")]
SCEN = list(E.SEVERITY)
NAMES = {"continued_boom": "Boom holds", "no_burst_sideways": "Contained repricing", "mild_adjustment": "Mild adjustment",
         "moderate_burst": "Moderate burst", "deep_drawdown_no_vacuum": "Deep drawdown, liquidity holds",
         "severe_burst": "Severe burst + liquidity vacuum", "severe_burst_with_financial_crisis": "Severe burst + banking crisis"}
HURDLE = f"{EP.BOOM_REAL_PER_YEAR*100:.0f}%"


def inp(name): return json.loads((HERE / "inputs" / name).read_text())
def clean(x):
    if isinstance(x, dict): return {str(k): clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)): return [clean(v) for v in x]
    if isinstance(x, (np.floating, float)): return float(x) if math.isfinite(float(x)) else None
    if isinstance(x, np.integer): return int(x)
    if isinstance(x, np.ndarray): return clean(x.tolist())
    if isinstance(x, np.bool_): return bool(x)
    return x
def dump(name, obj): OUT.mkdir(parents=True, exist_ok=True); (OUT / f"{name}.json").write_text(json.dumps(clean(obj), indent=1, allow_nan=False) + "\n")
def logit(p): p = np.clip(p, 1e-6, 1 - 1e-6); return np.log(p / (1 - p))
def logistic(x): return 1 / (1 + np.exp(-x))
def series(indicator, iso): d = pd.read_csv(ROOT / f"data/derived/series/WB_{indicator}_{iso}.csv"); return pd.Series(d.value.to_numpy(), index=d.date.astype(str).str[:4].astype(int))
def bands(a, years=E.YEARS): return [{"year": y, "p10": float(np.quantile(a[:, i], .1)), "p50": float(np.quantile(a[:, i], .5)), "p90": float(np.quantile(a[:, i], .9))} for i, y in enumerate(years)]


def current_features():
    us = inp("us_ai_decomposition.json")
    s = pd.Series({pd.Period(x["month"][:7], freq="M"): x["value"] for x in us["basket"]["indexMonthly"]}).sort_index()
    nominal = np.array([s.iloc[-1 - 12 * i] / s.iloc[-1 - 12 * (i + 1)] - 1 for i in range(5)])
    cpi = series("FP.CPI.TOTL.ZG", "USA")
    defl = float(series("NY.GDP.DEFL.KD.ZG", "USA").loc[2025])   # CPI ends 2024; 2025 deflator stands in for 2025 and 2026
    pi = [defl, defl] + [float(cpi.loc[y]) for y in (2024, 2023, 2022)]
    real = (1 + nominal) / (1 + np.array(pi) / 100) - 1
    feats = np.array([np.prod(1 + real[:3]) - 1, real[0], real.std()])  # third value is shown, not modelled
    return feats, {"nominalRunup3": float(np.prod(1 + nominal[:3]) - 1), "usInflationAssumed": pi, "realFeatures": [float(x) for x in feats]}, us


def fit_probs(df, features):
    ps = []
    for _, c in EP.MODEL_CONFIGS:
        sc = StandardScaler().fit(df[list(EP.PREDICTORS)])
        m = LogisticRegression(C=c, solver="lbfgs", max_iter=3000, random_state=SEED).fit(sc.transform(df[list(EP.PREDICTORS)]), df.band)
        raw = m.predict_proba(sc.transform(pd.DataFrame([features[:2]], columns=EP.PREDICTORS)))[0]
        p = {b: 1e-9 for b in EP.BANDS}; p.update(dict(zip(m.classes_, raw))); ps.append(p)
    return {b: float(np.mean([p[b] for p in ps])) for b in EP.BANDS}


def fit_challengers(df, features):
    X = df[list(EP.PREDICTORS)]; y = df.band; out = []
    for m in (GradientBoostingClassifier(n_estimators=80, max_depth=2, learning_rate=.035, subsample=.8, random_state=SEED),
              RandomForestClassifier(n_estimators=500, max_depth=4, min_samples_leaf=5, max_features=.8, class_weight="balanced", random_state=SEED, n_jobs=-1)):
        m.fit(X, y); raw = m.predict_proba(pd.DataFrame([features[:2]], columns=EP.PREDICTORS))[0]
        p = {b: 1e-9 for b in EP.BANDS}; p.update(dict(zip(m.classes_, raw))); out.append(p)
    return out


def bust_of(p): return sum(p[b] for b in EP.BANDS[1:])


def platt(df):
    """Calibrate the blended bust probability on country-out predictions (no in-sample fit)."""
    F = list(EP.PREDICTORS); y = (df.band != "none").astype(int).to_numpy(); oof = np.zeros(len(df))
    for c in df.country.unique():
        te = (df.country == c).to_numpy(); tr = ~te
        sc = StandardScaler().fit(df[tr][F]); lg = LogisticRegression(C=.2, max_iter=3000, random_state=SEED).fit(sc.transform(df[tr][F]), y[tr])
        gb = GradientBoostingClassifier(n_estimators=80, max_depth=2, learning_rate=.035, subsample=.8, random_state=SEED).fit(df[tr][F], y[tr])
        rf = RandomForestClassifier(n_estimators=200, max_depth=4, min_samples_leaf=5, max_features=1.0, random_state=SEED, n_jobs=-1).fit(df[tr][F], y[tr])
        oof[te] = .75 * lg.predict_proba(sc.transform(df[te][F]))[:, 1] + .15 * gb.predict_proba(df[te][F])[:, 1] + .10 * rf.predict_proba(df[te][F])[:, 1]
    z = logit(oof).reshape(-1, 1); pl = LogisticRegression(C=1e6).fit(z, y)
    return float(pl.intercept_[0]), float(pl.coef_[0][0]), float(np.mean((oof - y) ** 2)), float(np.mean((y.mean() - y) ** 2))


def apply_cal(base, a, b):
    raw = bust_of(base); cal = float(logistic(a + b * logit(raw)))
    out = {k: base[k] * cal / raw for k in EP.BANDS[1:]}; out["none"] = 1 - cal
    return out


def conditional(base, mult, continue_share, tail_share):
    bust0 = base["mild"] + base["moderate"] + base["severe"]
    bust = float(logistic(logit(bust0) + math.log(max(mult, .05))))
    within = np.array([base["mild"], base["moderate"], base["severe"]]); within /= within.sum()
    mild, moderate, severe = (bust * within).tolist(); none = 1 - bust
    out = {"continued_boom": none * continue_share, "no_burst_sideways": none * (1 - continue_share), "mild_adjustment": mild,
           "moderate_burst": moderate, "deep_drawdown_no_vacuum": severe * tail_share[0], "severe_burst": severe * tail_share[1],
           "severe_burst_with_financial_crisis": severe * tail_share[2]}
    z = sum(out.values()); return {k: v / z for k, v in out.items()}


def build_scenarios(df, features, feat_audit, systemic_bundle):
    systemic_model, _, systemic_template, systemic_audit = systemic_bundle
    linear = fit_probs(df, features); gb, rf = fit_challengers(df, features)
    raw_base = {b: .75 * linear[b] + .15 * gb[b] + .10 * rf[b] for b in EP.BANDS}
    cal_a, cal_b, oof_brier, base_brier = platt(df)
    base = apply_cal(raw_base, cal_a, cal_b)
    shift = float(logit(bust_of(raw_base)) - logit(bust_of(linear)))
    st = inp("states.json"); weights = np.array(st["windowStartWeights_pi"], float); weights /= weights.sum()
    geo = {"calm": .88, "tense": 1.0, "crisis": 1.18}; liq = {"ample": .62, "neutral": 1.0, "vacuum": 2.75}
    none = df[df.band == "none"]; boom_n = int((none.outcome == "boom").sum()); side_n = int(len(none) - boom_n)
    side_alpha = np.array([boom_n + .5, side_n + .5]); continue_share = float(side_alpha[0] / side_alpha.sum())
    grid = np.linspace(-.76, -.50, 81); w = np.exp(-.5 * ((grid + .62) / .075) ** 2); w /= w.sum()
    systemic_share = float(np.sum(ST.predict(systemic_model, systemic_template, grid) * w))
    vac = .20
    tail = np.array([(1 - systemic_share) * (1 - vac), (1 - systemic_share) * vac, systemic_share])
    rows = [{"geopolitics": g, "liquidity": l, "stressMultiplier": geo[g] * liq[l],
             "probabilities": conditional(base, geo[g] * liq[l], continue_share, tail)} for g, l in STATES]
    point = {k: sum(weights[i] * rows[i]["probabilities"][k] for i in range(9)) for k in SCEN}
    rng = np.random.default_rng(SEED)
    labels = rng.choice(SCEN, size=DRAWS, p=[point[k] for k in SCEN])
    # Year-cluster bootstrap: simultaneous global crashes are one draw, not thirty.
    ys = df.originYear.unique(); groups = {y: df[df.originYear == y] for y in ys}; boots = []
    for _ in range(300):
        sample = pd.concat([groups[y] for y in rng.choice(ys, len(ys))], ignore_index=True)
        try:
            pb = fit_probs(sample, features * rng.normal(1, [.05, .10, .10], 3))
            rb = bust_of(pb); pb = apply_cal({k: v * float(logistic(logit(rb) + shift)) / rb for k, v in pb.items() if k != 'none'} | {'none': 1 - float(logistic(logit(rb) + shift))}, cal_a, cal_b)
        except Exception: continue
        nb = sample[sample.band == "none"]; bn = int((nb.outcome == "boom").sum())
        cb = float(rng.beta(bn + .5, len(nb) - bn + .5)); wb = rng.dirichlet(weights * 250 + 1)
        ps = float(rng.beta(systemic_share * 16 + .5, (1 - systemic_share) * 16 + .5)); pv = float(rng.beta(2.5, 10.5))
        tb = np.array([(1 - ps) * (1 - pv), (1 - ps) * pv, ps]); vals = {k: 0. for k in SCEN}
        for i, (g, l) in enumerate(STATES):
            q = conditional(pb, geo[g] * liq[l] * rng.lognormal(0, .16), cb, tb)
            for k in SCEN: vals[k] += wb[i] * q[k]
        boots.append(vals)
    intervals = {k: [float(np.quantile([x[k] for x in boots], .1)), float(np.quantile([x[k] for x in boots], .9))] for k in SCEN}
    defs = {
        "continued_boom": (-.20, f"No 20% fall at any annual close to end-2030, and real returns of at least {HURDLE} a year."),
        "no_burst_sideways": (-.20, f"No 20% fall at any annual close, but real returns below {HURDLE} a year."),
        "mild_adjustment": (-.20, "Worst annual-close fall of 20–35%."), "moderate_burst": (-.35, "Worst annual-close fall of 35–50%."),
        "deep_drawdown_no_vacuum": (-.50, "Fall of 50% or more; funding markets keep working."),
        "severe_burst": (-.50, "Fall of 50% or more plus a dollar-liquidity vacuum."),
        "severe_burst_with_financial_crisis": (-.50, "Fall of 50% or more, liquidity vacuum and a banking crisis.")}
    sev_rows = df[df.band == "severe"]
    clusters = []
    for y in sorted(sev_rows.originYear.unique()):
        if not clusters or y - clusters[-1][-1] > 2: clusters.append([int(y)])
        else: clusters[-1].append(int(y))
    scenarios = [{"id": k, "name": NAMES[k], "class": k, "description": defs[k][1], "probability": point[k], "interval80": intervals[k],
                  "definition": {"drawdownThreshold": defs[k][0], "window": WINDOW, "closes": EP.HORIZON}} for k in SCEN]
    cv = None
    tree = {"asOf": ASOF, "window": WINDOW, "status": "model_conditional", "scenarios": scenarios,
            "drivers": [{"id": "ai_runup_36m", "label": "AI basket 3-year real run-up", "currentValue": float(features[0] * 100), "unit": "percent"},
                        {"id": "ai_return_12m", "label": "AI basket 12-month real return", "currentValue": float(features[1] * 100), "unit": "percent"},
                        {"id": "hy_oas", "label": "US high-yield spread", "currentValue": 3.16, "unit": "percent", "sourceRef": "FRED:BAMLH0A0HYM2"},
                        {"id": "china_property", "label": "China property decline from peak", "currentValue": 22.61, "unit": "percent", "sourceRef": "BIS:WS_SPP"}],
            "stateProbabilities": [{"geopolitics": g, "liquidity": l, "probability": float(weights[i])} for i, (g, l) in enumerate(STATES)],
            "conditionalProbabilities": rows,
            "method": {"estimator": "75% ridge-logit core, 15% gradient boosting, 10% random forest, calibrated on country-out predictions; year-cluster bootstrap",
                       "calibration": {"intercept": cal_a, "slope": cal_b, "countryOutBrierBlend": oof_brier, "countryOutBrierBaseRate": base_brier, "bustProbabilityRawBlend": bust_of(raw_base), "bustProbabilityCalibrated": bust_of(base)},
                       "predictors": list(EP.PREDICTORS),
                       "episodeCount": int(len(df)), "countries": int(df.country.nunique()), "originYears": int(df.originYear.nunique()),
                       "sources": {"modern": int((df.source == "modern").sum()), "history": int((df.source == "history").sum())},
                       "conditioning": "monotonic geopolitical × dollar-liquidity stress surface",
                       "currentFeatures": {"runup3": float(features[0]), "return1": float(features[1]), "volatility5": float(features[2])},
                       "featureAudit": feat_audit,
                       "challengerBustProbabilities": {"logit": sum(linear[b] for b in EP.BANDS[1:]), "gradientBoosting": sum(gb[b] for b in EP.BANDS[1:]),
                                                       "randomForest": sum(rf[b] for b in EP.BANDS[1:])},
                       "transitionAudit": {"boomObserved": boom_n, "sidewaysObserved": side_n, "nonBustObserved": int(len(none)),
                                           "boomShareOfNonBust": continue_share, "severeEpisodes": int(len(sev_rows)), "independentSevereClusters": len(clusters),
                                           "severeClusters": clusters,
                                           "tailShare": {"deepNoVacuum": float(tail[0]), "vacuumNoSystemic": float(tail[1]), "systemic": float(tail[2])},
                                           "tailMethod": "Banking-crisis transition integrated over 50–76% drawdowns; 20% of non-systemic severe paths are assigned a temporary liquidity vacuum.",
                                           "systemicTransition": systemic_audit},
                       "warning": "Global crash clusters are scarce; odds are scenario weights, not precise frequencies."},
            "monteCarlo": {"draws": DRAWS, "seed": SEED, "maxStdError": float(max(math.sqrt(point[k] * (1 - point[k]) / DRAWS) for k in SCEN)),
                           "classificationCounts": {k: int(np.sum(labels == k)) for k in SCEN}}}
    return tree, boots, weights, point


def classify_paths(tree, boots):
    """Unified simulation + calibration. Returns everything the output builders need."""
    cpi = series("NY.GDP.MKTP.KD.ZG", "CHN"); g = cpi[(cpi.index >= 2012) & ~cpi.index.isin([2020, 2021, 2022])]
    slope = float(np.polyfit(g.index, g.values, 1)[0]); last = float(cpi.loc[2025])
    cn_base = E.china_baseline(slope, last); cn_defl = float(series("NY.GDP.DEFL.KD.ZG", "CHN").loc[2025])
    targets = H.class_table(H.shortfall_panel()); cohorts = H.crisis_cohorts()
    fins_cal = {s: E.simulate_finance(s, 2000, SEED + i) for i, s in enumerate(SCEN)}
    params, calib = H.calibrate(fins_cal, targets, cohorts, cn_base, cn_defl)
    fins = {s: E.simulate_finance(s, PATHS, SEED + 7 + i) for i, s in enumerate(SCEN)}
    macros = {s: E.macro(fins[s], params, cn_base, cn_defl) for s in SCEN}
    return fins, macros, params, calib, targets, cohorts, cn_base, cn_defl, slope


def build_connected(tree, fins, macros, systemic_bundle, boots):
    systemic_model, _, systemic_template, systemic_audit = systemic_bundle
    result, path_stats = {}, {}
    for i, sc in enumerate(SCEN):
        f, m = fins[sc], macros[sc]; n = f["exp"].shape[0]; rng = np.random.default_rng(SEED + 99 + i)
        us_flag = np.full(n, sc == "severe_burst_with_financial_crisis", dtype=bool)
        china_old = 5.0 - 2.85 * f["ch"] - 1.85 * f["out"] - .45 * f["sale"] + rng.normal(0, .32, (n, 5))
        low_growth = np.maximum(0, 2 - np.minimum(china_old[:, 1], china_old[:, 2]))
        maxout, maxch, maxliq, maxlgfv = f["out"].max(1), f["ch"].max(1), f["liq"].max(1), f["lgfv"].max(1)
        p_ch = logistic(-5.80 + 2.6 * maxout + 1.5 * maxch + .25 * (maxlgfv - 5) + .70 * maxliq + .24 * low_growth + 1.30 * us_flag)
        ch_flag = rng.random(n) < p_ch; joint = us_flag & ch_flag; either = us_flag | ch_flag
        path_stats[sc] = {"paths": n, "usSystemic": float(us_flag.mean()), "chinaCrisis": float(ch_flag.mean()), "joint": float(joint.mean()), "either": float(either.mean()),
                          "chinaGivenUs": float(joint.sum() / max(1, us_flag.sum())), "usGivenChina": float(joint.sum() / max(1, ch_flag.sum())),
                          "medianMaxLiquidity": float(np.median(maxliq)), "medianDrawdown": float(np.median(1 - f["equity"].min(1) / 100)),
                          "medianMinCoverage": float(np.median(f["cov"].min(1)))}
        us, cn, eu = m["US"], m["China"], m["EU"]
        result[sc] = {k: bands(v) for k, v in {
            "aiRevenueExpectations": f["exp"], "usEquityIndex": f["equity"], "marginCallPressure": f["marg"], "liquidityStress": f["liq"],
            "hyperscalerMarginalRate": f["tech"], "cashFlowCoverage": f["cov"], "treasurySalePressure": f["sale"], "chinaCapitalOutflow": f["out"],
            "lgfvRefinancingRate": f["lgfv"], "chinaBalanceSheetStress": f["ch"], "usGdpGrowth": us["growth"], "chinaGdpGrowth": cn["growth"],
            "euGdpGrowth": eu["growth"], "usOutputVsTrend": us["level"], "chinaOutputVsTrend": cn["level"], "usPermanentLoss": us["scar"],
            "chinaPermanentLoss": cn["scar"], "usUnemployment": us["u"]}.items()}
    probs = {x["id"]: x["probability"] for x in tree["scenarios"]}
    mix = {k: sum(probs[s] * path_stats[s][k] for s in SCEN) for k in ["usSystemic", "chinaCrisis", "joint", "either"]}
    mix["chinaGivenUs"] = mix["joint"] / max(mix["usSystemic"], 1e-9); mix["usGivenChina"] = mix["joint"] / max(mix["chinaCrisis"], 1e-9)
    mixInt = {k: [float(np.quantile([sum(b[s] * path_stats[s][k] for s in SCEN) for b in boots], q)) for q in (.1, .9)] for k in ["usSystemic", "chinaCrisis", "joint", "either"]}
    rng = np.random.default_rng(SEED + 7); spreads = [3, 4, 5, 6.5, 8, 10, 12, 14]; properties = [15, 20, 25, 30, 35, 40]; grid = []
    for prop in properties:
        row = []
        for oas in spreads:
            m_ = 6000; z = rng.normal(size=m_); uu = logistic(z); uc = logistic(.62 * z + np.sqrt(1 - .62 ** 2) * rng.normal(size=m_))
            dd = np.clip(.30 + .035 * (oas - 3) + rng.normal(0, .055, m_), .20, .82)
            pu = logistic(logit(ST.predict(systemic_model, systemic_template, -dd)) + .17 * (oas - 4)); usf = uu < pu
            pc = logistic(-3.7 + .105 * (prop - 20) + .22 * (oas - 4) + 1.2 * usf); chf = uc < pc
            row.append(float(np.mean(usf & chf)))
        grid.append(row)
    grid = np.maximum.accumulate(np.maximum.accumulate(np.asarray(grid), axis=0), axis=1).tolist()
    doc = {"asOf": ASOF, "window": WINDOW, "status": "connected_structural_stress_simulation", "scenarios": result, "pathClassification": path_stats,
           "mixture": mix, "mixtureInterval80": mixInt, "systemicTransition": systemic_audit,
           "reverseStress": {"condition": "AI revenue-expectation reset; probabilities are conditional on it, not current-trajectory odds",
                             "x": {"label": "US high-yield OAS (%)", "values": spreads}, "y": {"label": "China property decline from peak (%)", "values": properties},
                             "values": grid, "copulaCorrelation": .62},
           "variables": {
               "aiRevenueExpectations": "Index, 1 = baseline: expected AI revenue relative to what current valuations and capex commitments need",
               "usEquityIndex": "2026 = 100; valuation loss plus forced-sale feedback", "marginCallPressure": "0–1; activated by incremental collateral loss",
               "liquidityStress": "0–1 shared state: coverage shortfall, margin calls and Treasury-sale pressure", "hyperscalerMarginalRate": "Illustrative marginal all-in funding rate, %",
               "cashFlowCoverage": "Operating cash generation ÷ sticky capex and power commitments", "treasurySalePressure": "0–1 foreign-official sale stress, not a forecast of intent",
               "chinaCapitalOutflow": "0–1 external-funding and capital-flight stress", "lgfvRefinancingRate": "Illustrative marginal refinancing rate, %",
               "chinaBalanceSheetStress": "0–1 property and LGFV balance-sheet state", "usOutputVsTrend": "Real GDP vs its pre-shock trend, %",
               "usPermanentLoss": "Hysteresis: part of the output loss that does not close, % of trend"},
           "classification": {"usSystemic": "Banking-crisis branch of the scenario partition (calibrated equity-loss → banking-crisis transition).",
                              "chinaCrisis": "Latent threshold on outflow, balance-sheet stress, refinancing cost, shared liquidity and the US crisis flag.",
                              "joint": "Both flags on the same path inside the window ending 31 Dec 2030."},
           "feedbackLoops": ["AI revenue expectations ↓ → coverage of capex commitments ↓ → marginal funding rate ↑",
                             "Equities ↓ → collateral loss → margin calls and forced sales ↑ → market liquidity ↓ → equities ↓",
                             "Dollar liquidity ↓ and China balance-sheet stress ↑ → capital outflow ↑ → LGFV refinancing premium ↑",
                             "China outflow and fiscal stress → Treasury-sale pressure ↑ → US liquidity and term premium ↑",
                             "A China crisis raises US banking-crisis risk; a US banking crisis raises China crisis risk",
                             "Output losses persist: impaired credit, cancelled investment and displaced workers lower potential output (hysteresis)"],
           "warning": "The banking-crisis transition and hysteresis targets are statistically calibrated on JST history. China and cross-border elasticities are transparent stress parameters, not identified causal estimates."}
    dump("connected_system", doc); return doc, path_stats


def build_paths(tree, fins, macros):
    out = {}
    for sc in SCEN:
        f, m = fins[sc], macros[sc]; us, cn, eu = m["US"], m["China"], m["EU"]; q = {}
        spread = 3.2 + 5.6 * f["liq"] + 1.4 * f["marg"]
        def region(name, growth, level, scar, unemp, beta, base_g, infl_base=2.5):
            idx = 100 * np.cumprod(1 + growth / 100, axis=1)
            eq = 100 + (f["equity"] - 100) * beta
            return {"gdpGrowth": bands(growth), "realGdpIndex": bands(idx), "outputVsTrend": bands(level), "permanentLoss": bands(scar),
                    "unemployment": bands(unemp), "equityIndex": bands(eq), "creditSpread": bands(3.2 + (spread - 3.2) * beta),
                    "inflation": bands(infl_base + .08 * level * beta)}
        q["US"] = region("US", us["growth"], us["level"], us["scar"], us["u"], 1.0, E.US_G0)
        q["China"] = region("China", cn["growth"], cn["level"], cn["scar"], np.full_like(cn["gap"], E.UNEMP0["China"]) + 0.3 * np.maximum(0, -cn["level"]), .82, 4.96)
        q["EU"] = region("EU", eu["growth"], eu["level"], eu["scar"], eu["u"], .68, E.EU_G0)
        sw_g = E.CH_G0 + (us["growth"] - E.US_G0) * .48
        q["Switzerland"] = region("Switzerland", sw_g, us["level"] * .48, us["scar"] * .48, E.UNEMP0["Switzerland"] + (us["u"] - E.UNEMP0["US"]) * .48, .48, E.CH_G0)
        sev = "severe" in sc or "deep" in sc
        q["benchmark"] = {"label": "Severity check", "text": ("Median US peak-to-trough real-GDP fall is compared with the 2007–09 contraction (BEA: −4.0%) and the Federal Reserve 2026 severely adverse path (−4.6%)." if sev
                          else "Conditional regime path. Bands show propagation uncertainty within the scenario, not the probability of the scenario."), "sources": ["Federal Reserve 2026 Stress Test Scenarios", "BEA FAQ 1004"]}
        out[sc] = q
    doc = {"asOf": ASOF, "window": WINDOW, "status": "unified_connected_simulation", "scenarios": out,
           "method": f"{PATHS:,} paths per scenario from one shared state. Growth = baseline + output-gap change − hysteresis flow. Bands describe within-scenario propagation uncertainty."}
    dump("scenario_paths", doc); return doc


def build_hysteresis(tree, fins, macros, params, calib, targets, cohorts, cn_base, cn_defl, slope):
    probs = {x["id"]: x["probability"] for x in tree["scenarios"]}; per = {}
    for sc in SCEN:
        m = macros[sc]; us, cn, eu = m["US"], m["China"], m["EU"]
        cum = np.cumsum(us["growth"][:, 1:], axis=1)
        flows_us = {k: float(np.mean(w * us[k][:, 1:])) for k, w in (("C", .45), ("I", .30), ("U", .25))}; tot = sum(flows_us.values()) or 1
        flows_cn = {k: float(np.mean(w * cn[k][:, 1:])) for k, w in (("D", .40), ("B", .35), ("F", .25))}; totc = sum(flows_cn.values()) or 1
        yr_cross = lambda a, thr: next((E.YEARS[t] for t in range(5) if np.median(a[:, t]) >= thr), None)
        per[sc] = {
            "probability": probs[sc],
            "us": {"outputVsTrend2030": [float(np.percentile(us["level"][:, 4], q)) for q in (10, 50, 90)],
                   "troughFromOrigin": float(np.median(np.minimum(cum.min(axis=1), 0))),
                   "permanentLoss2030": float(np.median(us["scar"][:, 4])), "outputVsTrend2036NoNewShock": float(np.median(m["ext"]["US"][0])),
                   "permanentLoss2036": float(np.median(m["ext"]["US"][1])), "peakUnemployment": float(np.median(us["u"].max(axis=1))),
                   "potentialGrowth2030": float(E.US_G0 - np.median(us["flow"][:, 4])), "firstYearLossAbove1pct": yr_cross(us["scar"], 1.0),
                   "channelShare": {"creditAllocation": flows_us["C"] / tot, "investmentCancelled": flows_us["I"] / tot, "labourDisplaced": flows_us["U"] / tot}},
            "china": {"outputVsTrend2030": [float(np.percentile(cn["level"][:, 4], q)) for q in (10, 50, 90)],
                      "permanentLoss2030": float(np.median(cn["scar"][:, 4])), "outputVsTrend2036NoNewShock": float(np.median(m["ext"]["China"][0])),
                      "permanentLoss2036": float(np.median(m["ext"]["China"][1])), "potentialGrowth2030": float(cn_base[4] - np.median(cn["flow"][:, 4])),
                      "baselineGrowth2030": float(cn_base[4]), "firstYearLossAbove1pct": yr_cross(cn["scar"], 1.0),
                      "channelShare": {"debtDeflation": flows_cn["D"] / totc, "balanceSheet": flows_cn["B"] / totc, "capitalOutflow": flows_cn["F"] / totc}},
            "eu": {"outputVsTrend2030": [float(np.percentile(eu["level"][:, 4], q)) for q in (10, 50, 90)], "permanentLoss2030": float(np.median(eu["scar"][:, 4]))}}
    sysm = "severe_burst_with_financial_crisis"
    path = {r: {k: [float(np.median(macros[sysm][r][k][:, t])) for t in range(5)] for k in ("level", "scar", "growth")} for r in ("US", "China")}
    mixed = {}
    for r, key in (("US", "us"), ("China", "china")):
        lv = np.concatenate([np.random.default_rng(SEED).choice(macros[s][r]["level"][:, 4], int(round(probs[s] * 20000)) or 1) for s in SCEN])
        mixed[key] = {"outputVsTrend2030": [float(np.percentile(lv, q)) for q in (10, 50, 90)], "probabilityLoss5pct": float(np.mean(lv < -5)), "probabilityLoss10pct": float(np.mean(lv < -10))}
    sys_lv = macros[sysm]["US"]["level"][:, 4]; emp = targets["deep_with_crisis"]
    validation = {"modelSystemicUS": {"p10": float(np.percentile(sys_lv, 10)), "p25": float(np.percentile(sys_lv, 25)), "p50": float(np.percentile(sys_lv, 50))},
                  "historicalSameClass": {k: emp[k] for k in ("n", "p10", "p25", "p50", "mean")},
                  "gfcUS": [x for x in cohorts["gfcCohort"] if x["iso"] == "USA"]}
    indicators = [
        {"economy": "US", "indicator": "High-yield spread", "now": 3.16, "unit": "% OAS", "watch": 6.5, "meaning": "Credit-allocation channel switches on above the liquidity-vacuum boundary."},
        {"economy": "US", "indicator": "Federal debt", "now": 118.8, "unit": "% GDP", "watch": 130, "meaning": "Limits fiscal offset; a higher term premium would slow the recovery."},
        {"economy": "US", "indicator": "AI revenue vs capex commitments", "now": 1.65, "unit": "cash-flow coverage ×", "watch": 1.0, "meaning": "Below 1.0 the cancelled-investment channel runs."},
        {"economy": "China", "indicator": "Property prices vs 2021 peak", "now": -22.6, "unit": "%", "watch": -25, "meaning": "The balance-sheet channel strengthens as household and developer wealth falls."},
        {"economy": "China", "indicator": "Private-sector debt service", "now": 19.1, "unit": "% of income", "watch": 22, "meaning": "High servicing leaves less room for investment and consumption."},
        {"economy": "China", "indicator": "GDP deflator", "now": cn_defl, "unit": "% y/y", "watch": 0, "meaning": "Negative deflator means nominal growth is below real growth; debt rises relative to income."},
        {"economy": "China", "indicator": "10-year government yield", "now": 1.8, "unit": "%", "watch": None, "meaning": "Sovereign debt costs less than nominal growth today; the stress sits in LGFV and property debt."}]
    doc = {"asOf": ASOF, "window": WINDOW,
           "definition": "Hysteresis = output that does not return to its pre-shock trend. It is measured as real GDP relative to the pre-shock trend, and as the permanent part that survives a further six years without a new shock (to 2036).",
           "channels": {"US": [{"id": "creditAllocation", "label": "Impaired credit allocation", "driver": "Dollar-liquidity stress and margin-call pressure", "weight": .45},
                               {"id": "investmentCancelled", "label": "Cancelled and stranded investment", "driver": "Cash-flow coverage below baseline", "weight": .30},
                               {"id": "labourDisplaced", "label": "Displaced labour", "driver": "Unemployment above 5%", "weight": .25}],
                        "China": [{"id": "debtDeflation", "label": "Debt-deflation", "driver": "Refinancing rate minus nominal growth", "weight": .40},
                                  {"id": "balanceSheet", "label": "Property and LGFV balance sheets", "driver": "Balance-sheet stress above 0.30", "weight": .35},
                                  {"id": "capitalOutflow", "label": "Lost external funding", "driver": "Capital-outflow stress above 0.30", "weight": .25}]},
           "parameters": params, "calibration": calib, "empiricalClasses": targets, "cohorts": cohorts, "validation": validation,
           "scenarios": per, "systemicMedianPath": path, "weighted": mixed, "chinaBaseline": {"growth": cn_base, "slopePerYear": slope, "deflator2025": cn_defl,
                                                                                     "method": "2025 growth, extended by the 2012–2025 linear trend (2020–22 excluded)"},
           "indicators": indicators,
           "method": ["Targets: JST real GDP per head four years after each origin, vs the ten-year pre-origin trend, grouped by equity drawdown and banking crisis (1900–2016, wars excluded).",
                      "Fitted: one cyclical scale, one hysteresis scale and one catch-up rate for the US so that scenario medians match those classes, the GFC/Fed peak-to-trough benchmark, and the post-war finding that 84% of a five-year banking-crisis shortfall remains after ten years.",
                      "China: a separate scale, anchored to the same banking-crisis class in 2030 and to Japan's ten-year shortfall after 1989 for 2036. One analogue, so the Chinese figures carry wider uncertainty."]}
    dump("hysteresis", doc); return doc


def build_history(paths_doc, macros):
    specs = [("US dot-com unwind", "USA", 2000, 5), ("US GFC", "USA", 2007, 5), ("Euro-area GFC / sovereign aftershock", "EMU", 2007, 7),
             ("Japan post-asset-bubble", "JPN", 1990, 6), ("US pandemic stop", "USA", 2019, 4)]
    analogs = []
    for label, iso, start, n in specs:
        d = pd.read_csv(ROOT / f"data/derived/series/WB_NY.GDP.MKTP.KD.ZG_{iso}.csv"); d["year"] = d.date.astype(str).str[:4].astype(int)
        d["value"] = pd.to_numeric(d.value, errors="coerce"); z = d[d.year.between(start, start + n - 1)].dropna(subset=["value"])
        level = 100 * np.cumprod(1 + z.value.to_numpy() / 100)
        analogs.append({"id": label.lower().replace(" ", "_").replace("/", "_"), "label": label, "region": iso, "startYear": start,
                        "growth": [{"year": int(y), "value": float(g)} for y, g in zip(z.year, z.value)],
                        "realGdpIndex": [{"year": int(y), "value": float(v)} for y, v in zip(z.year, level)],
                        "yearsNegative": int((z.value < 0).sum()), "cumulativeGrowth": float(level[-1] - 100), "source": "World Bank NY.GDP.MKTP.KD.ZG"})
    model = paths_doc["scenarios"]["severe_burst_with_financial_crisis"]["US"]
    trend = [100 * (1 + E.US_G0 / 100) ** k for k in range(5)]
    analogs.append({"id": "model_systemic_2026", "label": "Model: AI bust + banking crisis", "region": "USA model", "startYear": 2026,
                    "growth": [{"year": x["year"], "value": x["p50"]} for x in model["gdpGrowth"]],
                    "realGdpIndex": [{"year": x["year"], "value": x["p50"]} for x in model["realGdpIndex"]],
                    "trendIndex": [{"year": 2026 + k, "value": v} for k, v in enumerate(trend)],
                    "yearsNegative": sum(x["p50"] < 0 for x in model["gdpGrowth"]), "cumulativeGrowth": model["realGdpIndex"][-1]["p50"] - 100, "source": "Conditional model path"})
    doc = {"asOf": ASOF, "metric": "Annual aggregate real GDP growth and chained level", "analogs": analogs,
           "interpretation": "The dot-com crash stayed non-systemic because losses were dispersed. The GFC was nonlinear because losses sat in leveraged intermediaries. Japan shows a balance-sheet recession can suppress the level for a decade without consecutive contractions.",
           "limitations": "Annual data hide intra-year troughs. The pandemic is a magnitude check, not a causal analogue. The model is judged against ranges, not fitted to one episode."}
    dump("historical_validation", doc); return doc


def patch_other(tree, us, connected, hyst, checks):
    dump("china_hidden_debt", inp("china_hidden_debt.json")); dump("us_ai_decomposition", us); dump("contagion", inp("contagion.json"))
    mix, mi = connected["mixture"], connected["mixtureInterval80"]
    j = inp("joint_crisis_base.json")
    j.update({"probabilityCurrentTrajectory": {"point": mix["joint"], "interval80": mi["joint"],
                                                "status": "Probability-weighted path simulation; the interval comes from the year-cluster bootstrap of scenario weights.", "window": WINDOW},
              "marginals": {"usSystemic": mix["usSystemic"], "chinaCrisis": mix["chinaCrisis"], "eitherCrisis": mix["either"],
                            "chinaCrisisConditionalOnUsSystemic": mix["chinaGivenUs"], "usSystemicConditionalOnChinaCrisis": mix["usGivenChina"]},
              "marginalIntervals80": mi, "scenarioPathRates": connected["pathClassification"], "reverseStress": connected["reverseStress"], "drawsPerScenario": PATHS})
    j["dependence"] = {"type": "same-path common shocks plus two-way fixed-point feedback", "strength": connected["reverseStress"]["copulaCorrelation"],
                       "estimationNote": "US transition is calibrated on JST history. China and cross-border elasticities are structural stress parameters."}
    j["boundaryConditions"] = [
        {"variable": "US high-yield OAS", "threshold": 6.5, "unit": "percent", "direction": "above", "currentValue": 3.16, "rationale": "Liquidity-vacuum boundary in the stress grid."},
        {"variable": "Fed reserve balances", "threshold": 2500000, "unit": "USD million", "direction": "below", "currentValue": 3029659, "rationale": "Low-reserve boundary."},
        {"variable": "China property decline", "threshold": 25, "unit": "percent from peak", "direction": "above", "currentValue": 22.61, "rationale": "Frozen China crisis definition."},
        {"variable": "China real GDP growth", "threshold": 2, "unit": "percent", "direction": "below", "currentValue": 4.96, "rationale": "Growth floor for a balance-sheet recession."}]
    j["sensitivity"] = [{"driver": "Banking-crisis transition", "low": "20% drawdown", "high": "75% drawdown", "effect": f"{ST_CURVE[0]:.0%} → {ST_CURVE[-1]:.0%} before liquidity feedback"},
                        {"driver": "China property loss", "low": 15, "high": 40, "effect": "see the generated reverse-stress surface"},
                        {"driver": "US high-yield OAS", "low": 3, "high": 14, "effect": "see the generated reverse-stress surface"}]
    dump("joint_crisis", j)
    profiles = {
        "US": {"summary": "Origin of the shock. Funding-market depth decides whether an equity reset becomes a banking crisis.", "metrics": {"growth": 2.34, "publicDebt": 118.8, "privateCredit": 216.3, "policyRate": 4.25, "directExposure": "high"}, "shockRole": "Origin and dollar-funding amplifier"},
        "China": {"summary": "Little direct AI exposure, but property and LGFV balance sheets make it the second fault line.", "metrics": {"growth": 4.96, "publicDebt": None, "privateCredit": 194.3, "policyRate": 3.0, "directExposure": "low"}, "shockRole": "Property-debt amplifier and potential Treasury seller"},
        "EU": {"summary": "Trade, banks and dollar funding carry the first-round recession before any reallocation gain.", "metrics": {"growth": 1.5, "publicDebt": 87.4, "privateCredit": None, "policyRate": 2.0, "directExposure": "medium"}, "shockRole": "First-round loser; conditional later gainer"},
        "Switzerland": {"summary": "Low debt and safe-haven demand cushion funding stress; a stronger franc hurts exports.", "metrics": {"growth": 1.4, "publicDebt": 17.2, "privateCredit": 164.6, "policyRate": 0.0, "directExposure": "medium"}, "shockRole": "Safe haven with an export cost"}}
    dump("country_profiles", {"asOf": ASOF, "metricDefinitions": {"growth": "2025 real GDP growth, %", "publicDebt": "Latest government debt, % GDP; perimeters differ", "privateCredit": "Domestic private credit, % GDP",
                                                                      "policyRate": "Policy rate, %", "directExposure": "Qualitative direct AI/US-tech exposure"}, "countries": profiles})


ST_CURVE = [0, 0]


def main():
    global ST_CURVE
    df = EP.load_panel(); features, feat_audit, us = current_features()
    sys_model, sys_panel, sys_template, sys_audit = ST.fit(ROOT)
    sys_template = {**sys_template, "runup3": float(features[0])}
    ST_CURVE = [c["probability"] for c in sys_audit["currentBalanceSheetCurve"]]
    tree, boots, weights, point = build_scenarios(df, features, feat_audit, (sys_model, sys_panel, sys_template, sys_audit))
    cp = [x["probability"] for x in sys_audit["currentBalanceSheetCurve"]]
    fins, macros, params, calib, targets, cohorts, cn_base, cn_defl, slope = classify_paths(tree, boots)
    connected, _ = build_connected(tree, fins, macros, (sys_model, sys_panel, sys_template, sys_audit), boots)
    paths = build_paths(tree, fins, macros)
    hyst = build_hysteresis(tree, fins, macros, params, calib, targets, cohorts, cn_base, cn_defl, slope)
    build_history(paths, macros)
    boom_ids = {"continued_boom": "boom", "no_burst_sideways": "sideways"}
    model_probs = {"boom": point["continued_boom"], "sideways": point["no_burst_sideways"], "bust": 1 - point["continued_boom"] - point["no_burst_sideways"]}
    checks = CK.run(df, {"runup3": float(features[0]), "return1": float(features[1]), "volatility5": float(features[2])}, model_probs)
    dump("historical_checks", checks)
    cvc = checks["crossValidation"]; cve = cvc["leaveOneEraOut"]; cvk = cvc["leaveOneCountryOut"]
    tree["backtest"] = {"leaveOneCountryOut": {k: cvk[k] for k in ("brier", "baseRateBrier", "n")}, "leaveOneEraOut": {k: cve[k] for k in ("brier", "baseRateBrier", "n")},
                        "skillDisclosure": "Skill over the base rate is modest and unstable across eras. Treat the odds as disciplined scenario weights, not precise forecasts."}
    dump("scenario_tree", tree)
    patch_other(tree, us, connected, hyst, checks)
    print(json.dumps({"status": "released", "probabilitySum": sum(x["probability"] for x in tree["scenarios"]), "scenarios": {x["id"]: round(x["probability"], 4) for x in tree["scenarios"]},
                      "mixture": connected["mixture"], "episodes": len(df), "params": params}, indent=1))


if __name__ == "__main__":
    main()
