# Fault Lines — Global Economic Futures 2026–2030

An English static research dashboard testing how an AI valuation reset could propagate through hyperscaler commitments, funding spreads, forced liquidations, Treasury liquidity, China capital outflows, LGFV refinancing and European demand, and how much output never comes back (hysteresis).

**One window.** Every probability and every path covers 31 Oct 2026 – 31 Dec 2030.

Central reading: **76%** model weight on a 20%+ fall in AI equities inside the window; **14%** on a continuing boom; **15%** on a full banking-crisis branch; **14%** joint US banking crisis + China crisis. The 25 historical run-ups closest to today's ended in a 20%+ fall 72% of the time. These are model-conditional scenario weights, not objective frequencies or investment advice.

## Method in one page

- 301 run-up episodes (three-year real equity return of at least +50%) in 67 economies, 1870–2021: World Bank indices after 1993, JST Macrohistory before. Outcomes use the next four annual closes.
- Predictors are the 3-year run-up and last-12-month return. Volatility is excluded (not comparable for a 20-stock basket; no out-of-sample skill).
- 75% ridge-logit, 15% gradient boosting, 10% random forest, calibrated on leave-country-out predictions; geopolitical × dollar-liquidity regime scaling; year-cluster bootstrap for intervals.
- Equity loss → banking crisis: 16 economies, 1,924 country-years, same window.
- Connected simulator: one shared financial state per year, then output gaps, hysteresis and unemployment for the US, China and Europe, calibrated to JST output history and to Japan after 1989.
- Historical checks, cross-validation and nearest analogs are in `site/data/historical_checks.json`; hysteresis calibration and validation in `site/data/hysteresis.json`.

Read [docs/MODEL_RISK.md](docs/MODEL_RISK.md) before reusing any probability.

## Rebuild the model outputs

```sh
pip install numpy pandas scikit-learn
python model/fetch_data.py      # World Bank + JST, written to data/ (git-ignored)
python model/direct_release.py  # writes site/data/*.json
```

## Run locally

```sh
PORT=8080 HOST=127.0.0.1 python3 serve.py
```

Open <http://127.0.0.1:8080/> or use `docker compose up --build`. The health endpoint is `/healthz`.

As of 31 October 2026, Europe/Zurich.
