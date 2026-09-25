"""EXPLORATORY (decisions.md 2026-09-25): Deshmukh-style operating point on dev OOF predictions, A vs A+R4a and A vs A+R4a_nf,
the 528 episodes of the R4a flare check. Dev only; no claims. tau chosen in-sample (>= 88% weighted true kept)."""
import glob, json
import numpy as np, pandas as pd
from euv_spatial import cv_fit
from stage4_models import wlogloss, A_COLS

R = "data/euv_full"
coh = pd.read_csv("data/stage4/oof_cohort_dev.csv", parse_dates=["t"])
coh["eid"] = [f"{h}_{t:%Y%m%dT%H%M}" for h, t in zip(coh.harpnum, coh.t)]
res = pd.DataFrame([json.load(open(p)) for p in glob.glob(f"{R}/results/*.json")])[["eid", "sens_fill"]]
res["sens_fill"] = pd.to_numeric(res.sens_fill, errors="coerce")
sp = pd.DataFrame([json.load(open(p)) for p in glob.glob(f"{R}/spatial/*.json")])[["eid", "R4a"]]
nf = pd.DataFrame([json.load(open(p)) for p in glob.glob(f"{R}/spatial_nf/*.json")])[["eid", "R4a"]].rename(columns={"R4a": "R4a_nf"})
coh = coh.merge(res, on="eid", how="left").merge(sp, on="eid", how="left").merge(nf, on="eid", how="left")
c = coh[(coh.sens_fill >= 0.80) & coh.R4a_nf.notna()].reset_index(drop=True).copy()
c["weight"] = 1 / c.groupby("harpnum").harpnum.transform("size")
assert len(c) == 528
P = {"A": cv_fit(c, A_COLS), "A+R4a": cv_fit(c, A_COLS + ["R4a"]), "A+R4a_nf": cv_fit(c, A_COLS + ["R4a_nf"])}
y, w, h = c.true_alarm.to_numpy(), c.weight.to_numpy(), c.harpnum.to_numpy()
ev = pd.read_csv(f"{R}/spatial_nf/eval_nf_compare.csv")                        # check: same OOF predictions as nf_eval
for i, m in enumerate(["A+R4a", "A+R4a_nf"]):
    assert abs(wlogloss(y, P["A"], w) - ev.logloss_A[i]) < 1e-12 and abs(wlogloss(y, P[m], w) - ev.logloss_A_plus[i]) < 1e-12
print(f"check: OOF log-losses equal the R4a flare-check evaluation (n {len(c)}: {int(y.sum())} true / {int((y == 0).sum())} false)")


def tau_keep(p, keep=0.88):                                                   # = diag_operating_point.tau_keep
    t = pd.DataFrame(dict(p=p[y == 1], w=w[y == 1])).sort_values("p", ascending=False)
    cum = t.w.cumsum() / t.w.sum()
    return float(t.p.iloc[int(np.argmax(cum.to_numpy() >= keep))])


def stats(yy, ww, k):
    tk, fr = (ww * yy * k).sum() / (ww * yy).sum(), (ww * (1 - yy) * ~k).sum() / (ww * (1 - yy)).sum()
    prec = (ww * yy * k).sum() / (ww * k).sum() if k.any() else np.nan
    return dict(true_kept=tk, false_removed=fr, precision=prec, FAR=1 - prec)


tau = {m: tau_keep(p) for m, p in P.items()}; kept = {m: P[m] >= tau[m] for m in P}
keys = np.unique(h); grp = {x: np.where(h == x)[0] for x in keys}
rng, B = np.random.RandomState(0), {m: [] for m in P}
for _ in range(2000):
    ix = np.concatenate([grp[x] for x in rng.choice(keys, len(keys), replace=True)])
    for m in P:
        B[m].append(stats(y[ix], w[ix], kept[m][ix]))
B = {m: pd.DataFrame(v) for m, v in B.items()}
rows = []
for m in P:
    s = stats(y, w, kept[m]); ci = {k: np.nanpercentile(B[m][k], [2.5, 97.5]) for k in s}
    rows.append(dict(model=m, tau=tau[m], kept=int(kept[m].sum()),
                     true_kept_n=f"{int((kept[m] & (y == 1)).sum())}/{int(y.sum())}",
                     false_removed_n=f"{int((~kept[m] & (y == 0)).sum())}/{int((y == 0).sum())}",
                     **{f"{k}": s[k] for k in s}, **{f"{k}_CI": f"[{ci[k][0]:.4f}, {ci[k][1]:.4f}]" for k in s}))
T = pd.DataFrame(rows); T.to_csv(f"{R}/spatial_nf/oppoint_dev.csv", index=False)
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
print("\nDev OOF operating point (tau in-sample, >= 88% weighted true kept); weighted fractions; HARP bootstrap 2,000, seed 0")
print(T.to_string(index=False, float_format=lambda v: f"{v:.4f}"))
print("\nDifference in false removed vs A (paired, same resamples)")
for m in ["A+R4a", "A+R4a_nf"]:
    d = stats(y, w, kept[m])["false_removed"] - stats(y, w, kept["A"])["false_removed"]
    db = B[m].false_removed - B["A"].false_removed; lo, hi = np.nanpercentile(db, [2.5, 97.5])
    dn = int((~kept[m] & (y == 0)).sum()) - int((~kept["A"] & (y == 0)).sum())
    print(f"  {m} - A: weighted {d:+.4f} [{lo:+.4f}, {hi:+.4f}]; count {dn:+d}")
