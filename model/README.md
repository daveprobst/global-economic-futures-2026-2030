# Reproducible model source

`direct_release.py` builds the seven scenario weights, nonlinear macro paths, historical crash comparison and joint US–China path simulation. `systemic_transition.py` builds and validates the equity-loss-to-banking-crisis transition model.

The transition audit embedded in `site/data/scenario_tree.json` records sample size, features and leave-country-out scores. The connected simulation output, path classifications and generated reverse-stress grid are in `site/data/connected_system.json`; the historical aggregate real-GDP observations are in `site/data/historical_validation.json`.

The full research workspace contains the licensed/open raw series. These two files are published so that the transformations, thresholds and structural coefficients are inspectable in the same commit as the site.
