"""Shared model constructors: ridge logit core, boosting and forest challengers, and their blend."""
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import equity_panel as EP

SEED = 20261014
def make_gb(): return GradientBoostingClassifier(n_estimators=80, max_depth=2, learning_rate=.035, subsample=.8, random_state=SEED)
def make_rf(): return RandomForestClassifier(n_estimators=500, max_depth=4, min_samples_leaf=5, max_features=.8, class_weight="balanced", random_state=SEED, n_jobs=-1)
BLEND = (.75, .15, .10)   # ridge-logit core, gradient boosting, random forest




def blend_rows(train, test):
    """Blended probability of a 20%+ fall for each test row, fitted exactly like the point estimate."""
    F = list(EP.PREDICTORS)
    sc = StandardScaler().fit(train[F]); lgs = []
    for _, c in EP.MODEL_CONFIGS:
        m = LogisticRegression(C=c, solver="lbfgs", max_iter=3000, random_state=SEED).fit(sc.transform(train[F]), train.band)
        lgs.append(1 - m.predict_proba(sc.transform(test[F]))[:, list(m.classes_).index("none")])
    gb = make_gb().fit(train[F], train.band); rf = make_rf().fit(train[F], train.band)
    bust = lambda m: 1 - m.predict_proba(test[F])[:, list(m.classes_).index("none")]
    parts = (np.mean(lgs, axis=0), bust(gb), bust(rf))
    return BLEND[0] * parts[0] + BLEND[1] * parts[1] + BLEND[2] * parts[2], parts



