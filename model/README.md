# Reproducible model source

Run `python model/fetch_data.py` (World Bank WDI, JST Macrohistory R6; written to `data/`, git-ignored), then `python model/direct_release.py`, which rewrites `site/data/*.json`.

| File | Role |
|---|---|
| `equity_panel.py` | Pooled real-return run-up episodes, four-year outcome window |
| `systemic_transition.py` | Equity loss → banking-crisis transition (JST, 1870–2016 origins) |
| `engine.py` | Connected finance state, output gaps, hysteresis, unemployment |
| `hysteresis.py` | Empirical output-shortfall targets (JST) and calibration of the engine |
| `checks.py` | Frequency tables, nearest analogs, leave-country-out and leave-era-out validation |
| `direct_release.py` | Scenario weights, outputs and site data |
| `inputs/` | Frozen inputs: regime weights, US AI decomposition, China debt, contagion network |

Seeded (20261014); results are reproducible given the same downloaded data vintage.
