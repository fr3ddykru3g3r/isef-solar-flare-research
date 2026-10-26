"""STEP A (user; dev only; exploratory).  Within the dev cohort: logistic models with (i) gate score only, (ii) C/M/X
history only, (iii) score + history.  Same CV, weights, regularisation as Stage 4 (reuses stage4_models.cv).
Models are not saved (no overwrite of the frozen Stage 4 fold models)."""
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score
import stage4_models as S4

SETS = {"(i) gate score only": ["score"], "(ii) history only (n_C, n_M, n_X)": ["n_C", "n_M", "n_X"],
        "(iii) score + history (= model A)": ["score", "n_C", "n_M", "n_X"]}
rows = []
for cname, c in [("primary (all eligible, region-weighted)", S4.coh),
                 ("first eligible episode per region", S4.coh[S4.coh["first_eligible"]].assign(weight=1.0).reset_index(drop=True))]:
    y, w = c["true_alarm"].to_numpy(), c["weight"].to_numpy()
    for name, cols in SETS.items():
        p, folds = S4.cv(c, cols, "stepA", save=False)
        rows.append({"cohort": cname, "model": name, "episodes": len(c), "true": int(y.sum()),
                     "logloss": S4.wlogloss(y, p, w), "AUC": roc_auc_score(y, p, sample_weight=w),
                     **{f"logloss_f{f}": S4.wlogloss(y[folds == f], p[folds == f], w[folds == f]) for f in range(5)}})
t = pd.DataFrame(rows); t.to_csv("data/stage4/stepA_dev.csv", index=False)
print(t.to_string(index=False, float_format=lambda v: f"{v:.4f}"))
