"""Descriptive (decisions.md 2026-09-23): fraction of hours / regions followed by an M1+ flare within 24 h (K2 SWPC),
alarmed vs non-alarmed, primary test years 2021/2023/2024, single-region. Frozen gate scores (mean of the 5 frozen
fold models, as Stage 5) - no fitting. HARP bootstrap 1,000, seed 20260921 (Stage 5 gate CI scheme)."""
import hashlib, json
import numpy as np, pandas as pd, joblib
SPEC = json.load(open("frozen/frozen_spec.json")); H = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
assert H("frozen/frozen_spec.json").startswith("1d205068") and H(SPEC["data"]["labelled_file"]) == SPEC["data"]["labelled_sha256"]
F, THR = SPEC["gate"]["features"], SPEC["gate"]["threshold"]
split = pd.read_csv("frozen/split.csv")
lab = pd.read_csv(SPEC["data"]["labelled_file"], parse_dates=["t_rec_utc"], low_memory=False)
d = lab[lab.harpnum.isin(split.loc[split.set == "test", "harpnum"]) & lab.t_rec_utc.dt.year.isin([2021, 2023, 2024])
        & (lab.noaa_ar_count == 1)]
d = d[~d[F].isna().any(axis=1)].reset_index(drop=True)
X = d[F].to_numpy(float); dv = np.zeros(len(d))
for v in SPEC["gate"]["fold_models"].values():
    assert H(v["path"]) == v["sha256"]; g = joblib.load(v["path"]); dv += g["model"].decision_function((X - g["median"]) / g["sd"])
d["alarm"] = dv / len(SPEC["gate"]["fold_models"]) >= THR; y = d.flared_M1_next_24h.to_numpy(); a = d.alarm.to_numpy(); h = d.harpnum.to_numpy()
tp, fp = int((a & (y == 1)).sum()), int((a & (y == 0)).sum()); fn, tn = int((~a & (y == 1)).sum()), int((~a & (y == 0)).sum())
tss = tp / (tp + fn) - fp / (fp + tn); far = fp / (tp + fp)
print(f"hour contingency TP {tp} FP {fp} FN {fn} TN {tn}; TSS {tss:.4f} FAR {far:.4f} (Stage 5: 0.5467, 0.7021)")
assert abs(tss - 0.5467) < 5e-5 and abs(far - 0.7021) < 5e-5, "does not reproduce Stage 5"
r = d.groupby("harpnum").agg(y=("flared_M1_next_24h", "max"), a=("alarm", "max")).reset_index()


def rate(yy, aa, alarmed):
    m = aa if alarmed else ~aa
    return yy[m].mean() if m.any() else np.nan


rows = []
for level, (yy, aa, hh) in {"hour": (y, a, h), "region": (r.y.to_numpy(), r.a.to_numpy().astype(bool), r.harpnum.to_numpy())}.items():
    keys = np.unique(hh); grp = {k: np.where(hh == k)[0] for k in keys}; rng = np.random.RandomState(20260921); B = []
    for _ in range(1000):
        ix = np.concatenate([grp[k] for k in rng.choice(keys, len(keys), replace=True)])
        B.append((rate(yy[ix], aa[ix], True), rate(yy[ix], aa[ix], False)))
    B = np.array(B)
    for j, (lab_, alarmed) in enumerate([("(a) alarmed", True), ("(b) non-alarmed", False)]):
        m = aa if alarmed else ~aa; b = B[:, j][np.isfinite(B[:, j])]
        rows.append(dict(level=level, group=lab_, n=int(m.sum()), flare_followed=int(yy[m].sum()), fraction=round(yy[m].mean(), 4),
                         ci_lo=round(np.percentile(b, 2.5), 4), ci_hi=round(np.percentile(b, 97.5), 4), boot_used=len(b)))
    diff = B[:, 0] - B[:, 1]; diff = diff[np.isfinite(diff)]
    rows.append(dict(level=level, group="(a) − (b)", n=np.nan, flare_followed=np.nan,
                     fraction=round(rate(yy, aa, True) - rate(yy, aa, False), 4),
                     ci_lo=round(np.percentile(diff, 2.5), 4), ci_hi=round(np.percentile(diff, 97.5), 4), boot_used=len(diff)))
t = pd.DataFrame(rows); t.to_csv("data/stage5/flare_rate_by_alarm_primary.csv", index=False); print(t.to_string(index=False))
