# Fault Lines — Global Economic Futures 2026–2030

An English static research dashboard testing how an AI valuation reset could propagate through hyperscaler commitments, funding spreads, forced liquidations, Treasury liquidity, China capital outflows, LGFV refinancing and European demand, and how much output never comes back (hysteresis).

**One window.** Every probability and every path covers 31 Oct 2026 – 31 Dec 2030.

Central reading: **73%** model weight on a 20%+ fall in AI equities inside the window; **16%** on a continuing boom; **15%** on a full banking-crisis branch; **13%** joint US banking crisis + China crisis. The 25 historical run-ups closest to today's ended in a 20%+ fall 72% of the time. These are model-conditional scenario weights, not objective frequencies or investment advice.

## Method in one page

- 301 run-up episodes (three-year real equity return of at least +50%) in 67 economies, 1870–2021: World Bank indices after 1993, JST Macrohistory before. Outcomes use the next four annual closes.
- Predictors: 3-year run-up and last-12-month return. Volatility is excluded (an 8-stock basket is not comparable with a national index; no out-of-sample skill).
- 75% ridge-logit, 15% gradient boosting, 10% random forest, recalibrated on leave-one-economy-out predictions; geopolitical × dollar-liquidity scaling; year-cluster bootstrap for ranges.
- Equity loss → banking crisis: JST country-years, same window.
- Connected simulator: one shared financial state per year, then output gaps, a hysteresis stock and unemployment for the US, China and Europe, calibrated to JST output history and to Japan after 1989.
- The full parameter list, with the status of each (data, fixed rule, estimated, calibrated, assumed) and its source, is in the methodology section of the site and in `site/data/methodology.json`. Citations are in `site/data/citations.json`.

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

As of 31 October 2026, Europe/Zurich.
