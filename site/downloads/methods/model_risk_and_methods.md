# Global Economic Futures, 2026–2030: methods, reproducibility and model risk

As of 2026-10-14 (Europe/Zurich). Run `gef-main-20261014`. Status: research checkpoint-recovery-1 and model execution `execution-rerun_models-1792005512896` are accepted; the public site is a static read-only explorer built from those accepted artifacts.

## 1. What the numbers are

- **Scenario paths** are conditional stories built from stated assumptions. They are not forecasts.
- **Percentile bands** (p01–p99, 5th–95th) describe spread under the stated parameter bounds and sampling design. They are not calibrated probabilities.
- **The 70% AI revenue-loss case** is a stress test. It is not an estimated probability of that outcome.
- **Sensitivity sweeps** test whether conclusions survive changes in a parameter. They are robustness checks, not estimated causal effects.
- Every published figure carries one of five labels: **Observed**, **Computed**, **Assumed**, **Simulated**, **Uncertain**.

## 2. Accepted execution

Source: `simulations/execution-rerun_models-1792005512896.json` (state `passed`, seed 20261014, requested global samples 10,000).

| Check | Result |
|---|---|
| Deterministic global paths | 9 scenarios, 144 rows (passed) |
| Monte Carlo, global | n = 10,000, 144 rows (passed) |
| Sensitivity sweeps | 11 parameters, 296 results (passed) |
| Accounting identities | 49 identities, all passed |
| Unit and logic tests | 50 of 50 passed, 0 failed |

Model re-review acceptance is recorded in `reviews/models/model_re_review/iteration-0/findings.json`.

## 3. Modules and their status

| Module | Output used by the site | Status and caveat |
|---|---|---|
| Global transmission (demand-index deviation from 2026 = 100) | `models/global/outputs/*` | Accepted. Results are normalized indices, not GDP forecasts. |
| US top-five companies | Observed bridge `accepted-evidence/us/debt-commitment-bridge.*` and gross commitment inventory `models/company/output/commitment_inventory.json` | **Simulated company liquidity paths are withheld.** The accepted company run omits refinancing proceeds (reviewer correction MR02). A current-code regeneration exists in the build tree but has not been re-accepted, so it is not published. The 15 commitment items are gross amounts and are not added to cash uses. |
| China funding, property and demographics | `models/china/deterministic-scenarios.csv`, `models/china/monte-carlo-summary.json` (2,000 draws) | Accepted as scenario and design-sensitivity outputs. Funding-stress fractions use assumed pools and maturities. |
| EU raw materials (NdFeB) | `models/eu/outputs/materials_scenario_2030.*`, `project_capacity_scenarios.csv` | Feasibility envelope from a source model (8–19% secondary supply share of selected-application demand; 2.88–6.84 kt of 36 kt). Not observed output. |
| Switzerland branches | `models/swiss/outputs/deterministic.*`, `monte_carlo_summary.json` (2,000 draws) | Branches are design conditions. The signed package is conditional on entry into force. Status-quo erosion and safe-haven reversal are assumed paths. The severe branch has **no CPI pass-through and a zero GDP delta** in the deterministic module; this is a known limit, not a finding. |

The regional standalone outputs (China, EU, Switzerland) are regional-adapter or module outputs. They are covered by the accepted execution with the caveat recorded in the accepted-bundle limits.

## 4. Parameter estimation and identification

- Parameter values are taken from the source-linked baseline files (`accepted-evidence/<region>/baseline.json`). Each quantitative assumption has either a source ID or an explicit assumed label.
- Where a parameter has no direct observation, it is bounded rather than estimated. The model command specification (`models/global/command-spec.json`) is the place to check the parameter definitions used in the run.
- Parameter correlations come from the dependence-sensitivity file (`sensitivity_dependence.csv`). The correlation structure is a sensitivity assumption and is not estimated from data.
- Transmission from company or sector shocks to macro demand is not identified from the evidence. It is modelled as a mapping, so it cannot be read as a causal estimate.
- Cross-country and historical analogue comparisons (for example the 2001 telecom analogue) are illustrative, not identified causal tests.

## 5. Known model limits

1. The company liquidity module is withheld (see section 3). No simulated company values are shown anywhere on the site.
2. The 70% AI revenue-loss case is a stress design and should be read as a plausibility bound on sensitivity, not as an expected outcome.
3. Swiss severe branch: no CPI pass-through and zero GDP delta in the deterministic run. Treat it as a structural placeholder for that channel, not as an estimate.
4. EU secondary-supply shares come from one source model's scenario envelope. The 30% recycling-sufficiency claim sits above that envelope.
5. Bank exposure bounds for the EU are partial coverage.
6. Narrative numbers in the site were checked against the ledgers and outputs, but the site is not a substitute for the underlying ledgers. Use the downloads to verify.
7. Scenario labels describe conditions to test. They are not likelihood rankings.

The accepted use limits U01–U08 are listed in `evidence/accepted_use_limits.json` in the downloads. Those limits apply to any reuse of these outputs.

## 6. Reproducing the results

1. Read `models/global/command-spec.json` for the exact commands, input hashes and expected outputs. The accepted execution recorded the command hash, code hash and input hash for each check.
2. Run the deterministic, Monte Carlo (seed 20261014, 10,000 draws), sensitivity, accounting and test commands in that order.
3. Compare the produced files with the downloads by SHA-256. The site manifest `manifests/download_manifest.json` lists the hash of each published file.
4. Rebuild the site with `python3 website/build/build_site.py` (standard library only) and check it with `python3 website/build/verify_site.py`.

Limitations of this reproduction: the Docker image build was not run in the builder environment, because Docker is not available there (see `docs/DEPLOYMENT.md`). The site was checked with the Python static server and a headless Chromium browser suite (38 of 38 checks passed, see `PREVIEW_INSTRUCTIONS.md`).

## 7. Model risk register (summary)

| Risk | Effect | Mitigation in this build |
|---|---|---|
| Overreading percentile bands as probabilities | False precision | Bands labelled as design percentiles; captions say so |
| Company paths used as forecasts | Unsupported liquidity claims | Company simulated paths withheld; observed bridge only |
| Equity prices used as cash-flow evidence | Wrong inference | Not used; cash-flow and filing evidence only |
| Narrative drift from ledgers | Inconsistent statements | Numbers checked against ledgers and outputs before publication |
| Stale data presented as current | Misleading as-of | Visible as-of and source periods; unavailable October 2026 data is labelled |
| Synthetic test fixtures used as evidence | Invalid sources | The software-test fixture folder is excluded from the research and the site |
