"""D7 -- closest possible reproduction of Bobra & Couvidat (2015), Table 2 protocol (diagnostic; dev period only).
Built from the RAW chunk files, independent of this project's filters.  Every choice is from the D7 audit table
in decisions.md; NOT STATED items use the most literal reading (listed there as assumptions).
Also D7b: this project's baseline gate restricted to the same period, with a HARP-level bootstrap CI."""
import sys
import numpy as np, pandas as pd
from astropy.time import Time
from joblib import Parallel, delayed
from sklearn.svm import SVC
from sklearn.model_selection import train_test_split
import swpc
from chunks import months

F = ["totusjh", "totpot", "totusjz", "absnjzh", "savncpp", "usflux", "area_acr", "meanpot", "r_value", "shrgt45"]
LO, HI = pd.Timestamp("2010-05-01"), pd.Timestamp("2014-05-31 23:59:59")
SEED, NP, REPEATS = 20260921, 16.5, 1000
SVM = dict(kernel="rbf", C=4.0, gamma=0.075, tol=1e-8, class_weight={1: 2.0, 0: 1.0})

# ---------------------------------------------------------------- raw SHARP rows, B&C filters
parts = []
for a, b in months("2010-05-01", "2014-07-01"):
    tag = f"{a}_{b}".replace("-", "")
    r = pd.read_csv(f"data/raw_sharp_{tag}.csv", dtype={"NOAA_ARS": str, "T_REC": str})
    x = pd.read_csv(f"data/raw_sharp_extra_{tag}.csv", dtype={"T_REC": str})
    parts.append(r.merge(x, on=["HARPNUM", "T_REC"], how="left", validate="one_to_one"))
raw = pd.concat(parts, ignore_index=True).drop_duplicates(["HARPNUM", "T_REC"])   # month-boundary duplicates
raw.columns = [c.lower() for c in raw.columns]
raw["t"] = pd.to_datetime(Time([s.replace("_TAI", "").replace(".", "-", 2).replace("_", " ") for s in raw["t_rec"]],
                               format="iso", scale="tai").utc.isot)
raw["ars"] = raw["noaa_ars"].fillna("").apply(lambda v: frozenset(int(s) for s in v.split(",") if s.strip().isdigit()))
for c in F + ["lon_fwt", "quality"]:
    raw[c] = pd.to_numeric(raw[c], errors="coerce")
n0 = len(raw)
ok = (raw["quality"] <= 65536) & (raw["lon_fwt"].abs() <= 68) & raw[F].notna().all(axis=1) & (raw["ars"].str.len() > 0)
print(f"raw rows 2010-05..2014-06: {n0}; QUALITY<=65536: {int((raw['quality'] <= 65536).sum())}; "
      f"+|LON|<=68: {int(((raw['quality'] <= 65536) & (raw['lon_fwt'].abs() <= 68)).sum())}; "
      f"+features present +NOAA mapped: {int(ok.sum())}")
elig = raw[ok & (raw["t"] >= LO) & (raw["t"] <= HI)].copy()

# ---------------------------------------------------------------- flares, OLD (K) scale
swpc.FLARE_SCALE = "K"
fl, _ = swpc.fetch(LO - pd.Timedelta(days=2), HI + pd.Timedelta(days=3), verbose=False)
m1 = fl[fl["flux"] >= 1e-5].copy()
print(f"SWPC M1+ (K scale) with a region, {LO.date()}..{HI.date()}+: {len(m1)}")

# ---------------------------------------------------------------- positives: 24 h before each flare peak
by_harp = {h: g.sort_values("t") for h, g in raw.groupby("harpnum")}
region_harps = {}
for h, g in raw.groupby("harpnum"):
    for ar in set().union(*g["ars"]):
        region_harps.setdefault(ar, []).append(h)
pos, why = [], {"no peak time": 0, "sample time outside period": 0, "region in no patch": 0,
                "no patch record within 30 min of peak-24h passing filters": 0,
                "flare-location proxy: patch |LON|>68 or no record at peak": 0}
for _, f in m1.iterrows():
    if pd.isna(f["peak"]):
        why["no peak time"] += 1; continue
    ts = f["peak"] - pd.Timedelta(hours=24)
    if not (LO <= ts <= HI):
        why["sample time outside period"] += 1; continue
    hs = sorted(region_harps.get(int(f["noaa_ar"]), []))
    if not hs:
        why["region in no patch"] += 1; continue
    got = None
    for h in hs:                                           # first patch (by HARPNUM) with a qualifying record
        g = by_harp[h]
        at_peak = g[((g["t"] - f["peak"]).abs() <= pd.Timedelta(minutes=30))]
        if at_peak.empty or at_peak["lon_fwt"].abs().min() > 68:
            continue
        c = elig[(elig["harpnum"] == h) & ((elig["t"] - ts).abs() <= pd.Timedelta(minutes=30))
                 & elig["ars"].apply(lambda s: int(f["noaa_ar"]) in s)]
        if len(c):
            got = c.index[0]; break
    if got is None:
        g_any = any(not by_harp[h][((by_harp[h]["t"] - f["peak"]).abs() <= pd.Timedelta(minutes=30))].empty
                    and by_harp[h][((by_harp[h]["t"] - f["peak"]).abs() <= pd.Timedelta(minutes=30))]["lon_fwt"].abs().min() <= 68
                    for h in hs)
        why["no patch record within 30 min of peak-24h passing filters" if g_any
            else "flare-location proxy: patch |LON|>68 or no record at peak"] += 1
        continue
    pos.append(got)
P = len(pos)
print(f"positive examples: {P} (one per flare; {len(set(pos))} distinct records)")
for k, v in why.items():
    print(f"  M1+ flares not used -- {k}: {v}")

# ---------------------------------------------------------------- negatives: random, no M1+ within 24 h after
m1_by_ar = {ar: np.sort(g["start"].values) for ar, g in m1.groupby("noaa_ar")}


def flares_next24(row):
    t0, t1 = np.datetime64(row["t"]), np.datetime64(row["t"] + pd.Timedelta(hours=24))
    return any(((v > t0) & (v <= t1)).any() for ar in row["ars"] for v in [m1_by_ar.get(ar, np.array([], "datetime64[ns]"))])


pool = elig.drop(index=pos, errors="ignore")
pool = pool[~pool.apply(flares_next24, axis=1)]
N = int(round(NP * P))
neg = pool.sample(n=N, replace=False, random_state=SEED).index
print(f"negative pool (eligible records, no M1+ in (t, t+24h]): {len(pool)}; drawn once: N = {N} (N/P = {N / P:.2f})")

cat = pd.concat([elig.loc[pos].assign(y=1), elig.loc[neg].assign(y=0)], ignore_index=True)
X = cat[F].to_numpy(float); y = cat["y"].to_numpy()
X = (X - np.median(X, axis=0)) / X.std(axis=0)                 # assumption: scaling on the whole catalogue


def one(i):
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.30, stratify=y, random_state=SEED + i)
    pred = SVC(**SVM).fit(Xtr, ytr).decision_function(Xte) >= 0     # assumption: SVC default boundary
    tpr = (pred & (yte == 1)).sum() / (yte == 1).sum(); fpr = (pred & (yte == 0)).sum() / (yte == 0).sum()
    return tpr - fpr, tpr, fpr


res = np.array(Parallel(n_jobs=3)(delayed(one)(i) for i in range(REPEATS)))
pd.DataFrame(res, columns=["TSS", "TPR", "FPR"]).to_csv("data/diag/d7_repeats.csv", index=False)
print(f"\nD7 over {REPEATS} random 70/30 splits: TSS {res[:, 0].mean():.4f} ± {res[:, 0].std(ddof=1):.4f} "
      f"(min {res[:, 0].min():.4f}, max {res[:, 0].max():.4f}); TPR {res[:, 1].mean():.4f} ± {res[:, 1].std(ddof=1):.4f}; "
      f"FPR {res[:, 2].mean():.4f} ± {res[:, 2].std(ddof=1):.4f}; P {P}, N {N}; test set ~{int(round(0.3 * P))} pos / "
      f"{int(round(0.3 * N))} neg")
print(f"distinct patches among positives: {cat.loc[cat.y == 1, 'harpnum'].nunique()}, among negatives: "
      f"{cat.loc[cat.y == 0, 'harpnum'].nunique()}")

# ---------------------------------------------------------------- D7b: our baseline, same period
import diag_ablation as A
base = A.load("data/labelled_20100501_20250101.csv")
per = base[(base["t_rec_utc"] >= LO) & (base["t_rec_utc"] <= HI)].reset_index(drop=True)
r, s = A.run(per, A.harp_folds(per), A.thin(per), "maxTSS")
yb, hb = per["flared_M1_next_24h"].to_numpy(), per["harpnum"].to_numpy()
harps = np.unique(hb); rows_of = {x: np.where(hb == x)[0] for x in harps}; rng = np.random.RandomState(SEED); vals = []
for _ in range(1000):
    idx = np.concatenate([rows_of[x] for x in rng.choice(harps, len(harps), replace=True)])
    a = s[idx] >= r["threshold"]; yy = yb[idx]
    if yy.sum() and (yy == 0).sum():
        vals.append((a & (yy == 1)).sum() / (yy == 1).sum() - (a & (yy == 0)).sum() / (yy == 0).sum())
lo, hi = np.percentile(vals, [2.5, 97.5])
print(f"\nD7b our baseline, {LO.date()}..{HI.date()}: TSS {r['TSS']:.4f} 95% CI [{lo:.4f}, {hi:.4f}] "
      f"(HARP bootstrap, {len(vals)} resamples); TPR {r['TPR']:.4f}, FPR {r['FPR']:.4f}; rows {r['eval_rows']}, "
      f"positive rows {r['eval_pos']}, positive HARPs {r['pos_HARPs']}, HARPs {len(harps)}; threshold {r['threshold']:.4f}")
