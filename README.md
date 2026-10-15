# Fault Lines — Global Economic Futures 2026–2030

An English static research dashboard testing how an AI trust and valuation break could propagate through hyperscaler commitments, funding spreads, forced liquidations, Treasury liquidity, China capital outflows, LGFV refinancing and European demand.

The revised central estimate is **50.5% for a 20% or greater AI-equity adjustment by October 2028**. The full systemic branch is **13.3%** because it additionally requires a liquidity vacuum and financial-system stress. These are model-conditional scenario weights, not objective frequencies or investment advice.

## Method in one page

- 127 non-overlapping annual equity run-up episodes across 37 countries.
- A 75% regularised-logit core with capped gradient-boosting (15%) and random-forest (10%) challengers. The nonlinear models perform worse out of sample and therefore cannot dominate the estimate.
- A transparent monotonic geopolitical × liquidity stress surface replaces the previous unstable historical state multipliers.
- Seven mutually exclusive outcome classes use explicit drawdown thresholds. The non-bust split is estimated from 93 episodes; the severe split collapses 11 synchronized country rows into two independent global crash clusters before applying Jeffreys-Dirichlet shrinkage.
- A 2,400-path shared-state simulator links AI trust, cash-flow coverage, marginal funding, equity losses, margin calls, liquidity, Treasury-sale pressure, China outflows and LGFV refinancing.
- Persistent macro paths are benchmarked to the Federal Reserve 2026 severely adverse design and the 2007–09 US contraction.

Read [docs/MODEL_RISK.md](docs/MODEL_RISK.md) before reusing any probability.

## Run locally

```sh
PORT=8080 HOST=127.0.0.1 python3 serve.py
```

Open <http://127.0.0.1:8080/> or use `docker compose up --build`. The health endpoint is `/healthz`.

As of 15 October 2026, Europe/Zurich.
