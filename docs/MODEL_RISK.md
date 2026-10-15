# Model risk and interpretation

## Intended use

This release is a scenario-analysis and stress-testing tool. It is not a trading signal, credit decision, regulatory-capital model, or claim that a crisis will occur.

## Probability architecture

The broad outcome starts from 127 annual equity run-up episodes in 37 countries. Two regularised multinomial logits are the calibrated core. Gradient boosting and random forest act as capped nonlinear challengers at 15% and 10% weights because their leave-country-out performance is weaker and their current estimates are unstable. The resulting broad probability is conditioned on an explicitly monotonic geopolitical × liquidity surface. Those multipliers are structural stress assumptions rather than fitted frequencies.

The seven public classes form an exact partition: boom and sideways remain below a 20% drawdown; mild is 20–35%; moderate is 35–50%; severe is at least 50%, separated by whether broad liquidity holds, a liquidity vacuum develops, or systemic bank/market stress follows.

## Connected stress simulator

For each scenario, 2,400 paths update a shared state within each year. The system links:

- AI trust and revenue realisation;
- sticky power, chip and data-centre commitments;
- cash-flow coverage and hyperscaler marginal funding rates;
- equity losses, collateral calls, forced sales and liquidity;
- China capital outflow and Treasury-sale pressure;
- LGFV refinancing costs and China balance-sheet stress;
- US, China and EU real GDP growth.

Margin calls depend on incremental collateral losses and run off after deleveraging. Liquidity can recover through policy offsets. This prevents both automatic one-year mean reversion and permanent mechanical collapse. Coefficients are stress-test elasticities chosen to reproduce public crisis ranges and directional accounting relationships; they are not separately econometrically identified.

## Validation and benchmarks

The historical logit layer only modestly improves Brier score versus the base rate. Nonlinear challengers do not improve out-of-sample performance, so the site discloses their disagreement rather than presenting them as superior forecasts. Severe GDP paths are bounded against the Federal Reserve's 2026 severely adverse scenario and BEA evidence from the 2007Q4–2009Q2 contraction.

The release checks that probabilities sum to one, the stress surface rises monotonically as geopolitical and liquidity regimes worsen, severe-system coverage falls below one, marginal hyperscaler and LGFV rates exceed 9%, and the systemic equity trough falls below 35 on a 2026=100 index. Browser QA passed at 1440×1000 and 390×844 with no page errors or horizontal overflow.

## Main limitations

1. Annual country episodes are analogues for a concentrated AI basket.
2. Rare crises are few; subclass probabilities are structurally calibrated.
3. The connected model reproduces mechanisms and plausible ranges, not identified causal elasticities.
4. Hyperscaler aggregate cash generation is strong today; commitment stress needs a simultaneous revenue and funding shock.
5. Treasury holdings show potential sale capacity, not intent to sell.
6. The 47.4% S&P sector proxy is not an AI-bubble estimate.
7. China debt perimeters overlap and cannot be summed mechanically.
8. European relative gains require successful policy execution and follow the initial recessionary hit.
9. The joint US–China tail is an order-of-magnitude stress weight.

As-of date: 15 October 2026, Europe/Zurich.
