# Fault Lines — Global Economic Futures 2026–2030

An English, static research dashboard testing whether the AI investment cycle can transmit into a broader global liquidity shock. The site presents seven mutually exclusive scenario classes, conditional macro paths, US/AI exposure, China debt ranges, contagion channels, a joint-crisis stress estimate, country balance sheets, and a searchable 69-source register.

The central estimate is **28.5% for a 20% or greater AI-equity adjustment by October 2028**. The full US systemic-crisis branch is **0.7%**. These are model-conditional estimates from a small historical episode panel, not objective frequencies or investment advice.

## Method in one page

- 127 non-overlapping annual equity run-up episodes across 37 countries, built from the World Bank/S&P Global annual equity-index return series.
- Two regularised multinomial logistic models with fold-local scaling, averaged after leave-one-country-out evaluation.
- Nine geopolitical-risk and global-liquidity states reweight the episode-model probabilities.
- Seven final classes split the broad drawdown bands using transparent structural stress assumptions.
- 10,000 fixed-seed classifications and a country-cluster bootstrap produce the displayed ranges.
- Conditional paths are scenario designs. They are not expected-value forecasts.

The historical model has weak but positive discrimination against a base-rate benchmark. Subclass splits, contagion paths, and the joint-crisis estimate rely more heavily on assumptions than the broad adjustment probability. Read [docs/MODEL_RISK.md](docs/MODEL_RISK.md) before reusing any probability.

## Run locally

No runtime packages are required:

```sh
PORT=8080 HOST=127.0.0.1 python3 serve.py
```

Then open <http://127.0.0.1:8080/>. The health endpoint is <http://127.0.0.1:8080/healthz>.

With Docker:

```sh
docker compose up --build
```

## Deployment

The image uses a small Python slim base, runs as an unprivileged user, serves only static files, and is configured for Render's free Docker service. Render terminates TLS and calls `/healthz`. The site makes no third-party browser requests and stores no cookies, analytics, credentials, or personal data.

As of 15 October 2026, Europe/Zurich.
