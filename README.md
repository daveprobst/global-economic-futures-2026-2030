# Fault Lines — Global Economic Futures 2026–2030

An English static research dashboard testing how an AI valuation reset could propagate through hyperscaler commitments, funding spreads, forced liquidations, Treasury liquidity, China capital outflows, LGFV refinancing and European demand, and how much output never comes back (hysteresis).

**One window.** Every probability and every path covers 15 Oct 2026 – 31 Dec 2030.

Central reading: **77%** model weight on a 20%+ fall in AI equities inside the window; **18%** on a continuing boom; **14%** on a full banking-crisis branch; **12%** joint US banking crisis + China crisis. The 25 historical run-ups closest to today's ended in a 20%+ fall 84% of the time. These are model-conditional scenario weights, not objective frequencies or investment advice.

## Method in one page

- 301 run-up episodes (three-year real equity return of at least +50%) in 67 economies, 1870–2021: World Bank indices after 1993, JST Macrohistory before. A fall is a peak-to-trough decline of 20%+ at annual closes within four years.
- Headline odds: what happened after comparable run-ups (100%+), with each global wave counted once (71 episodes, 9 waves), then scaled by a funding-regime surface. Ranges come from a wave bootstrap.
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
