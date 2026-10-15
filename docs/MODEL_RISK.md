# Model risk and interpretation

## Intended use

Scenario analysis and stress testing. Not a trading signal, credit decision, regulatory-capital model, or claim that a crisis will occur.

## One window

Every probability covers 31 Oct 2026 – 31 Dec 2030 and is measured on annual closes. Every macro path runs 2026 (baseline year) to 2030. A longer view appears only in the hysteresis section, labelled as 2036 with no new shock.

## Probability architecture

An episode starts when an equity market's real three-year return is at least +50%. Outcomes use the next four annual closes. The panel has 301 episodes in 67 economies (World Bank indices for origins from 1994, JST Macrohistory before; windows with inflation above 25% a year are dropped). The seven public outcomes partition the window: boom holds (no 20% fall, real return ≥5% a year), contained repricing (no 20% fall, lower return), mild (20–35% fall), moderate (35–50%), and three severe branches (50%+, split by liquidity vacuum and banking crisis).

A ridge-logit (75%), gradient boosting (15%) and random forest (10%) predict the fall bands from the 3-year run-up and last-12-month return; the blend is calibrated on leave-country-out predictions. A geopolitical × dollar-liquidity surface scales the odds. The AI basket is deflated with US inflation (2025 deflator stands in for 2025–26 as CPI ends in 2024).

## Historical crash check

- Run-ups of 100%+ (n=71): 28% boom, 15% contained, 56% fall of 20%+.
- The 25 closest to today's state: 12% / 16% / 72%. Model: 14% / 9% / 76%.
- Out-of-sample Brier skill over the base rate is 3% on held-out countries and 3% on held-out eras. Bust frequency is far higher since 1994 than before, and the model does not separate eras.
- An earlier release showed 37% for "continued boom". That was a two-year weight labelled as a 2030 outcome; it is not supported on the four-year window.

## Equity loss to banking crisis

Regularised logit on 1,924 country-years (16 economies, 1870–2016 origins): worst four-year drawdown, preceding run-up, loans/GDP, five-year credit growth, public debt/GDP and the short rate. It beats the base rate on held-out countries but not on held-out eras, so the systemic share of the severe tail is uncertain. Credit inputs for the current US state use the latest JST vintage.

## Connected simulator and hysteresis

Per scenario, 4,000 paths update one financial state within every year (revenue expectations, coverage, funding, margin calls, forced sales, liquidity, Treasury-sale pressure, China outflows, LGFV refinancing). Macro paths follow: output gap, a permanent hysteresis stock fed by credit impairment, cancelled investment and displaced labour (US) or debt-deflation, balance-sheet stress and lost external funding (China), and unemployment.

Calibration: one cyclical scale, one hysteresis scale and one catch-up rate for the US are fitted so scenario medians match JST output shortfalls by equity-drawdown class, the GFC/Fed peak-to-trough benchmark and the post-war finding that most of a five-year banking-crisis shortfall remains at ten years. Parameter uncertainty (lognormal, sd 0.4) widens the bands. The systemic branch gives US output -10.9% against trend in 2030 (p10 -16.5%); history for 35%+ equity falls with a banking crisis: median -8.8%, p10 -19.1%. China is anchored to Japan after 1989 (one analogue) and to the same crisis class.

## Main limitations

1. National-index run-ups are analogues for a concentrated AI basket.
2. Global crash clusters are scarce: 301 episodes contain about 10 independent severe clusters.
3. Annual closes understate intra-year troughs.
4. China and cross-border elasticities, the liquidity-vacuum split and regime multipliers are structural assumptions, not identified causal estimates.
5. Hyperscaler stress needs a combined revenue, commitment and funding shock; the largest firms are cash-generative today.
6. Treasury holdings indicate sale capacity, not intent.
7. The 47.4% broad technology proxy is not an estimate that the whole sector is a bubble.
8. China debt perimeters overlap and cannot be summed.
9. European relative gains arrive after the acute hit and need policy execution.

As-of date: 31 October 2026, Europe/Zurich.
