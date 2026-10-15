# Deployment: Global Economic Futures, 2026–2030

As of 2026-10-14 (Europe/Zurich).

## Status (read this first)

- **Not deployed.** No public URL is claimed in this build. A deployment is complete only after an external HTTPS request to the public URL returns the site, `/healthz` returns `ok`, and the download manifest is reachable. None of these checks has been run from outside the builder environment yet.
- **Local preview:** `serve.py` serves the built site. See `PREVIEW_INSTRUCTIONS.md`.
- **Browser tests:** a Python Playwright suite with headless Chromium ran against the Python server: 38 of 38 checks passed, including no CSP violations and no horizontal overflow at 390 px. Node.js is not used.
- **Docker image:** `Dockerfile` and `docker-compose.yml` are written but **were not built**, because Docker is not available on the builder host. The first real build must be run by the operator and recorded in the progress manifest.

## What is in the public repository

The public Git repository holds only the output of `deploy/export_public_bundle.py`, which copies an allowlist of files and scans them for private markers before writing `BUNDLE_MANIFEST.json`:

| File in the repository | Purpose |
|---|---|
| `Dockerfile`, `.dockerignore` | Image build. Copies only `serve.py` and `site/` into the image. |
| `docker-compose.yml` | Local run with the same limits as the free host |
| `render.yaml` | Render Blueprint (Docker, free plan, health check `/healthz`). No secrets. |
| `serve.py` | Standard-library static server |
| `site/` | The built site, data, downloads and manifests |
| `README.md`, `docs/` | Public readme, this document and the methods and model-risk note |
| `BUNDLE_MANIFEST.json` | Path, size and SHA-256 of every file in the repository |

Build tooling, tests, source code, the agent runtime and the research artifacts are not in the repository.

## Hosting choice: Render free Docker web service

Render is the chosen host. Free-plan terms are below with their verification status. Render changes its terms, so re-check the items marked "not verified" in the dashboard before launch. Each figure cites its official page; the terms were last checked on 2026-10-14.

| Term | Status on 2026-10-14 |
|---|---|
| Free web service with the `free` instance type | Recorded in the hosting preflight. Confirm when creating the service. |
| 750 free instance hours per workspace per calendar month | Confirmed on Render's free-plan page (re-checked 2026-10-14) |
| Service sleeps after 15 idle minutes | Confirmed on Render's free-plan page |
| Free services are not intended for production | Confirmed on Render's free-plan page |
| Dockerfile builds on Render | Confirmed in general on Render's Docker page. |
| Docker runtime on the Free instance type | **Not verified.** The pages reviewed do not say the Free instance type can run Docker services. Confirm in the dashboard when creating the service. |
| 5 GB outbound bandwidth per month (Hobby workspace) | Confirmed on Render's outbound-bandwidth page (re-checked 2026-10-14). Free services count against it. |
| 500 pipeline (build) minutes per month (Hobby workspace) | Confirmed on Render's build-pipeline page (re-checked 2026-10-14). Free services count against it. |
| Suspension, not billing, if bandwidth or build minutes are exceeded without a payment method | Confirmed on Render's outbound-bandwidth and build-pipeline pages. |
| First request after sleep takes about one minute | Stated on Render's free-plan page. Measure it after deployment. |
| No payment method needed for the free deploy path | Stated in Render's first-deploy tutorial only. If Render asks for a payment method or phone verification, stop and record the request. Do not supply a payment method. |

The site runs on a free Render web service with these settings:

| Item | Value |
|---|---|
| Service type | Docker web service, built from `Dockerfile` in the repository root |
| Architecture | `linux/amd64` |
| Port | `0.0.0.0:$PORT` (Render sets `PORT`; the Blueprint uses `10000`) |
| Health check path | `/healthz` |
| Storage | Ephemeral. The site writes nothing at runtime, so no persistent disk is needed. |
| TLS | Managed certificate for `*.onrender.com`. Custom domains are optional. |

Render's free plan is not for production workloads. The site is static and read-only, which keeps the risk low, but availability is not guaranteed.

## Alternatives considered

The following have not been re-checked on their current terms. Treat their figures as preflight records only.

- **Koyeb free web service:** the preflight recorded a lower-cost fallback with larger egress. It also recorded that a card is required. Use it only if Render's bandwidth limit is at risk.
- **Oracle Cloud Always Free:** more resources, but verification with a card and phone is recorded, along with capacity limits. The operator would maintain the OS, Docker, firewall and TLS.
- **Cloudflare Pages:** a static-only option. It does not run a Docker image, so it fits only if the Docker requirement is relaxed.

## Operator steps (Render)

The operator owns the browser account and performs these steps. The builder holds no credentials and stores none.

1. Sign in to Render in the browser.
2. Build the bundle locally: `python3 build/build_site.py`, then `python3 build/verify_site.py`, then `python3 deploy/export_public_bundle.py`. The bundle is written to `public-bundle/`.
3. Create a **public** Git repository whose contents are exactly the bundle. Do not add the build tree, source code, tests, agent runtime, progress files or research artifacts.
4. In Render, create a new Blueprint from that repository, or a Web Service with the Docker runtime and the Free instance type. Confirm that `Dockerfile` is at the repository root and the health check path is `/healthz`.
5. Deploy. In the build log, check that the base image is `python:3.13.9-slim-bookworm` and that the server starts as the non-root user `10001`.
6. Only after step 7 passes, record the public URL in the progress manifest.
7. From outside the builder environment, request `https://<service>.onrender.com/`, `/healthz`, `/manifests/download_manifest.json` and one file from the download manifest. Check the status codes, the `Content-Type` and `X-Content-Type-Options` headers. Compare the downloaded file's SHA-256 with the manifest.

## Container design

- Base image `python:3.13.9-slim-bookworm`, pinned by tag and built for `linux/amd64`. There is no floating `latest` tag.
- Runs as a non-root user (`app`, UID 10001, no login shell, no home directory).
- Copies only `serve.py` and `site/` into the image. `.dockerignore` is an allowlist, so everything else is excluded.
- Standard library only: no `pip install` at build time, so there is no package supply-chain step and the image stays small.
- `HEALTHCHECK` requests `/healthz` on the bound port using Python's standard library.
- `docker-compose.yml` sets a read-only root filesystem, `no-new-privileges`, all capabilities dropped, 0.25 CPU, 128 MB memory, 64 processes and capped log size. The server writes nothing.

## HTTPS plan

- Render terminates TLS and issues the certificate for `*.onrender.com`. The server listens on plain HTTP inside the container, as Render expects.
- The server sends `Strict-Transport-Security`, `X-Content-Type-Options`, `Referrer-Policy` and `Permissions-Policy`. The site makes no third-party requests.
- A custom domain can be added later. DNS is owned by the operator. The first deployment does not need a domain.

## Free-tier economics

- **Cash cost:** zero, provided no paid plan is attached and no payment method is added to clear a limit. Cash cost depends on the "not verified" terms above and must be confirmed in the dashboard.
- **Bandwidth budget:** the largest part of the site is `site/downloads/`. Its size is in `manifests/download_manifest.json` (`totalBytes`). Most visits load only the HTML, CSS, JavaScript and the data files. At 5 GB per month, the number of full-download visits is 5 GB divided by the total download size. Check this against the figure in the dashboard once it is confirmed.
- **Build minutes:** one Docker build is expected to take a few minutes. Rebuilds must stay well within the monthly allowance.
- **Trigger:** deployment is manual (`autoDeploy: false`). No schedule or background job runs.

If bandwidth is at risk, the options are: reduce the downloads, host large files elsewhere under the operator's control, or move to the alternatives above. Each change needs a new deployment check.

## Rollback

1. In the Render dashboard, open the service, go to the deploy history and redeploy the last known-good deploy.
2. If the repository must be reverted, revert the commit in the public repository. Do not force-push the default branch. Auto-deploy is off in `render.yaml`, so a push does not redeploy: trigger a manual deploy in the dashboard afterwards.
3. After any rollback, repeat the external checks in step 7 of the operator steps.
4. Record the rolled-back deploy ID and the reason in the progress manifest.

## Maintenance

- **Health:** check `/healthz` after every deploy.
- **Updates:** update the pinned base image tag deliberately, then rebuild and re-verify.
- **Content changes:** rebuild the site, verify it, export the bundle, then commit and push the public repository (the three commands in step 2 above).
- **Monitoring:** check bandwidth and build minutes in the Render dashboard each month. Expect a delay on the first response after a quiet period.
- **Data age:** the as-of date is 2026-10-14. Each observation carries its own date. Do not add observations dated after the as-of date. Data that is not yet available is marked as unavailable.
- **Secrets:** no credentials or tokens are stored in the repository, the image or the site. Do not paste credentials into the progress manifest or into this repository.

## Human action required

The operator completes the Render sign-in and the first deployment in the browser, then provides the public URL for external verification. If Render asks for a card, a payment method, phone verification or a paid plan, stop and record the request. Do not supply a payment method to clear it.
