# Hosting status and free-tier terms

Status as of 2026-10-14 (Europe/Zurich). This document replaces the earlier hosting preflight
decision and provider comparison, which were written before the terms were re-checked and before
the operator's account sign-in. Those earlier files are no longer published because parts of them
are out of date.

## Current status

- **Provider:** Render. Free Docker web service (plan `free`) in a Hobby workspace.
- **Deployed:** no. No public URL exists yet.
- **Public repository:** not created by the build tooling. The repository must contain only the
  public source tree, not the research workspace.
- **Local Docker check:** the Dockerfile has not been built or run. Docker is not installed on the
  builder host. The local preview (`serve.py`) was checked instead, with its HTTP, browser and
  download checks.
- **Account:** the root operator reports a Render sign-in in a browser. The build did not verify
  it. No API key or service ID has been provided to the build tooling, and no payment method has
  been linked.

## Free-tier terms (checked 2026-10-14 against the official Render pages)

"Confirmed" means the wording was read on the official page on the check date. It does not mean a
service exists or a deploy has succeeded.

| Term | Status | Official source |
|---|---|---|
| 750 free instance hours per workspace per calendar month | Confirmed | Render free-plan page (`render.com/docs/free`) |
| Spin-down after 15 minutes without inbound traffic; about one minute to wake | Confirmed | Render free-plan page |
| Free instances are for testing and hobby use and should not be used for production | Confirmed | Render free-plan page |
| Ephemeral filesystem on free web services; changes are lost on redeploy, restart or spin-down | Confirmed | Render free-plan page |
| Hobby workspace: 5 GB outbound per month (Pro 25 GB, Scale 1 TB) | Confirmed | Render outbound-bandwidth page |
| Overage $0.15 per GB for public internet traffic | Confirmed | Render outbound-bandwidth page |
| Hobby workspace: 500 pipeline minutes per month (Pro 1000, Scale 5000) | Confirmed | Render build-pipeline page |
| Free web services count against the included outbound and pipeline-minute allowances | Confirmed | Render free-plan page |
| Without a linked payment method, workspace services are spun down for the rest of the month when outbound allowance is exceeded; pipeline tasks including builds stop for the rest of the month when minutes run out; free services are suspended when free instance hours run out | Confirmed | Render outbound-bandwidth, build-pipeline and free-plan pages |
| Dockerfile builds are documented | Documented in general | Render Docker page (`render.com/docs/docker`) |
| Docker services can be created on the **Free** instance type | **Not confirmed** on the pages reviewed | Check in the dashboard when creating the service |
| Free plan offered in the Frankfurt region | **Not verified** | Check in the dashboard |
| Free tier is permanent | **Not guaranteed.** No end date is stated and it is not described as a trial. Terms may change. | Render free-plan page |

The 5 GB and 500-minute figures are Hobby workspace allowances. The free-plan page does not state
them, so they are cited to the Hobby pages.

If the Free instance type cannot run a Docker service in the dashboard, the service cannot be
created on the free plan. Do not choose a paid plan without a separate decision by the operator.

## Operator steps before launch

1. Create or choose a public Git repository. Push only the public source tree.
2. Authorise Render's Git integration for that one repository.
3. Create the service from the Blueprint (`render.yaml`) or by hand: runtime Docker, plan Free,
   health check `/healthz`, auto-deploy off.
4. Confirm in the dashboard that a Docker service can be created on the Free instance type and that
   Frankfurt is offered. If Frankfurt is not offered, change the region and rebuild.
5. Do not link a payment method.
6. After the first deploy, record the public URL and the `/healthz` result in the progress record,
   then check the site over HTTPS.

## Rollback and maintenance

Auto-deploy is off, so a repository push does not redeploy. Roll back from the dashboard's deploy
history, or revert the commit in the public repository and trigger a manual deploy. Check the
usage page each month against the 5 GB outbound, 500 build-minute and 750 instance-hour allowances.
