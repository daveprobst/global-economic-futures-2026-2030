# Global Economic Futures, 2026–2030: explorer

A static, read-only English research and scenario explorer. Every figure is labelled **Observed**, **Computed**, **Assumed**, **Simulated** or **Uncertain**. Scenario paths are conditional stories, not forecasts. Percentile bands describe spread under stated bounds, not calibrated probabilities. The 70% AI revenue-loss case is a stress test, not an estimated probability.

As of 2026-10-14 (Europe/Zurich). Each observation carries its own date. Data that is not yet available is marked as unavailable.

## What is in this repository

- `site/`: the built website and its data, downloads and manifests. Nothing is computed at runtime.
- `serve.py`: a standard-library Python server for `site/`. It serves files only, with a health endpoint at `/healthz`.
- `Dockerfile`, `.dockerignore`, `docker-compose.yml`: container build and local run. The image runs as a non-root user with the site and server only.
- `render.yaml`: a Render Blueprint for a free Docker web service.
- `docs/DEPLOYMENT.md`: hosting, free-tier terms, HTTPS, rollback and maintenance.
- `docs/MODEL_RISK.md`: methods, reproducibility and model limits.
- `BUNDLE_MANIFEST.json`: the path, size and SHA-256 of every file in this repository.

## Run locally

Python 3.10 or newer, no packages to install:

```sh
PORT=8080 HOST=127.0.0.1 python3 serve.py
```

Then open http://127.0.0.1:8080/ and check http://127.0.0.1:8080/healthz, which returns `ok`.

With Docker:

```sh
docker compose up --build
```

Then open http://localhost:8080/.

## Endpoints

| Path | Purpose |
|---|---|
| `/` | The explorer |
| `/healthz` | Health check (`ok`) |
| `/manifests/content_manifest.json` | Sections, claims, mechanisms and sources |
| `/manifests/download_manifest.json` | Every downloadable file with size and SHA-256 |

## Security

- Responses carry a Content-Security-Policy that allows same-origin scripts, styles and data only.
- `X-Content-Type-Options: nosniff`, a strict Referrer-Policy and no framing.
- The site makes no third-party requests and uses no cookies or storage.
- No secrets, tokens or credentials are in this repository.

## Licence and sources

The data and text are research outputs. Source titles, URLs, periods and retrieval metadata are listed in `manifests/content_manifest.json` and `manifests/download_manifest.json`. Check the source records before reusing any figure.
