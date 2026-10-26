"""DESCRIPTIVE ONLY (decisions.md 2026-09-26): (a) model C coefficients (dev fit); (b) label-blind CV_box by year 2010-2026."""
import glob, json
import numpy as np, pandas as pd
from euv_confirm_tests import log_r
from euv_heldout import fit_folds
from phase_f import A_COLS

pd.set_option("display.width", 250)
coh = pd.read_csv("data/stage4/oof_cohort_dev.csv", parse_dates=["t"])
coh["logR"] = log_r(coh, pd.Timestamp("2010-04-28"), pd.Timestamp("2019-12-31 23:59"))
mC, _ = fit_folds(coh, A_COLS + ["logR"])
cols = A_COLS + ["logR"]
rows = []
for k, (sc, m, _) in enumerate(mC):
    b = m.coef_[0]
    rows.append(dict(fold=k, **{f"std_{c}": b[i] for i, c in enumerate(cols)}, per_unit_logR=b[-1] / sc.scale_[-1],
                     SD_logR=sc.scale_[-1], intercept=m.intercept_[0]))
C = pd.DataFrame(rows); mean = C.drop(columns="fold").mean()
print("(a) model C = A + log(1+R), dev fold models (StandardScaler per training fold; logistic coefficients)")
print(C.to_string(index=False, float_format=lambda v: f"{v:.4f}"))
print(f"mean over folds: standardized coef of log(1+R) {mean.std_logR:.4f} (odds ratio per 1 SD {np.exp(mean.std_logR):.4f}); "
      f"per unit of log(1+R) {mean.per_unit_logR:.4f} (odds ratio per unit {np.exp(mean.per_unit_logR):.4f}); signs over folds "
      f"{np.sign(C.std_logR).astype(int).tolist()}")
print(f"dev log(1+R): median {coh.logR.median():.3f}; share at the cap (no C1+ in 48 h) {(coh.logR == np.log1p(48)).mean():.3f}")
print("direction (mechanical): coefficient " + ("negative -> shorter time since the last C1+ flare gives a HIGHER predicted probability"
      if mean.std_logR < 0 else "positive -> shorter time since the last C1+ flare gives a LOWER predicted probability"))

print("\n(b) CV_box (primary_CV_box) by calendar year of t — label-blind (no label column read)")
out = []
for src, root, sub in [("dev", "data/euv_full", "single"), ("test", "data/euv_test", "single"), ("confirmation", "data/euv_confirm", "<=2 union")]:
    r = pd.DataFrame([json.load(open(p)) for p in glob.glob(f"{root}/results/*.json")])
    r = r[r.eid.notna()].copy()
    for c in ["primary_CV_box", "primary_fill"]:
        r[c] = pd.to_numeric(r[c], errors="coerce")
    r["year"] = r.eid.str.split("_").str[1].str[:4].astype(int)
    for y, g in r.groupby("year"):
        for lab, x in [("all with value", g.primary_CV_box.dropna()), ("fill >= 80%", g.loc[g.primary_fill >= 0.8, "primary_CV_box"].dropna())]:
            out.append(dict(source=src, subset=sub, year=y, episodes=lab, n=len(x), median=x.median(), Q1=x.quantile(.25), Q3=x.quantile(.75)))
T = pd.DataFrame(out); T.to_csv("data/euv_confirm/cv_box_by_year.csv", index=False)
print(T[T.episodes == "all with value"].drop(columns="episodes").to_string(index=False, float_format=lambda v: f"{v:.4f}"))
print("\nsame, primary fill >= 80% only:")
print(T[T.episodes == "fill >= 80%"].drop(columns="episodes").to_string(index=False, float_format=lambda v: f"{v:.4f}"))

# single-region subset of the confirmation set (like-for-like with dev/test); label-blind
s = pd.read_csv("data/euv_confirm/cohort_single.csv", usecols=["harpnum", "t"], parse_dates=["t"])
s["eid"] = [f"{h}_{t:%Y%m%dT%H%M}" for h, t in zip(s.harpnum, s.t)]
r = pd.DataFrame([json.load(open(p)) for p in glob.glob("data/euv_confirm/results/*.json")])
for c in ["primary_CV_box", "primary_fill"]:
    r[c] = pd.to_numeric(r[c], errors="coerce")
r = r[r.eid.isin(set(s.eid))].copy(); r["year"] = r.eid.str.split("_").str[1].str[:4].astype(int)
print("\nconfirmation, single-region episodes only (label-blind):")
for y, g in r.groupby("year"):
    for lab, x in [("all with value", g.primary_CV_box.dropna()), ("fill >= 80%", g.loc[g.primary_fill >= 0.8, "primary_CV_box"].dropna())]:
        print(f"  {y} {lab:15s} n {len(x):3d} median {x.median():.4f} IQR [{x.quantile(.25):.4f}, {x.quantile(.75):.4f}]")
