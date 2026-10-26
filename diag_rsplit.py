"""EXPLORATORY DIAGNOSTIC "R-split" (decisions.md 2026-09-23). Dev years 2010-05..2017-12 only; refit per split.
Does not touch the 2021-2024 test set, frozen files or FINAL results."""
import numpy as np, pandas as pd
from joblib import Parallel, delayed
from sklearn.svm import SVC
from sklearn.metrics import roc_curve
import swpc

F = ["totusjh", "totpot", "totusjz", "absnjzh", "savncpp", "usflux", "area_acr", "meanpot", "r_value", "shrgt45"]
SVM = dict(kernel="rbf", C=4.0, gamma=0.075, tol=1e-8, class_weight={1: 2.0, 0: 1.0})
SEEDS = list(range(100, 1001, 100))

lab = pd.read_csv("data/labelled_20100501_20250101.csv", parse_dates=["t_rec_utc"], low_memory=False)
split = pd.read_csv("frozen/split.csv")
d = lab[(lab.t_rec_utc < "2018-01-01") & (lab.noaa_ar_count == 1)].copy()
assert not set(d.harpnum) & set(split.loc[split.set == "test", "harpnum"]), "test HARP in dev years"
d = d[~d[F].isna().any(axis=1)].reset_index(drop=True)
d["hr"] = d.t_rec_tai.str[11:13].astype(int)
# R-D label: M1+ (K2 SWPC, region join) starting in (t, t+12h]
fl, _ = swpc.load(pd.Timestamp("2010-04-29"), pd.Timestamp("2018-01-02"))
m1 = fl[fl.flux >= 1e-5].dropna(subset=["noaa_ar"]); by = {int(a): np.sort(g.start.values) for a, g in m1.groupby("noaa_ar")}
t = d.t_rec_utc.to_numpy(); ar = d.noaa_ars.astype(str).str.split(",").str[0].astype(int).to_numpy()
d["y12"] = [int(((by.get(a, np.array([], "datetime64[ns]")) > x) & (by.get(a, np.array([], "datetime64[ns]")) <= x + np.timedelta64(12, "h"))).any())
            for a, x in zip(ar, t)]
d["y24"] = d.flared_M1_next_24h
assert (d.y12 <= d.y24).all(), "12-h label must imply 24-h label"
harps = np.sort(d.harpnum.unique())
print(f"rows {len(d)}, HARPs {len(harps)}, positive rows y24 {int(d.y24.sum())}, y12 {int(d.y12.sum())}")


def cont(y, a):
    tp, fp, fn, tn = (int(x) for x in ((a & (y == 1)).sum(), (a & (y == 0)).sum(), (~a & (y == 1)).sum(), (~a & (y == 0)).sum()))
    P, N = tp + fn, fp + tn; tpr, fpr = tp / P, fp / N
    return dict(P=P, N=N, TP=tp, FP=fp, FN=fn, TN=tn, base_rate=P / (P + N), TPR=tpr, FPR=fpr, TSS=tpr - fpr,
                precision=tp / (tp + fp) if tp + fp else np.nan, FAR=fp / (tp + fp) if tp + fp else np.nan,
                accuracy=(tp + tn) / (P + N), acc_always_no=N / (P + N))


def run(seed, variant):
    p = harps[np.random.RandomState(seed).permutation(len(harps))]
    ntr, nva = int(len(p) * 0.7), int(len(p) * 0.1)
    s_of = {h: "train" for h in p[:ntr]} | {h: "val" for h in p[ntr:ntr + nva]} | {h: "test" for h in p[ntr + nva:]}
    s = d.harpnum.map(s_of).to_numpy()
    lbl = "y12" if variant == "R-D" else "y24"
    ev = d.hr.isin(range(0, 24, 3)).to_numpy() if variant == "R-D" else np.ones(len(d), bool)
    tr = (s == "train") & d.hr.isin([4, 10, 16, 22]).to_numpy()
    X = d[F].to_numpy(float); y = d[lbl].to_numpy()
    med, sd = np.median(X[tr], axis=0), X[tr].std(axis=0)
    m = SVC(**SVM).fit((X[tr] - med) / sd, y[tr])
    va, te = (s == "val") & ev, (s == "test") & ev
    sv = m.decision_function((X[va] - med) / sd)
    fpr, tpr, th = roc_curve(y[va], sv); thr = float(th[int(np.argmax(tpr - fpr))])
    st = m.decision_function((X[te] - med) / sd)
    return dict(variant=variant, seed=seed, train_rows=int(tr.sum()), test_HARPs=int(len(set(d.harpnum[s == "test"]))),
                val_pos=int(y[va].sum()), threshold=thr, **cont(y[te], st >= thr))


res = Parallel(n_jobs=3)(delayed(run)(sd_, v) for v in ["R-D", "R-24"] for sd_ in SEEDS)
r = pd.DataFrame(res); r.to_csv("data/diag/rsplit_per_seed.csv", index=False)
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
cols = ["P", "N", "TP", "FP", "FN", "TN", "base_rate", "TPR", "FPR", "TSS", "precision", "FAR", "accuracy", "acc_always_no"]
print(r[["variant", "seed", "train_rows", "test_HARPs", "val_pos", "threshold"] + cols].round(4).to_string(index=False))
agg = r.groupby("variant")[cols].agg(["mean", "min", "max"]).round(4)
agg.to_csv("data/diag/rsplit_summary.csv"); print("\n" + agg.T.to_string())
