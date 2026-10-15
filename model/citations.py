"""Curated citation list: what each source is used for in this model.

Entries marked `reg` come from the verified reference register (site/data/references.json,
Crossref-checked). Entries marked `new` were added for the methods section and checked
against Crossref / the World Bank API on 2026-10-15.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# key -> (kind, ("reg", id-or-title-substring) | ("new", dict), use)
SPEC = [
 # ---- data
 ("wdi", "data", ("new", {"authors": ["World Bank"], "year": 2026, "title": "World Development Indicators: S&P Global Equity Indices (CM.MKT.INDX.ZG), Inflation, consumer prices (FP.CPI.TOTL.ZG), GDP growth (NY.GDP.MKTP.KD.ZG), GDP deflator inflation (NY.GDP.DEFL.KD.ZG)", "venue": "World Bank DataBank (CC BY 4.0)", "url": "https://databank.worldbank.org/source/world-development-indicators"}),
  "Annual equity-index returns, CPI and deflator inflation and real GDP growth. Supplies the run-up panel from 1994, the 25% inflation screen, the US deflation of the AI basket, and China's baseline growth and deflator."),
 ("jst", "data", ("reg", "jorda_schularick_taylor_2017_macrofinancial"),
  "The paper behind the JST Macrohistory database: banking-crisis dates, credit, debt, interest rates, real GDP per head and equity returns for 16–18 economies since 1870."),
 ("jstdb", "data", ("reg", "jst_macrohistory_database"),
  "Release R6 (data to 2020) used directly: pre-1994 run-up episodes, the banking-crisis transition panel and every hysteresis target."),
 ("gpr", "data", ("reg", "caldara_iacoviello_2022_geopolitical_risk"),
  "News-based geopolitical risk index; its percentiles define the calm / tense / crisis rows of the funding-regime surface."),
 ("fred", "data", ("new", {"authors": ["Federal Reserve Bank of St. Louis"], "year": 2026, "title": "Federal Reserve Economic Data (FRED): BAMLH0A0HYM2, NFCI, STLFSI4, WRESBAL", "venue": "FRED", "url": "https://fred.stlouisfed.org/"}),
  "Current gauges of dollar-market liquidity: high-yield spread, financial-conditions and stress indices, reserve balances."),
 ("bisgap", "data", ("reg", "bis_credit_to_gdp_gaps"),
  "China credit-to-GDP level, credit gap and debt-service ratio shown in the China section and the early-warning gauges."),
 ("imfchn", "data", ("reg", "imf_cr26-044_chn_2026"),
  "China augmented debt (IMF perimeter), reserves and policy-space inputs."),
 ("tic", "data", ("reg", "Major Foreign Holders of Treasury Securities"),
  "Japanese and Chinese Treasury holdings (latest month: July 2026): sale capacity for the Treasury-pressure channel."),
 ("spdji", "data", ("reg", "S&P 500 Communication Services & Information Technology Index"),
  "Sector weights behind the 47.4% broad technology and platform proxy and the 73% top-10 concentration."),
 ("wb2023", "data", ("reg", "Falling Long-Term Growth Prospects"),
  "Counterexample and baseline constraint: weak potential growth is the counterfactual, not a crash input."),
 # ---- severity benchmarks
 ("fedscen", "benchmark", ("reg", "2026 Stress Test Scenarios"),
  "Severely adverse path: US real GDP level falls 4.6% to its trough. Used as the peak-to-trough check for the systemic branch."),
 ("bea", "benchmark", ("reg", "How did the economic downturn affect real GDP growth"),
  "The 2007–09 contraction (−4.0% peak to trough): second severity check."),
 ("bern12", "benchmark", ("reg", "Some Reflections on the Crisis and the Policy Response"),
  "Why the dot-com crash stayed dispersed while the GFC concentrated losses in leveraged intermediaries."),
 ("bern13", "benchmark", ("reg", "The Crisis as a Classic Financial Panic"),
  "Funding-run mechanics behind the margin-call and liquidity loops."),
 ("fed87", "benchmark", ("reg", "The October 1987 Crash Ten Years Later"),
  "Market-liquidity breakdown and forced selling in 1987."),
 ("sr117", "benchmark", ("reg", "sr_11_7_model_risk"),
  "Model-risk standard behind the validation, limitations and disclosure practice."),
 ("imfweo", "benchmark", ("new", {"authors": ["International Monetary Fund"], "year": 2026, "title": "World Economic Outlook, October 2026: adverse AI scenario (figures as reported by Reuters, 13 Oct 2026)", "venue": "IMF / Reuters", "url": "https://www.reuters.com/world/china/imf-says-ai-investment-propping-up-global-growth-war-debt-threaten-outlook-2026-10-13/"}),
  "Benchmark for a correction-type AI scenario: global GDP 1.1% and US GDP 1.8% below baseline by 2028."),
 ("bisai", "theory", ("new", {"authors": ["Phurichai Rungcharoenkitkul"], "year": 2026, "title": "The AI investment race", "venue": "BIS Working Paper 1367, 14 July 2026", "url": "https://www.bis.org/publications/working-paper-1367-ai-investment-race"}),
  "Calibrated model of over-investment, debt financing and contagion between AI firms: independent support for the transmission mechanism."),
 ("crma", "benchmark", ("new", {"authors": ["European Commission"], "year": 2024, "title": "Critical Raw Materials Act: 2030 benchmarks (10% extraction, 40% processing, 25% recycling, at most 65% from one supplier)", "venue": "DG GROW", "url": "https://single-market-economy.ec.europa.eu/sectors/raw-materials/areas-specific-interest/critical-raw-materials/critical-raw-materials-act_en"}),
  "Policy targets behind Europe's supply-independence strategy. Objectives, not operating capacity."),
 ("shiller", "data", ("new", {"authors": ["Robert J. Shiller"], "year": 2026, "title": "Monthly S&P 500 price, dividend, earnings and CPI data (as redistributed in the Open Data Commons datasets/s-and-p-500 repository)", "venue": "ODC-PDDL-1.0", "url": "https://github.com/datasets/s-and-p-500"}),
  "Monthly US equity history used only to measure how much annual closes understate falls."),
 # ---- statistical methods
 ("ridge", "method", ("new", {"authors": ["Arthur E. Hoerl", "Robert W. Kennard"], "year": 1970, "title": "Ridge Regression: Biased Estimation for Nonorthogonal Problems", "venue": "Technometrics", "doi": "10.1080/00401706.1970.10488634"}),
  "L2 penalty of the outcome logit (C = 0.2 and 1.0, averaged)."),
 ("gelman", "method", ("reg", "gelman_2008_weakly_informative_prior"),
  "Argues for weakly informative regularisation of logistic regressions with few events; motivates the ridge core."),
 ("gbm", "method", ("new", {"authors": ["Jerome H. Friedman"], "year": 2001, "title": "Greedy function approximation: A gradient boosting machine", "venue": "The Annals of Statistics", "doi": "10.1214/aos/1013203451"}),
  "Gradient-boosting challenger (15% of the blend) for thresholds the logit cannot represent."),
 ("rf", "method", ("new", {"authors": ["Leo Breiman"], "year": 2001, "title": "Random Forests", "venue": "Machine Learning", "doi": "10.1023/A:1010933404324"}),
  "Random-forest challenger (10% of the blend)."),
 ("platt", "method", ("new", {"authors": ["Alexandru Niculescu-Mizil", "Rich Caruana"], "year": 2005, "title": "Predicting good probabilities with supervised learning", "venue": "Proceedings of the 22nd International Conference on Machine Learning", "doi": "10.1145/1102351.1102430"}),
  "Logistic (Platt) recalibration of the blended fall probability on out-of-fold predictions."),
 ("jeffreys", "method", ("new", {"authors": ["Harold Jeffreys"], "year": 1946, "title": "An invariant form for the prior probability in estimation problems", "venue": "Proceedings of the Royal Society of London. Series A", "doi": "10.1098/rspa.1946.0056"}),
  "Beta(½, ½) prior for the share of no-fall run-ups that keep booming."),
 ("brier", "method", ("reg", "brier_1950_verification"),
  "Brier score: the loss for every out-of-sample comparison."),
 ("gneiting", "method", ("reg", "gneiting_raftery_2007_scoring_rules"),
  "Why a strictly proper score (Brier) is used to compare probability forecasts."),
 ("roberts", "method", ("new", {"authors": ["David R. Roberts", "Volker Bahn", "Simone Ciuti", "et al."], "year": 2017, "title": "Cross-validation strategies for data with temporal, spatial, hierarchical, or phylogenetic structure", "venue": "Ecography", "doi": "10.1111/ecog.02881"}),
  "Justifies leave-country-out and leave-era-out folds when observations are clustered."),
 ("efron", "method", ("reg", "efron_1979_bootstrap"),
  "Bootstrap behind every 10th–90th percentile interval."),
 ("cameron", "method", ("new", {"authors": ["A. Colin Cameron", "Jonah B. Gelbach", "Douglas L. Miller"], "year": 2008, "title": "Bootstrap-Based Improvements for Inference with Clustered Errors", "venue": "The Review of Economics and Statistics", "doi": "10.1162/rest.90.3.414"}),
  "Resampling whole origin years, because simultaneous crashes are one draw, not thirty."),
 ("embrechts", "method", ("reg", "embrechts_mcneil_straumann_2002"),
  "Copula dependence in the China/US reverse-stress surface; warns that correlation alone misses tail dependence."),
 ("forbes", "method", ("reg", "forbes_rigobon_2002_no_contagion"),
  "Separates contagion from interdependence; the joint-crisis model draws both flags from shared shocks plus explicit feedback."),
 ("glasserman", "method", ("reg", "glasserman_kang_kang_2014_stress_scenarios"),
  "Stress-scenario selection by likelihood: the reverse-stress grid reports conditional, not current-trajectory, odds."),
 # ---- bubbles, crises, history
 ("greenwood", "theory", ("reg", "greenwood_shleifer_you_2019"),
  "Closest published test of whether large price run-ups predict crashes; compare with the frequency table on this page."),
 ("jordabubbles", "theory", ("reg", "jorda_schularick_taylor_2015_leveraged_bubbles"),
  "Credit-financed bubbles are followed by deeper recessions: why balance-sheet variables enter the banking-crisis link."),
 ("scht", "theory", ("reg", "schularick_taylor_2012"),
  "Credit growth predicts financial crises: source of the five-year credit-growth feature."),
 ("lv", "theory", ("reg", "laeven_valencia_2018_systemic_banking_crises"),
  "Definition and dating of systemic banking crises."),
 ("rr", "theory", ("reg", "reinhart_rogoff_2009_aftermath"),
  "Deep and long output and employment losses after banking crises."),
 ("bo13", "theory", ("reg", "brunnermeier_oehmke_2013"),
  "Survey of how bubbles and leverage turn into systemic risk."),
 ("aischool", "theory", ("reg", "acemoglu_2024_simple_macro_ai"),
  "Bounds on near-term economy-wide gains from AI: why expected AI revenue can reset."),
 ("jcurve", "theory", ("reg", "brynjolfsson_rock_syverson_2018_j_curve"),
  "Delayed productivity payoff of general-purpose technology: the gap between capex and revenue."),
 # ---- funding spirals and dollar liquidity
 ("bp09", "theory", ("reg", "brunnermeier_pedersen_2009_funding_liquidity"),
  "Margin and funding spirals: the loop from equity losses to forced sales to lower liquidity."),
 ("km97", "theory", ("reg", "kiyotaki_moore_1997_credit_cycles"),
  "Collateral-constrained credit cycles: why asset falls cut borrowing and investment."),
 ("bs14", "theory", ("reg", "brunnermeier_sannikov_2014"),
  "Nonlinear amplification when intermediary balance sheets are impaired."),
 ("as10", "theory", ("reg", "adrian_shin_2010_liquidity_leverage"),
  "Procyclical leverage of market-based intermediaries."),
 ("sss21", "theory", ("reg", "schrimpf_shin_sushko_2021_margin_spirals"),
  "Margin spirals in March 2020: the liquidity-vacuum analogue."),
 ("bruno", "theory", ("reg", "bruno_shin_2014_cross_border_banking"),
  "Dollar funding and cross-border bank leverage: the transmission to Europe and China."),
 ("du18", "theory", ("reg", "du_tepper_verdelhan_2018_cip"),
  "Dollar funding premia when balance sheets are scarce."),
 ("cfg16", "theory", ("reg", "caballero_farhi_gourinchas_2016_safe_asset"),
  "Safe-asset scarcity and the role of Treasuries in the dollar-liquidity channel."),
 # ---- hysteresis, Japan, China
 ("cerra", "theory", ("new", {"authors": ["Valerie Cerra", "Sweta Chaman Saxena"], "year": 2008, "title": "Growth Dynamics: The Myth of Economic Recovery", "venue": "American Economic Review", "doi": "10.1257/aer.98.1.439"}),
  "Output losses after financial crises are largely permanent: supports a persistent loss share rather than a mechanical rebound."),
 ("bcs", "theory", ("new", {"authors": ["Olivier Blanchard", "Eugenio Cerutti", "Lawrence Summers"], "year": 2015, "title": "Inflation and Activity – Two Explorations and their Monetary Policy Implications", "venue": "NBER Working Paper 21726", "doi": "10.3386/w21726"}),
  "Most recessions leave output below its earlier trend, evidence for hysteresis."),
 ("rww", "theory", ("new", {"authors": ["David Reifschneider", "William L. Wascher", "David Wilcox"], "year": 2013, "title": "Aggregate Supply in the United States: Recent Developments and Implications for the Conduct of Monetary Policy", "venue": "Finance and Economics Discussion Series 2013-77, Federal Reserve Board", "doi": "10.17016/feds.2013.77"}),
  "Potential output fell after the 2007–09 crisis: the US precedent for the hysteresis stock."),
 ("okun", "theory", ("new", {"authors": ["Laurence Ball", "Daniel Leigh", "Prakash Loungani"], "year": 2017, "title": "Okun's Law: Fit at 50?", "venue": "Journal of Money, Credit and Banking", "doi": "10.1111/jmcb.12420"}),
  "Unemployment responds to the output gap at roughly half a point per point; the engine uses 0.55."),
 ("koo", "theory", ("reg", "koo_2013_balance_sheet_recession"),
  "Balance-sheet recession: why a debt-burdened private sector stays on the sidelines."),
 ("hoshi", "theory", ("reg", "hoshi_kashyap_2004_japan"),
  "Japan's financial crisis and stagnation: the analogue behind the China anchor."),
 ("chen", "theory", ("reg", "chen_he_liu_2017_local_government_financing"),
  "How LGFV financing grew and shifted to shadow banking: the refinancing channel."),
 ("bao", "theory", ("reg", "china_lgfv_infrastructure_financing_ssrn"),
  "LGFV balance-sheet evidence for the refinancing premium."),
]


OVERRIDE = {
    "jstdb": {"authors": ["Òscar Jordà", "Moritz Schularick", "Alan M. Taylor"], "title": "The JST Macrohistory Database, Release R6 (MacroFinance & MacroHistory Lab)"},
    "fedscen": {"authors": ["Board of Governors of the Federal Reserve System"], "title": "2026 Stress Test Scenarios"},
    "sr117": {"authors": ["Board of Governors of the Federal Reserve System"], "title": "Supervisory Letter SR 11-7 on Guidance on Model Risk Management"},
    "bisgap": {"authors": ["Bank for International Settlements"], "title": "Credit-to-GDP gaps"},
    "bea": {"authors": ["US Bureau of Economic Analysis"]},
    "tic": {"authors": ["US Department of the Treasury"]},
    "spdji": {"authors": ["S&P Dow Jones Indices"]},
}


def build() -> dict:
    reg = json.loads((ROOT / "site/data/references.json").read_text())["references"]
    def find(k):
        for r in reg:
            if r.get("id") == k or k.lower() in r["title"].lower(): return r
        raise KeyError(k)
    items = []
    for key, kind, (src, ref), use in SPEC:
        r = find(ref) if src == "reg" else ref
        r = {**r, **OVERRIDE.get(key, {})}
        a = r["authors"]; a = [a] if isinstance(a, str) else a
        items.append({"key": key, "kind": kind, "authors": a, "year": r.get("year"), "title": r["title"].replace("&amp;", "&").replace("&#39;", "'"),
                      "venue": r.get("venue"), "doi": r.get("doi"), "url": r.get("url") or (f"https://doi.org/{r['doi']}" if r.get("doi") else None),
                      "use": use, "source": "register" if src == "reg" else "added"})
    return {"asOf": "2026-10-15", "items": items}
