"""Regenerate README.md and docs/MODEL_RISK.md from the released site data, so quoted numbers cannot drift."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; D = ROOT / "site/data"
L = lambda n: json.loads((D / f"{n}.json").read_text())


def main():
    t, c, h, chk = L("scenario_tree"), L("connected_system")["mixture"], L("hysteresis"), L("historical_checks")
    P = {s["id"]: s["probability"] for s in t["scenarios"]}; bust = 1 - P["continued_boom"] - P["no_burst_sideways"]
    s = h["scenarios"]["severe_burst_with_financial_crisis"]; cv = chk["crossValidation"]; n = chk["nearestAnalogs"]; b = chk["runupAtLeast100"]
    sk = lambda x: 1 - x["brier"] / x["baseRateBrier"]
    (ROOT / "README.md").write_text(f"""# Fault Lines — Global Economic Futures 2026–2030

An English static research dashboard testing how an AI valuation reset could propagate through hyperscaler commitments, funding spreads, forced liquidations, Treasury liquidity, China capital outflows, LGFV refinancing and European demand, and how much output never comes back (hysteresis).

**One window.** Every probability and every path covers 15 Oct 2026 – 31 Dec 2030.

Central reading: **{bust:.0%}** model weight on a 20%+ fall in AI equities inside the window; **{P['continued_boom']:.0%}** on a continuing boom; **{P['severe_burst_with_financial_crisis']:.0%}** on a full banking-crisis branch; **{c['joint']:.0%}** joint US banking crisis + China crisis. The 25 historical run-ups closest to today's ended in a 20%+ fall {n['bust']:.0%} of the time. These are model-conditional scenario weights, not objective frequencies or investment advice.

## Method in one page

- {chk['episodes']} run-up episodes (three-year real equity return of at least +50%) in {chk['countries']} economies, 1870–2021: World Bank indices after 1993, JST Macrohistory before. A fall is a peak-to-trough decline of 20%+ at annual closes within four years.
- Headline odds: what happened after comparable run-ups (100%+), with each global wave counted once ({t['method']['calibration']['anchorEpisodes']} episodes, {t['method']['calibration']['anchorWaves']} waves), then scaled by a funding-regime surface. Ranges come from a wave bootstrap.
- Four statistical models (ridge logit, boosting, forest, blend) were tested against that frequency with whole waves held out. None had reliable skill, so they are shown for validation, not used for the headline.
- Equity loss → banking crisis: JST country-years, same window.
- Connected simulator: one shared financial state per year (converged fixed point), then output gaps, a hysteresis stock and unemployment for the US, China and Europe, calibrated to JST output history and to Japan after 1989.
- The full parameter list, with the status of each (data, fixed rule, estimated, calibrated, assumed) and its source, is in the methodology section and in `site/data/methodology.json`. Static tables and CSV downloads: `site/tables.html`.

Read [docs/MODEL_RISK.md](docs/MODEL_RISK.md) before reusing any probability.

## Rebuild the model outputs

```sh
pip install numpy pandas scikit-learn
python model/fetch_data.py      # World Bank + JST, written to data/ (git-ignored)
python model/direct_release.py  # writes site/data/*.json and regenerates these docs
```

## Run locally

```sh
PORT=8080 HOST=127.0.0.1 python3 serve.py
```

Open <http://127.0.0.1:8080/> or use `docker compose up --build`. The health endpoint is `/healthz`.

As of 15 October 2026 (latest prices 14 October 2026), Europe/Zurich.
""")
    (ROOT / "docs/MODEL_RISK.md").write_text(f"""# Model risk and interpretation

## Intended use

Scenario analysis and stress testing. Not a trading signal, credit decision, regulatory-capital model, or claim that a crisis will occur.

## One window

Every probability covers 15 Oct 2026 – 31 Dec 2030 and is measured on annual closes. Every macro path runs 2026 (baseline year) to 2030. A longer view appears only in the hysteresis section, labelled 2036 with no new shock.

## Where the parameters are documented

The methodology section of the site lists every model and parameter with a status: **Data**, **Fixed rule**, **Estimated**, **Calibrated** or **Assumed**. Assumed entries (regime factors, finance-engine coefficients, channel weights, China-crisis coefficients, copula correlation, bootstrap widths) are judgments, not estimates; challenge them first.

## Historical crash check

- Run-ups of 100%+ (n={b['n']}): {b['boom']:.0%} boom, {b['sideways']:.0%} contained, {b['bust']:.0%} fall of 20%+.
- The 25 closest to today's state: {n['boom']:.0%} / {n['sideways']:.0%} / {n['bust']:.0%}. Model: {P['continued_boom']:.0%} / {P['no_burst_sideways']:.0%} / {bust:.0%}.
- Models were tested with whole global waves held out; the best has Brier skill of a few percent over the base rate and a ranking no better than chance, so the headline is a frequency, not a model output.
- Annual closes miss falls inside the year; in US monthly data they catch only about half of 20% falls, so fall probabilities are conservative.
- An earlier release showed 37% for "continued boom". That was a two-year weight labelled as a 2030 outcome; it is not supported on the four-year window.

## Main limitations

1. National-index run-ups are analogues for a concentrated 8-stock AI basket.
2. About 10 independent global crash clusters sit behind every tail estimate.
3. Annual closes understate intra-year troughs.
4. The equity-loss-to-banking-crisis link beats the base rate on held-out economies but not on held-out eras.
5. Finance-engine coefficients are structural stress parameters; they are not estimated and not in the bootstrap, so ranges understate total uncertainty.
6. China rests on one analogue (Japan after 1989) and cannot be validated against a Chinese crisis.
7. The systemic branch gives US output {s['us']['outputVsTrend2030'][1]:.1f}% against trend in 2030 (10th percentile {s['us']['outputVsTrend2030'][0]:.1f}%); history for 35%+ equity falls with a banking crisis has median {h['empiricalClasses']['deep_with_crisis']['p50']:.1f}% and 10th percentile {h['empiricalClasses']['deep_with_crisis']['p10']:.1f}%.
8. Treasury holdings indicate sale capacity, not intent; China debt perimeters overlap and cannot be summed; European relative gains need policy execution.

As-of date: 15 October 2026 (latest prices 14 October 2026), Europe/Zurich.
""")


if __name__ == "__main__":
    main()
