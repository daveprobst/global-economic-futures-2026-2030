# Model risk and interpretation

## Intended use

This is a scenario-analysis and stress-testing tool. It is not a trading signal, credit decision, regulatory-capital model, or claim that a crisis will occur.

## Probability architecture

The broad outcome model starts from 127 annual equity run-up episodes in 37 countries. Regularised multinomial logits supply 75% of the estimate. Gradient boosting and random forest are capped at 15% and 10% because their leave-country-out performance is weaker. A monotonic geopolitical × dollar-liquidity surface conditions the broad result.

The seven public outcomes form an exact partition. “Contained repricing” means a drawdown below 20% and a 24-month return no higher than 10%. Mild is a 20–35% decline; moderate is 35–50%; severe is at least 50%, separated by whether broad liquidity holds, a liquidity vacuum develops, or systemic financial stress follows. Among 93 non-bust historical episodes, 23 met the contained-repricing rule; the Jeffreys posterior mean is 25.0% conditional on no bust.

## Equity loss to banking crisis

The former fixed severe-tail split has been removed. A separate regularised logit matches World Bank equity returns to JST Macrohistory balance sheets and banking-crisis starts. It uses 476 country-years in 17 countries, including 39 crisis starts. Inputs are the two-year equity drawdown, preceding three-year run-up, loans/GDP, five-year credit growth, public debt/GDP and the short rate.

Leave-one-country-out validation produces a Brier score of 0.057 versus 0.075 for the constant base rate and AUC of 0.833. At current US balance-sheet inputs, the estimated banking-crisis transition is 6.6% after a 20% drawdown, 28.3% after 50%, 48.3% after 65%, and 62.4% after 75%. Integrating that curve over 50–76% severe declines sets the systemic share of the severe tail. Annual closes understate intrayear losses, and synchronized global events remain a small effective sample.

## Connected stress simulator

For each scenario, 4,000 paths update a shared state within every year. AI trust changes revenue coverage while chip, power and data-centre commitments remain sticky. Funding costs, collateral losses, margin calls, forced sales and liquidity then update together. Chinese outflows, LGFV refinancing and Treasury-sale pressure feed back into US dollar liquidity. US systemic stress raises China crisis risk, while Chinese stress worsens the US funding state.

The current weighted output is 13.8% US systemic, 21.1% China crisis and 12.3% joint by 2028. Within the US systemic branch, 89.2% of paths also cross the China crisis threshold. The 6.8–20.3% joint range is parameter sensitivity, not a frequentist confidence interval. US banking-crisis transition risk is statistically calibrated; China and cross-border elasticities remain transparent structural stress parameters.

## Historical crash lab

The site compares annual aggregate real-GDP growth and chained levels with the US dot-com unwind, the US and euro-area GFC paths, Japan after 1990 and the pandemic. Dot-com demonstrates that a valuation crash can remain non-systemic when losses are dispersed. The GFC demonstrates the nonlinear result when losses are concentrated in leveraged financial nodes. Japan demonstrates persistent level damage without requiring consecutive annual contractions. Annual data hide intrayear troughs, and the pandemic is used only as a magnitude check.

## Main limitations

1. Annual country episodes are analogues for a concentrated AI basket.
2. Global crash clusters are scarce, so tail uncertainty remains wide.
3. The connected model reproduces accounting mechanisms and historical ranges; most elasticities are not separately causal estimates.
4. Hyperscaler stress requires a combined revenue, commitment and funding shock; the largest firms remain cash-generative in the baseline.
5. Treasury holdings indicate potential sale capacity, not intent.
6. The 47.4% broad technology/platform proxy is not an estimate that the whole sector is an AI bubble.
7. China debt perimeters overlap and cannot be summed mechanically.
8. European relative gains arrive only after the acute recessionary hit and require policy execution.

As-of date: 15 October 2026, Europe/Zurich.
