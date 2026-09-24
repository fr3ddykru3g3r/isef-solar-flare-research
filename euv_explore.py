"""EXPLORATORY DIAGNOSTIC on step 6 dCV -- NOT PRE-REGISTERED (decisions.md 2026-09-24). Dev 2010-2019, primary version,
the 540 episodes of the step 6 PRIMARY set. No model fitting."""
import numpy as np, pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score
import swpc

OUT = "data/euv_full/step6"
pd.set_option("display.width", 250)
c = pd.read_csv("data/stage4/oof_cohort_dev.csv", parse_dates=["t"])
c["eid"] = [f"{h}_{t:%Y%m%dT%H%M}" for h, t in zip(c.harpnum, c.t)]
d = pd.read_csv(f"{OUT}/oof_PRIMARY.csv")[["eid", "weight", "dCV"]].merge(c.drop(columns="weight"), on="eid", how="left")  # step 6 weights
assert len(d) == 540 and d.dCV.notna().all()
d["hist"] = d.n_C + d.n_M + d.n_X
print("EXPLORATORY DIAGNOSTIC (not pre-registered); dev 2010-2019, primary version, n =", len(d))

# 1. overlap with flare history / gate score
T1 = pd.DataFrame([dict(variable=v, n=len(d), rho=spearmanr(d.dCV, d[v])[0], p=spearmanr(d.dCV, d[v])[1])
                   for v in ["n_C", "n_M", "n_X", "hist", "score"]]).replace({"hist": "n_C+n_M+n_X"})
T1.to_csv(f"{OUT}/explore_1_spearman.csv", index=False)
print("\n1. Spearman rho of dCV with flare history and gate score (unweighted)"); print(T1.to_string(index=False, formatters={"rho": "{:.4f}".format, "p": "{:.2e}".format}))

# 2. timing (true episodes): hours from t to the first M1+ of the region in (t, t+24h]
fl, _ = swpc.load(d.t.min() - pd.Timedelta("1D"), d.t.max() + pd.Timedelta("2D"))
m1 = fl[fl.flux >= 1e-5].dropna(subset=["noaa_ar"]).copy(); m1["noaa_ar"] = m1.noaa_ar.astype(int)
tr = d[d.true_alarm == 1].copy()


def lead(e):
    ars = {int(x) for x in str(e.noaa_ars).split(",") if x.strip().isdigit()}
    f = m1[m1.noaa_ar.isin(ars) & (m1.start > e.t) & (m1.start <= e.t + pd.Timedelta("24h"))]
    return (f.start.min() - e.t).total_seconds() / 3600 if len(f) else np.nan


tr["lead_h"] = [lead(e) for e in tr.itertuples()]
tr[["eid", "harpnum", "t", "dCV", "lead_h"]].to_csv(f"{OUT}/explore_2_timing.csv", index=False)
k = tr.dropna(subset=["lead_h"]); r, p = spearmanr(k.dCV, k.lead_h)
a, b = k[k.lead_h <= 6], k[k.lead_h > 6]
print(f"\n2. true episodes {len(tr)}; with a region M1+ start in (t, t+24h]: {len(k)}")
print(f"   Spearman rho(dCV, hours to flare start) = {r:.4f} (p {p:.4f}, n {len(k)})")
print(f"   lead (0, 6] h:  n {len(a)}, median dCV {a.dCV.median():.4f}; lead (6, 24] h: n {len(b)}, median dCV {b.dCV.median():.4f}")

# 3. dCV alone as a score; HARP bootstrap 2,000, seed 0
grp = np.where(d.true_alarm == 1, "true", np.where(d.delayed == 1, "delayed", "other false"))
rows = []
for name, keep, pos in [("(true + delayed) vs other false", np.ones(len(d), bool), grp != "other false"),
                        ("true vs other false", grp != "delayed", grp == "true")]:
    s = d[keep]; y = pos[keep].astype(int); w, x, h = s.weight.to_numpy(), s.dCV.to_numpy(), s.harpnum.to_numpy()
    harps = np.unique(h); idx = {q: np.where(h == q)[0] for q in harps}
    rng, bs, skip = np.random.RandomState(0), [], 0
    for _ in range(2000):
        ix = np.concatenate([idx[q] for q in rng.choice(harps, len(harps), replace=True)])
        if 0 < y[ix].sum() < len(ix):
            bs.append(roc_auc_score(y[ix], x[ix], sample_weight=w[ix]))
        else:
            skip += 1
    rows.append(dict(comparison=name, episodes=len(s), positive=int(y.sum()), negative=int((y == 0).sum()), HARPs=len(harps),
                     weighted_AUC=roc_auc_score(y, x, sample_weight=w), CI_lo=np.percentile(bs, 2.5), CI_hi=np.percentile(bs, 97.5),
                     skipped_resamples=skip))
T3 = pd.DataFrame(rows); T3.to_csv(f"{OUT}/explore_3_auc.csv", index=False)
print("\n3. weighted AUC of dCV alone (weights 1/n per HARP over the 540); HARP bootstrap 2,000, seed 0")
print(T3.to_string(index=False, float_format=lambda v: f"{v:.4f}"))

# 4. skew
v = d.dCV.to_numpy(); sd, mu = v.std(ddof=1), v.mean()
q = dict(zip(["min", "p1", "p5", "p50", "p95", "p99", "max"], [v.min(), *np.percentile(v, [1, 5, 50, 95, 99]), v.max()]))
T4 = pd.DataFrame([dict(n=len(v), mean=mu, SD=sd, **q, n_abs_gt_3SD=int((np.abs(v) > 3 * sd).sum()),
                        n_abs_dev_from_mean_gt_3SD=int((np.abs(v - mu) > 3 * sd).sum()))])
T4.to_csv(f"{OUT}/explore_4_skew.csv", index=False)
print("\n4. dCV distribution (primary, 540)"); print(T4.T.to_string(header=False, float_format=lambda v: f"{v:.4f}"))
