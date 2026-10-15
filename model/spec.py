"""Methodology specification: every model, its parameters and how each was set.

Values are read from the live modules and outputs wherever they exist; coefficients that
sit inside engine.py / direct_release.py equations are reproduced as written and marked
with their source so a reader can audit them. Status vocabulary:
  Data        observed input
  Fixed rule  definition or threshold chosen by design, not estimated
  Estimated   fitted to data by the model code
  Calibrated  searched so that outputs match stated historical targets
  Assumed     structural parameter set by judgment; not estimated, not validated on its own
"""
from __future__ import annotations
import numpy as np
import equity_panel as EP
import engine as E
import hysteresis as H


def r(name, value, status, how, cite=None, src=None):
    return {"name": name, "value": value, "status": status, "how": how, "cite": cite or [], "src": src}


def f(x, d=3): return f"{x:.{d}f}"
def p(x, d=0): return f"{x*100:.{d}f}%"


def build(c: dict) -> dict:
    tree, par, cal, tg, co, ck, hy = c["tree"], c["params"], c["calib"], c["targets"], c["cohorts"], c["checks"], c["hyst"]
    m = tree["method"]; cb = m["calibration"]; ta = m["transitionAudit"]; sa = ta["systemicTransition"]
    cv = ck["crossValidation"]; scen = {s["id"]: s for s in tree["scenarios"]}
    feat = m["featureAudit"]; infl = feat["usInflationAssumed"]
    sec = []

    sec.append({"id": "data", "title": "1 · Data and episode panel",
      "summary": "A run-up episode is a market whose real three-year equity return reached +50%. The outcome is what happened over the next four annual closes, which is the same geometry as today (end-2026 to end-2030).",
      "tables": [{"title": "Inputs and rules", "rows": [
        r("Modern equity returns", "1994–2021 origins, 156 episodes", "Data", "World Bank S&P Global equity indices (CM.MKT.INDX.ZG), deflated by WB consumer-price inflation.", ["wdi"], "equity_panel.py:_wb"),
        r("Historical equity returns", "1870–1993 origins, 145 episodes", "Data", "JST total equity return, deflated by JST CPI. Origins before 1994 only, so the two sources never double-count a market.", ["jst", "jstdb"], "equity_panel.py:load_panel"),
        r("Episode trigger", "3-year real return ≥ +50%", "Fixed rule", "Bubble-scale threshold kept from the original design; origins must be ≥3 years apart within an economy. Run-ups of 100%+ are reported separately.", [], "equity_panel.py:THRESHOLD"),
        r("Inflation screen", "drop windows above 25% a year", "Fixed rule", "Index returns are not comparable in hyperinflation; removes the affected windows.", [], "equity_panel.py:INFLATION_CAP"),
        r("Outcome window", "next 4 annual closes", "Fixed rule", "End-2026 origin to end-2030. All probabilities and all paths use this window.", [], "equity_panel.py:HORIZON"),
        r("Fall bands", "20% / 35% / 50%", "Fixed rule", "Worst peak-to-trough fall at annual closes inside the window, measured from the highest close reached since the origin (so an index that rises then falls counts): mild 20–35%, moderate 35–50%, severe 50%+. Measuring from the origin level only, as an earlier release did, lowers the share of falls from 61% to 42%.", [], "equity_panel.py:drawdown_of"),
        r("Boom hurdle", "5% a year real (21.6% over four years)", "Assumed", "A round figure for “keeps earning normal returns”. It splits no-fall cases into boom and contained repricing; no sensitivity run.", [], "equity_panel.py:BOOM_REAL_PER_YEAR"),
        r("Panel size", f"{ck['episodes']} episodes · {ck['countries']} economies · {ck['originYears']} origin years", "Data", "Simultaneous crashes make countries non-independent, so intervals resample whole origin years.", ["cameron"]),
        r("Predictors", "3-year real run-up; last-12-month real return", "Fixed rule", "Volatility is excluded: an 8-stock basket (NVDA, MSFT, AMZN, AVGO, AMD, ORCL, GOOGL, META) is not comparable with a national index and added no held-out skill.", ["roberts"], "equity_panel.py:PREDICTORS"),
        r("Current state", f"run-up {p(feat['realFeatures'][0])}, last 12 months {p(feat['realFeatures'][1])}", "Data", f"Equal-weight monthly-rebalanced basket to 31 Oct 2026, nominal run-up {p(feat['nominalRunup3'])}, deflated by US inflation of {', '.join(f'{x:.1f}' for x in infl)}% (windows ending Oct 2026 back to Oct 2022). CPI ends in 2024, so the 2025 GDP deflator stands in for 2025–26.", ["wdi"], "direct_release.py:current_features")]}]})

    va = c["val"]["validation"]; vw = va["schemes"]["Leave one global wave out"]; fb = "Full blend (logit + boosting + forest)"; bs = "Base rate (training frequency)"
    sens = c["val"]["sensitivity"]
    sec.append({"id": "outcome", "title": "2 · Outcome probabilities: history first, models as a check",
      "summary": f"The headline weights are what happened after comparable run-ups, with each global wave counted once. Four statistical models were tested against that simple frequency; none held up once whole waves were held out, so they are used for validation, not for the headline.",
      "tables": [{"title": "What sets the probabilities", "rows": [
        r("Comparable run-ups", f"3-year real gain ≥ {p(cb['anchorRunup'])}: {cb['anchorEpisodes']} episodes in {cb['anchorWaves']} global waves", "Fixed rule", "Today's gain is about 190%, inside this group. A global wave is a cluster of origin years within two years of each other; simultaneous crashes count once.", ["greenwood", "cameron"], "direct_release.py:build_scenarios"),
        r("Chance of a 20%+ fall", f"{p(cb['anchorFall'])} (before the funding-regime surface)", "Estimated", "Mean over waves of the share of episodes that fell 20%+ peak to trough at annual closes within four years. 10th–90th percentile from a wave bootstrap is shown with each scenario.", ["efron", "cameron"]),
        r("Split of falls into mild / moderate / severe", "same wave-weighted frequencies", "Estimated", "Taken from the same episodes; with nine waves this split is lumpy, hence the wide ranges.", []),
        r("Boom share of no-fall cases", f"{ta['boomObserved']} boom vs {ta['sidewaysObserved']} contained → {p(ta['boomShareOfNonBust'])}", "Estimated", "Beta(½, ½) Jeffreys prior on the share that clears the real-return hurdle.", ["jeffreys"], "direct_release.py:build_scenarios"),
        r("Model extrapolation (not used)", f"{p(cb['modelRawFall'])} for the blend below", "Estimated", f"Held out by whole global wave the blend reaches Brier {f(vw[fb]['brier'])} against {f(vw[bs]['brier'])} for the base rate, but its ranking is no better than chance (AUC {f(vw[fb]['auc'],2)}). A recalibration fitted on those held-out predictions has slope {f(cb['waveOutPlattSlope'],2)}, so the model's extra confidence is not trusted.", ["platt", "roberts"], "direct_release.py:platt")]},
        {"title": "Models tested (validation only)", "rows": [
        r("Ridge logit (run-up + 12-month return)", "C = 0.2 and 1.0, averaged", "Estimated", "Four-band target, standardised predictors, L-BFGS; penalties chosen a priori.", ["ridge", "gelman"], "direct_release.py:fit_probs"),
        r("Gradient boosting", "80 trees · depth 2 · learning rate 0.035 · subsample 0.8", "Fixed rule", "Shallow and slow to limit overfit; not tuned.", ["gbm"], "models.py:make_gb"),
        r("Random forest", "500 trees · depth 4 · min leaf 5 · max features 0.8 · balanced classes", "Fixed rule", "Same reasoning.", ["rf"], "models.py:make_rf"),
        r("Blend", "75% logit · 15% boosting · 10% forest", "Assumed", "Set before testing.", []),
        r("Folds", f"67 economies; {va['waveCount']} global waves; 6 eras; before/after 1994", "Fixed rule", "Whole waves are held out together, because the same global crash seen in many countries is not independent evidence.", ["roberts"], "checks.py:validation_report"),
        r("Sensitivity of the headline", f"fall probability from {p(min(x['fall20'] for x in sens))} to {p(max(x['fall20'] for x in sens))} across {len(sens)} reasonable variants", "Data", "Window length, trigger size, era and predictors all move the number; the full table is in the validation section.", [])]}]})

    geo = {"calm": .88, "tense": 1.0, "crisis": 1.18}; liq = {"ample": .62, "neutral": 1.0, "vacuum": 2.75}
    w = {(x["geopolitics"], x["liquidity"]): x["probability"] for x in tree["stateProbabilities"]}
    sec.append({"id": "regime", "title": "3 · Funding-regime surface",
      "summary": "The historical panel cannot see the dollar-liquidity regime today, so a 3 × 3 surface scales the odds of a fall. Its numbers are structural assumptions, not estimates.",
      "tables": [{"title": "Parameters", "rows": [
        r("Geopolitical factor on fall odds", "calm 0.88 · tense 1.00 · crisis 1.18", "Assumed", "Monotone, set by judgment. Applied as a shift in the log-odds of a fall. Rows are percentile bands of the news-based GPR index (calm below 40th, tense 40–80th, crisis above 80th).", ["gpr"], "direct_release.py:geo"),
        r("Liquidity factor on fall odds", "ample 0.62 · neutral 1.00 · vacuum 2.75", "Assumed", "Monotone, set by judgment. A vacuum means a high-yield spread above 6.5%, reserves below $2.5tn, or equivalent repo and Treasury dysfunction, with two or more signals active (2008 and March 2020 are the analogues).", ["bp09", "sss21", "fred"], "direct_release.py:liq"),
        r("Window-start state weights", f"crisis × neutral {p(w[('crisis','neutral')])}; tense × neutral {p(w[('tense','neutral')])}; all nine sum to 100%", "Assumed", "Carried from the first release’s state model; not re-estimated here.", ["gpr", "fred"], "inputs/states.json"),
        r("Net effect", f"{p(cb['anchorFall'])} before the surface → {p(1 - scen['continued_boom']['probability'] - scen['no_burst_sideways']['probability'])} after", "Assumed", "The surface is the only judgment-set multiplier on the headline; the bootstrap perturbs it by a lognormal factor (sd 0.16).", [])]}]})

    cur = sa["currentBalanceSheetCurve"]
    sec.append({"id": "tail", "title": "4 · From equity loss to banking crisis",
      "summary": "How a 50%+ fall splits into liquidity holds / vacuum / banking crisis. A second logit, fitted on 150 years of country-years, gives the chance that a banking crisis starts inside the window.",
      "tables": [{"title": "Transition model", "rows": [
        r("Panel", f"{sa['rows']:,} country-years · {sa['countries']} economies · origins {sa['firstOrigin']}–{sa['lastOrigin']} · {sa['crisisWindows']} windows with a crisis ({p(sa['crisisRate'],1)})", "Data", "Every origin year with a consistent real equity record; a crisis counts if JST flags one starting in the window.", ["jstdb", "lv"], "systemic_transition.py:build_panel"),
        r("Features", "worst 4-year drawdown · 3-year run-up · loans/GDP · 5-year credit change · public debt/GDP · short rate", "Fixed rule", "Credit and leverage variables because credit-financed booms end worse.", ["scht", "jordabubbles", "rr"], "systemic_transition.py:FEATURES"),
        r("Model", "ridge logit, C = 0.2, median imputation, standardised", "Estimated", "Penalty chosen a priori.", ["ridge"], "systemic_transition.py:_model"),
        r("Held-out skill (Brier vs base rate)", f"countries {f(sa['validation']['leaveOneCountryOut']['brier'])} vs {f(sa['validation']['leaveOneCountryOut']['baseRateBrier'])}; eras {f(sa['validation']['leaveOneEraOut']['brier'])} vs {f(sa['validation']['leaveOneEraOut']['baseRateBrier'])}", "Estimated", f"Beats the base rate on held-out economies (AUC {f(sa['validation']['leaveOneCountryOut']['auc'],2)}) but not on held-out eras (AUC {f(sa['validation']['leaveOneEraOut']['auc'],2)}). The systemic share is therefore wide: the bootstrap draws it from Beta(16·s + ½, 16·(1−s) + ½).", ["brier"]),
        r("Current balance-sheet curve", " · ".join(f"{abs(x['drawdown'])*100:.0f}% fall → {p(x['probability'])}" for x in cur), "Estimated", "Latest JST US row for credit variables (vintage 2016 origin), overridden by public debt 118.8% of GDP, short rate 4.25% and the current real run-up.", [], "systemic_transition.py:fit"),
        r("Severity integration", "Gaussian over falls of 50–76%, centre 62%, sd 7.5%", "Assumed", f"Weights the curve over plausible severe falls; gives a systemic share of {p(ta['tailShare']['systemic'])} of severe outcomes.", [], "direct_release.py:build_scenarios"),
        r("Vacuum without banking crisis", "20% of non-systemic severe paths", "Assumed", "No dataset identifies a vacuum that spares the banks; 20% is a central guess, drawn from Beta(2.5, 10.5) in the bootstrap.", ["sss21"], "direct_release.py:vac")]}]})

    sec.append({"id": "uncertainty", "title": "5 · Uncertainty and sampling",
      "summary": "Every 10th–90th percentile range comes from one bootstrap that resamples whole global waves and perturbs the judgment-set inputs.",
      "tables": [{"title": "Procedure", "rows": [
        r("Bootstrap", "500 replications; whole global waves among comparable run-ups resampled with replacement", "Fixed rule", f"With only {cb['anchorWaves']} waves the ranges are wide on purpose.", ["efron", "cameron"], "direct_release.py:build_scenarios"),
        r("State weights", "Dirichlet(250·w + 1)", "Assumed", "Concentration set so state weights move by a few points.", []),
        r("Regime multiplier", "× lognormal(0, 0.16)", "Assumed", "Judgment uncertainty in the surface.", []),
        r("Boom share, systemic share, vacuum share", "Beta from resampled counts; Beta(16·s+½, 16·(1−s)+½); Beta(2.5, 10.5)", "Assumed", "Widths set by judgment.", []),
        r("Scenario draws", f"{tree['monteCarlo']['draws']:,} draws, seed {tree['monteCarlo']['seed']}", "Fixed rule", f"Largest Monte Carlo standard error {p(tree['monteCarlo']['maxStdError'],2)}.", []),
        r("Not in the bootstrap", "finance-engine coefficients (section 6)", "Fixed rule", "They are fixed structural parameters; only the macro-damage multipliers (section 7) are randomised. Ranges are therefore narrower than total model uncertainty.", [])]}]})

    sev = {s: E.SEVERITY[s] for s in E.SEVERITY}
    md = {s: c["pathStats"][s]["medianDrawdown"] for s in E.SEVERITY}
    sec.append({"id": "engine", "title": "6 · Connected finance engine",
      "summary": "One shared state per simulated year, solved by iterating eight times to a fixed point: AI revenue expectations → coverage of commitments → funding cost → equity loss → margin calls → forced sales → liquidity → China outflow → LGFV refinancing → back to liquidity. These coefficients are stress parameters set so each loop behaves as the cited mechanisms describe. They are not estimated.",
      "equations": [
        "expectations_t = clip(1 − sev · shape_t + ε_t, 0.03, 1.12),  shape = [0, .95, .82, .58, .38],  ε ~ N(0, 0.07)",
        "revenue = clip(0.70 + 0.40·expectations − 0.15·liquidity, 0.12, 1.15);  commitments = 1 + 0.48·sev·e^(−0.18(t−1))",
        "coverage = 1.82 · revenue / commitments",
        "margin_t = 0.36·margin_{t−1} + max(0, drawdown_t − drawdown_{t−1} − 0.025) · (1.18 + 0.72·sev)",
        "outflow = clip(0.08 + 0.50·liq + 0.34·(1 − expectations) + 0.25·chinaStress, 0, 1)",
        "sale = clip(0.025 + 0.40·max(0, outflow − 0.30) + 0.18·chinaStress, 0, 0.72)",
        "liquidity_t = clip(0.44·liquidity_{t−1} + 0.76·max(0, 1 − coverage) + 1.12·margin + 0.34·sale − policy, 0, 1);  policy = 0.075·(t−1)·sev·(1 − 0.55·margin)",
        "equity_t = clip(0.54·equity_prev + 0.46·100·(1 − 0.52·sev·shape − 0.20·liquidity − 0.10·margin) + N(0, 1.45), 10, 150)",
        "chinaStress_t = clip(0.58·chinaStress_{t−1} + 0.35·outflow + 0.24·liquidity + 0.11·sev, 0, 1);  start 0.22",
        "hyperscaler rate = 4.8 + 5.2·liquidity + 1.3·max(0, 1 − coverage);  LGFV rate = 4.5 + 5.1·outflow + 1.35·sale"],
      "tables": [{"title": "Scenario severity index", "rows": [
        r(NAMES[s], f"sev = {sev[s]:.2f}", "Assumed", f"Median simulated annual-close fall {p(md[s])}; target band {'under 20%' if s in ('continued_boom','no_burst_sideways') else '20–35%' if s=='mild_adjustment' else '35–50%' if s=='moderate_burst' else '50%+'}.", [], "engine.py:SEVERITY") for s in E.SEVERITY]},
        {"title": "Structural mechanisms", "rows": [
        r("Funding and margin spirals", "coefficients above", "Assumed", "Equity losses cut collateral, which forces sales and lowers market liquidity.", ["bp09", "km97", "bs14", "as10", "sss21", "bern13", "fed87"]),
        r("Revenue-expectation reset and sticky commitments", "0.70/0.40/0.15; 0.48", "Assumed", "Expected AI revenue falls short of what capex and power contracts need; commitments decay slowly.", ["aischool", "jcurve"]),
        r("Dollar funding and Treasury channel", "0.25, 0.40, 0.18, 0.34", "Assumed", "Outflow from China and dollar scarcity feed back to US liquidity through Treasury sales.", ["bruno", "du18", "cfg16", "tic"]),
        r("LGFV refinancing", "4.5% + 5.1·outflow + 1.35·sale", "Assumed", "Marginal refinancing cost for local-government vehicles.", ["chen", "bao", "imfchn"]),
        r("Paths", "4,000 per scenario; 8 fixed-point iterations per year", "Fixed rule", "Common random numbers across scenarios; seed 20261014 + 7 + index.", [])]}]})

    pr = par; M = {s: hy["scenarios"][s] for s in E.SEVERITY}
    emp = tg
    sec.append({"id": "hysteresis", "title": "7 · Macro paths and hysteresis",
      "summary": "The finance state drives an output gap and a permanent loss stock. Each of the three US channels (and three China channels) adds to the stock, which decays only slowly. The scales were searched so scenario medians reproduce what happened after equity crashes and banking crises in 1900–2016.",
      "equations": [
        "US output gap:  gap_t = (1 − catch)·gap_{t−1} − φ·m·(4.15·liq + 1.85·(1 − exp) + 0.70·margin) + ε,   m ~ lognormal(0, 0.4)",
        "US channels:  C = clip(0.6·liq + 0.4·margin);  I = clip((1.65 − coverage)/1.65);  U = clip(max(0, u − 5)/5)",
        "Hysteresis flow and stock:  flow_t = κ·m'·(0.45·C + 0.30·I + 0.25·U);  scar_t = (1 − ρ)·scar_{t−1} + flow_t",
        "Unemployment:  u_t = 4.3 + okun · max(0, −(gap_t − scar_{t−1}))",
        "Growth:  g_t = 2.4 + (gap_t − gap_{t−1}) − flow_t;   output vs trend = gap − scar",
        "China channels:  D = clip((LGFV rate − nominal growth − 2)/8);  B = clip((chinaStress − 0.30)/0.5);  F = clip((outflow − 0.30)/0.5);  flow = κ_cn·m'·(0.40·D + 0.35·B + 0.25·F)",
        "China output gap uses 2.85·max(0, chinaStress − 0.22) + 1.85·max(0, outflow − 0.135) + 0.45·max(0, sale − 0.065); deflator = −0.92 − 1.5·max(0, chinaStress − 0.22)",
        "Europe: same structure at half the hysteresis scale (credit and labour channels only); Switzerland scales the US path by 0.48."],
      "tables": [{"title": "Fitted and fixed parameters", "rows": [
        r("φ, US cyclical scale", f(pr["phi"], 2), "Calibrated", "Grid search (0.30–1.20) minimising squared distance to the 2030 shortfall and trough targets below.", ["rww"], "hysteresis.py:calibrate"),
        r("κ, US hysteresis scale", f(pr["kappa_us"], 1), "Calibrated", "Grid search (0–5.0) jointly with φ and catch-up; pinned by the persistence target.", ["cerra", "bcs", "rww"]),
        r("catch, US output-gap closure", f(pr["catch_us"], 2), "Calibrated", "Searched over {0.20, 0.30}; a rebound penalty stops growth exceeding 1.9% after 2028 because history shows no catch-up above trend.", ["cerra"]),
        r("ρ, decay of the permanent stock", f(pr["rho"], 2), "Assumed", "3% a year: slow enough that most of the loss survives a decade.", ["cerra", "bcs"]),
        r("Okun coefficient", f(pr["okun"], 2), "Assumed", "Literature range about 0.4–0.6 unemployment points per point of output gap.", ["okun"]),
        r("Macro-damage multipliers", "lognormal sd 0.40 on φ and κ (US and China, separate draws)", "Assumed", "Widens bands toward the historical spread; check below.", []),
        r("Channel weights", "US 0.45 / 0.30 / 0.25; China 0.40 / 0.35 / 0.25", "Assumed", "Credit allocation weighs most because the post-crisis evidence points to impaired intermediation; not separately identified.", ["rr", "koo"]),
        r("φ_cn, κ_cn, catch_cn (China)", f"{f(pr['phi_cn'],2)}, {f(pr['kappa_cn'],1)}, {f(pr['catch_cn'],2)}", "Calibrated", f"Fitted on the systemic branch to two anchors: the 2030 shortfall of the banking-crisis class ({f(cal['chinaTarget2030'],1)}%) and Japan’s ten-year shortfall after 1989 ({f(cal['japanTarget10y'],1)}%). Japan is a single analogue.", ["hoshi", "koo"]),
        r("China baseline growth", f"4.96% in 2025, then {f(c['slope'],3)} points a year to {f(c['cnBase'][4],2)}% in 2030", "Estimated", "Linear trend of 2012–2025 growth, 2020–22 excluded.", ["wdi"], "direct_release.py:classify_paths")]},
       {"title": "Historical targets (JST, 1900–2016, war years excluded)", "rows": [
        r(v["label"], f"n {v['n']} · median {f(v['p50'],1)}% · mean {f(v['mean'],1)}% · p10 {f(v['p10'],1)}% · trough median {f(v['troughP50'],1)}%", "Data", "Real GDP per head four years after the origin against the ten-year pre-origin trend.", ["jstdb"], "hysteresis.py:shortfall_panel") for k, v in emp.items()]},
       {"title": "Fit by scenario (US output vs trend, 2030)", "rows": [
        r(NAMES[s], f"model {f(M[s]['us']['outputVsTrend2030'][1],1)}% · target {f(cal['usTargets'][s],1)}%", "Calibrated", f"Trough {f(M[s]['us']['troughFromOrigin'],1)}% (target {f(cal['usTroughTargets'][s],1)}%).", []) for s in E.SEVERITY]},
       {"title": "Persistence and out-of-fit checks", "rows": [
        r("Persistence share", f(cal["persistenceShare"], 2), "Data", "Post-war banking crises: median shortfall at 10 years ÷ at 5 years.", ["cerra"]),
        r("Spread of outcomes", f"model p10/p25/p50 {f(hy['validation']['modelSystemicUS']['p10'],1)} / {f(hy['validation']['modelSystemicUS']['p25'],1)} / {f(hy['validation']['modelSystemicUS']['p50'],1)} vs history {f(hy['validation']['historicalSameClass']['p10'],1)} / {f(hy['validation']['historicalSameClass']['p25'],1)} / {f(hy['validation']['historicalSameClass']['p50'],1)}", "Data", "The spread was not fitted; it checks that the multipliers give a plausible range.", ["rr"]),
        r("Severity benchmark", f"systemic trough {f(M['severe_burst_with_financial_crisis']['us']['troughFromOrigin'],1)}% vs GFC −4.0% and Fed severe −4.6%", "Data", "Peak-to-trough fall in the real-GDP level.", ["bea", "fedscen"]),
        r("Japan counterfactual", "log-linear trend of 1970–89, 1975–89 or 1980–89 real GDP, per head or total", "Data", "Shortfall against that trend: " + "; ".join(f"{x['trendYears']} {x['measure']}: {f(x['h4'],1)}% at +4, {f(x['h10'],1)}% at +10" for x in hy["cohorts"]["japanSensitivity"] if x["trendYears"] != "1960–1989") + ". A 1960–89 trend is rejected: it extrapolates catch-up growth.", ["hoshi", "jstdb"], "hysteresis.py:crisis_cohorts"),
        r("IMF adverse-AI scenario", "global GDP −1.1% and US −1.8% by 2028 vs baseline", "Data", "As reported by Reuters on 13 Oct 2026 (primary chapter not retrieved). Our 2028 US output vs trend: " + ", ".join(f"{NAMES[k]} {f(v['usOutputVsBaseline2028'],1)}%" for k, v in hy["imfBenchmark"]["ours"].items() if k in ("no_burst_sideways", "mild_adjustment", "moderate_burst", "severe_burst_with_financial_crisis")) + ". The IMF case sits between our contained and mild branches; ours is a harsher family because it adds forced selling and banking-crisis branches.", ["imfweo"]),
        r("Europe rebound term", "+0.28·severity points a year from 2029", "Assumed", "A small placeholder for safe-asset inflows and reallocation toward Europe. It is not estimated, and Europe’s possible gains as a safe-asset destination are not otherwise simulated.", ["crma"], "engine.py:macro")]}]})

    jb = c["joint"]
    sec.append({"id": "joint", "title": "8 · Joint US–China crisis",
      "summary": "A US banking crisis is the systemic branch of the scenario partition. A China crisis is a latent threshold on each simulated path. Both flags come from the same path, so the overlap is generated, not multiplied.",
      "equations": [
        "US flag = scenario is “severe burst + banking crisis”",
        "P(China crisis | path) = logistic(−5.80 + 2.6·max outflow + 1.5·max chinaStress + 0.25·(max LGFV rate − 5) + 0.70·max liquidity + 0.24·low-growth + 1.30·US flag)",
        "Reverse-stress cell (property loss P, spread S): drawdown = clip(0.30 + 0.035·(S − 3) + N(0, 0.055), 0.20, 0.82);  P(US) = logistic(logit(transition(drawdown)) + 0.17·(S − 4));  P(China) = logistic(−3.7 + 0.105·(P − 20) + 0.22·(S − 4) + 1.2·US flag);  Gaussian copula ρ = 0.62;  monotone envelope"],
      "tables": [{"title": "Parameters", "rows": [
        r("China-crisis threshold coefficients", "see equation", "Assumed", "Structural stress parameters from the first joint-crisis release. No comparable historical China crisis exists, so this layer cannot be validated.", ["forbes", "koo", "chen"], "direct_release.py:build_connected"),
        r("Crisis definition (research stage)", "property decline ≥25%, growth <2%, plus restructuring or recapitalisation stress", "Fixed rule", "Motivates the inputs of the threshold above; the simulated flag is the logistic, not a literal test of these conditions. China is currently 22.6% below its 2021 property peak.", ["bisgap", "imfchn"]),
        r("Copula correlation", "ρ = 0.62", "Assumed", "Strength of the shared shock in the reverse-stress surface; tail dependence beyond a Gaussian copula is not modelled.", ["embrechts", "forbes"], "direct_release.py:build_connected"),
        r("Intervals", f"joint {p(jb['point'],1)} (10th–90th {p(jb['interval80'][0],1)}–{p(jb['interval80'][1],1)})", "Estimated", "Bootstrap of scenario weights multiplied by per-scenario path rates.", ["efron"]),
        r("Selection of stress points", "grid cells are conditional on a revenue-expectation reset", "Fixed rule", "Reported as conditional odds, not as current-trajectory odds.", ["glasserman"])]}]})

    near = ck["nearestAnalogs"]; big = ck["runupAtLeast100"]; ot = va["outOfTime"]; sr = c["val"]["samplingResolution"]; ec = c["val"]["engineChecks"]
    rel = vw[fb]["reliability"]
    sec.append({"id": "validation", "title": "9 · Validation and known weaknesses",
      "summary": "What was tested, what held, and where the work is weak.",
      "tables": [{"title": "Tests", "rows": [
        r("Frequency check", f"run-ups of 100%+ (n {big['n']}): boom {p(big['boom'])}, contained {p(big['sideways'])}, 20%+ fall {p(big['bust'])} (unweighted)", "Data", "Same window, same definitions, no model.", ["greenwood"], "checks.py:run"),
        r("Nearest analogs", f"25 closest by run-up and 12-month return: {p(near['boom'])} / {p(near['sideways'])} / {p(near['bust'])}", "Data", "Model-free comparison with today’s state.", []),
        *[r(m_, f"Brier {f(x['brier'])} · log loss {f(x['logLoss'])} · AUC {f(x['auc'],2) if x['auc'] else 'n/a'}", "Estimated", "Leave one global wave out; target is a 20%+ peak-to-trough fall.", ["brier", "gneiting"]) for m_, x in vw.items()],
        r("Out of time", " · ".join(f"{k}: blend {f(v['models'][fb]['brier'])} vs base {f(v['models'][bs]['brier'])}" for k, v in ot.items()), "Estimated", "Models trained on one era and tested on the other; they beat the base rate there, which is why they are kept for comparison.", ["roberts"]),
        r("Reliability by wave", " · ".join(f"said {p(b['predicted'])} → happened {p(b['observed'])} (n {b['n']})" for b in rel), "Data", "Low predictions came true more often than said, and the top bin less often: the model is over-spread, so its extreme outputs are not used.", ["platt"]),
        r("Parameter sensitivity", "; ".join(f"{x['variant']}: {p(x['fall20'])}" for x in sens), "Data", "Core logit before the regime surface, so the first row is the model extrapolation, not the headline.", []),
        r("Annual-close resolution", f"US monthly data: {p(sr['monthlyFall20'])} of 4-year windows contain a 20% fall; annual closes catch {p(sr['annualFall20'])}", "Data", f"Annual closes miss {p(1 - sr['annualCatchesMonthlyFalls'])} of the falls monthly data see and understate their depth by a median {f(sr['medianDepthUnderstatedPp'],0)} points, so every fall probability here is conservative. Source: Shiller monthly real S&P 500, 1871–2022 origins.", ["wdi"]),
        r("Engine convergence", f"fixed point converged (largest residual {ec['worstResidualAfter8']:.4f}); multiple equilibria in {p(ec['worstMultiEquilibriumShare'])} of paths", "Data", "Same shocks, 40 vs 60 iterations, and starts from liquidity 0 and 1 give the same state.", []),
        r("Model risk standard", "limitations, ranges and challenger models disclosed", "Fixed rule", "Practice follows SR 11-7.", ["sr117"])]},
        {"title": "Known weaknesses", "rows": [
        r("Few independent crashes", f"{cb['anchorWaves']} global waves behind the headline; about {ta['independentSevereClusters']} clusters of 50%+ falls", "Data", "Every tail estimate rests on a handful of events.", []),
        r("Models do not beat history", "wave-out AUC about 0.44", "Data", "Why the headline is a frequency, not a model output.", ["roberts"]),
        r("Annual time step", "state updates once a year", "Fixed rule", "Margin calls (days) and funding stress (weeks) are collapsed into one fixed point per year. Short, severe liquidity episodes that recover within a year are not resolved. A higher-frequency contagion layer is the main modelling gap.", ["bp09", "sss21"]),
        r("Finance-engine coefficients untested", "section 6", "Assumed", "They reproduce the loops qualitatively and land median falls in each band, but are not estimated or bootstrapped.", []),
        r("Non-AI shocks", "energy, bond-yield and fiscal shocks only through the regime surface", "Assumed", "The scenarios are conditional on an AI reset. A rate or energy shock that also hits AI valuations would be attributed to AI here; the IMF lists those risks separately.", ["imfweo"]),
        r("Policy response", "one liquidity-support term; no alternative policy scenarios", "Assumed", "Central-bank and fiscal responses beyond that term are not simulated.", ["bern13"]),
        r("Treasury channel", "sale-pressure index 0–1", "Assumed", "Holdings are attributed by custodian and dealers, the Fed and other buyers can absorb sales; the index is a stress trigger, not a forecast.", ["tic", "cfg16"]),
        r("One China analogue", "Japan after 1989", "Assumed", "China differs in policy space, capital controls and state-bank structure.", ["hoshi"]),
        r("Basket is not an index", "8 names", "Fixed rule", "National-index episodes are analogues for a concentrated basket. Attribution of each name’s value to AI is an assumption (see the US section).", ["bo13", "greenwood"])]}]})

    sec.append({"id": "repro", "title": "10 · Reproduce it",
      "summary": "All code and frozen inputs are in the repository.",
      "equations": ["python model/fetch_data.py      # World Bank + JST → data/ (git-ignored)", "python model/direct_release.py  # → site/data/*.json  (seed 20261014)",
                    "Modules: equity_panel · systemic_transition · engine · hysteresis · checks · spec · direct_release;  frozen inputs in model/inputs"]})
    return {"asOf": "2026-10-15", "statusLegend": [
        {"status": "Data", "meaning": "Observed input or measured statistic."}, {"status": "Fixed rule", "meaning": "Definition or threshold set by design."},
        {"status": "Estimated", "meaning": "Fitted to data by the model code."}, {"status": "Calibrated", "meaning": "Searched so outputs match stated historical targets."},
        {"status": "Assumed", "meaning": "Structural parameter set by judgment; not estimated and not validated on its own."}], "sections": sec}


NAMES = {"continued_boom": "Boom holds", "no_burst_sideways": "Contained repricing", "mild_adjustment": "Mild adjustment", "moderate_burst": "Moderate burst",
         "deep_drawdown_no_vacuum": "Deep drawdown, liquidity holds", "severe_burst": "Severe burst + liquidity vacuum", "severe_burst_with_financial_crisis": "Severe burst + banking crisis"}
