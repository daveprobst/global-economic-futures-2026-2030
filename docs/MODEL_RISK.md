# Model risk and interpretation

## Intended use

This release is a scenario-analysis tool for examining mechanisms in the 2026–2030 AI investment, China debt, global liquidity, EU, and Swiss outlook. It supports research discussion, stress testing, and monitoring. It is not suitable for trading, credit approval, regulatory capital, portfolio optimisation, or a claim that a crisis will occur.

## What is estimated

The broad equity outcome is estimated from 127 non-overlapping annual run-up episodes in 37 countries. Two L2-regularised multinomial logistic regressions map three frozen run-up features to three outcome bands: continued boom, no-burst/sideways, and a drawdown of at least 20%. Features are scaled inside each training fold. The models are evaluated by leaving one country out at a time and averaging their predicted distributions.

The current AI-linked basket is mapped into that historical feature space. Nine combinations of geopolitical risk and liquidity conditions then apply prespecified hazard multipliers. Current state weights average those conditional distributions.

The seven public scenario classes are an exact partition, but history does not identify all seven separately. Mild, moderate, deep, severe, liquidity-vacuum, and financial-crisis splits use structural calibration. The site therefore gives more evidential weight to the aggregate 20%+ adjustment estimate than to any tail subclass.

## What is simulated

- 10,000 fixed-seed classifications propagate state and classification uncertainty.
- Country-cluster bootstrap refits the historical layer to form model-conditional intervals.
- GDP, inflation, unemployment, equity, credit, and policy-rate paths are conditional scenario designs, bounded against public stress-test ranges where inputs were available.
- China debt blocks are ranges with overlap warnings, not an additive hidden-debt total.
- The joint US-systemic and China-crisis estimate multiplies the US systemic branch by a conditional China-crisis calibration. It is a stress-model output with a broad uncertainty range, not an empirically identified joint frequency.

## Validation evidence

The leave-one-country-out Brier score improves modestly on the unconditional base-rate predictor. The log-score improvement is small. This means the model contains limited ranking information and does not justify narrow confidence. The website displays this comparison beside the method.

The browser release was checked at 1440×1000 and 390×844: all eight JSON inputs loaded, all nine chapters rendered, source search and scenario switching worked, the light/dark control worked, no horizontal overflow occurred, and Chromium reported no console, page, or Content Security Policy errors.

## Main limitations

1. Annual country episodes are only an analogue for a concentrated AI-linked equity basket.
2. The effective crisis sample is small; bootstrap intervals do not span all structural uncertainty.
3. The historical layer has only three outcomes. The seven-class tail split depends on assumptions.
4. State weights and hazard multipliers are judgmental and can dominate rare-event results.
5. Conditional macro paths are internally coherent stories rather than an estimated structural macro model.
6. AI-linked market-cap exposure is not the size of a bubble premium.
7. Growth less direct AI investment is an accounting exclusion, not a causal no-AI counterfactual.
8. China local-government, property, and shadow-credit ranges overlap and cannot be summed mechanically.
9. The contagion network visualises transmission channels and sensitivities; it does not estimate a causal network.
10. The reported joint-crisis probability is especially sensitive to dependence assumptions and should be treated as a tail stress indicator.

## Monitoring and change control

Re-estimate after a material revision to the World Bank equity series, a change in basket membership, or a regime shift in liquidity/geopolitical inputs. Revisit the model if its rolling Brier score no longer beats the base-rate forecast or if observed outcomes fall outside the scenario taxonomy. Any change to taxonomy, feature definitions, state weights, hazard multipliers, or tail splits requires a new dated release and refreshed validation.

Model owner: repository maintainer. As-of date: 15 October 2026, Europe/Zurich.
