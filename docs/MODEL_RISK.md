# Model risk and interpretation

## Intended use

Scenario analysis and stress testing. Not a trading signal, credit decision, regulatory-capital model, or claim that a crisis will occur.

## One window

Every probability covers 15 Oct 2026 – 31 Dec 2030 and is measured on annual closes. Every macro path runs 2026 (baseline year) to 2030. A longer view appears only in the hysteresis section, labelled 2036 with no new shock.

## Where the parameters are documented

The methodology section of the site lists every model and parameter with a status: **Data**, **Fixed rule**, **Estimated**, **Calibrated** or **Assumed**. Assumed entries (regime factors, finance-engine coefficients, channel weights, China-crisis coefficients, copula correlation, bootstrap widths) are judgments, not estimates; challenge them first.

## Historical crash check

- Run-ups of 100%+ (n=71): 18% boom, 4% contained, 77% fall of 20%+.
- The 25 closest to today's state: 8% / 8% / 84%. Model: 18% / 5% / 77%.
- Models were tested with whole global waves held out; the best has Brier skill of a few percent over the base rate and a ranking no better than chance, so the headline is a frequency, not a model output.
- Annual closes miss falls inside the year; in US monthly data they catch only about half of 20% falls, so fall probabilities are conservative.
- An earlier release showed 37% for "continued boom". That was a two-year weight labelled as a 2030 outcome; it is not supported on the four-year window.

## Main limitations

1. National-index run-ups are analogues for a concentrated 8-stock AI basket.
2. About 10 independent global crash clusters sit behind every tail estimate.
3. Annual closes understate intra-year troughs.
4. The equity-loss-to-banking-crisis link beats the base rate on held-out economies but not on held-out eras.
5. Finance-engine coefficients are structural stress parameters; they are not estimated and not in the bootstrap, so ranges understate total uncertainty.
6. China rests on one analogue (Japan after 1989) and cannot be validated against a Chinese crisis.
7. The systemic branch gives US output -8.6% against trend in 2030 (10th percentile -13.1%); history for 35%+ equity falls with a banking crisis has median -8.0% and 10th percentile -16.2%.
8. Treasury holdings indicate sale capacity, not intent; China debt perimeters overlap and cannot be summed; European relative gains need policy execution.

As-of date: 15 October 2026 (latest prices 14 October 2026), Europe/Zurich.
