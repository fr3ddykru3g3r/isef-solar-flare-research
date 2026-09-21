"""DIAGNOSTIC (user): uncertainty for the ablation.  Dev 2010-2019 only; test HARPs never loaded.
  2. baseline and D1-D6 over 20 fold seeds (SEED + 0..19; seed 0 = the Stage 2 folds).  Region-grouped folds for
     all except D5 and D6, which keep the random row split (D6 is D1-D5 together, so it includes D5's split).
     D4/D6 samples are fixed; only the folds vary.
  3. baseline and D6: region-level bootstrap 95% CI on TSS, 1,000 resamples of HARPs, at the seed-0 fold
     assignment and each run's fixed threshold.
  4. D2 vs baseline at seed 0: rows, labels, positive HARPs, alarm episodes (decision T1 episode rule)."""
import numpy as np, pandas as pd
import diag_ablation as A, cohort

SEEDS = [A.SEED + i for i in range(20)]
S = A.S
base = A.load("data/labelled_20100501_20250101.csv")
d2 = A.load(f"{S}/labelled_K.csv")
d3 = A.load("data/diag_K2_lon68/labelled_dev.csv")
d4, _ = A.bc_samples(base.copy(), "K2")
d6, _ = A.bc_samples(A.load("data/diag_K_lon68/labelled_dev.csv").copy(), "K")


def tss_at(y, s, thr):
    a = s >= thr
    return (a & (y == 1)).sum() / (y == 1).sum() - (a & (y == 0)).sum() / (y == 0).sum()


# ---------------------------------------------------------------- 2. seeds
res = {k: [] for k in ["baseline", "D1", "D2", "D3", "D4", "D5", "D6"]}
keep = {}
for sd in SEEDS:
    r, s = A.run(base, A.harp_folds(base, sd), A.thin(base), "maxTSS")
    res["baseline"].append(r["TSS"])
    res["D1"].append(tss_at(base["flared_M1_next_24h"].to_numpy(), s, 0.0))
    r2, s2 = A.run(d2, A.harp_folds(d2, sd), A.thin(d2), "maxTSS"); res["D2"].append(r2["TSS"])
    res["D3"].append(A.run(d3, A.harp_folds(d3, sd), A.thin(d3), "maxTSS")[0]["TSS"])
    res["D4"].append(A.run(d4, A.harp_folds(d4, sd), np.ones(len(d4), bool), "maxTSS")[0]["TSS"])
    res["D5"].append(A.run(base, A.row_folds(len(base), sd), A.thin(base), "maxTSS")[0]["TSS"])
    r6, s6 = A.run(d6, A.row_folds(len(d6), sd), np.ones(len(d6), bool), "zero"); res["D6"].append(r6["TSS"])
    if sd == A.SEED:
        keep = dict(base=(r, s), d2=(r2, s2), d6=(r6, s6))
    print(f"  seed {sd - A.SEED:2d} done", flush=True)
t2 = pd.DataFrame({k: {"seed0 (Stage 2 folds)": v[0], "mean": np.mean(v), "sd": np.std(v, ddof=1),
                       "min": np.min(v), "max": np.max(v)} for k, v in res.items()}).T
t2.index.name = "run"
pd.DataFrame(res).to_csv("data/diag/uncertainty_seeds.csv", index=False)
print("\n2. TSS over 20 fold seeds (pooled out-of-fold, primary subset)")
print(t2.to_string(float_format=lambda v: f"{v:.4f}"))

# ---------------------------------------------------------------- 3. bootstrap
print("\n3. region-level bootstrap, 1,000 resamples of HARPs, seed-0 folds, fixed threshold")
rng = np.random.RandomState(A.SEED)
for name, d, (r, s) in [("baseline", base, keep["base"]), ("D6", d6, keep["d6"])]:
    y, h = d["flared_M1_next_24h"].to_numpy(), d["harpnum"].to_numpy()
    harps = np.unique(h); rows_of = {x: np.where(h == x)[0] for x in harps}
    vals, skipped = [], 0
    for _ in range(1000):
        idx = np.concatenate([rows_of[x] for x in rng.choice(harps, len(harps), replace=True)])
        if y[idx].sum() == 0 or (y[idx] == 0).sum() == 0:
            skipped += 1; continue
        vals.append(tss_at(y[idx], s[idx], r["threshold"]))
    lo, hi = np.percentile(vals, [2.5, 97.5])
    print(f"  {name:8s} TSS {r['TSS']:.4f}  95% CI [{lo:.4f}, {hi:.4f}]  threshold {r['threshold']:.4f}  "
          f"HARPs {len(harps)}  resamples used {len(vals)} (skipped {skipped}: one class absent)")

# ---------------------------------------------------------------- 4. D2 vs baseline
print("\n4. D2 (K labels) vs baseline (K2 labels), seed-0 folds")
(rb, sb), (r2, s2) = keep["base"], keep["d2"]
kb = base["harpnum"].astype(str) + "|" + base["t_rec_tai"]; k2 = d2["harpnum"].astype(str) + "|" + d2["t_rec_tai"]
print(f"  rows: baseline {len(base)}, D2 {len(d2)}; same row keys: {set(kb) == set(k2)}")
m = base[["harpnum", "t_rec_tai", "flared_M1_next_24h"]].merge(d2[["harpnum", "t_rec_tai", "flared_M1_next_24h"]],
                                                               on=["harpnum", "t_rec_tai"], suffixes=("_K2", "_K"))
print(f"  rows whose label differs: {int((m['flared_M1_next_24h_K2'] != m['flared_M1_next_24h_K']).sum())} "
      f"(positive under K2 only: {int(((m.flared_M1_next_24h_K2 == 1) & (m.flared_M1_next_24h_K == 0)).sum())}, "
      f"under K only: {int(((m.flared_M1_next_24h_K2 == 0) & (m.flared_M1_next_24h_K == 1)).sum())})")
pb, p2 = set(base.loc[base.flared_M1_next_24h == 1, "harpnum"]), set(d2.loc[d2.flared_M1_next_24h == 1, "harpnum"])
print(f"  positive HARPs: baseline {len(pb)}, D2 {len(p2)}; in both {len(pb & p2)}, baseline only {len(pb - p2)}, "
      f"D2 only {len(p2 - pb)}")
eb = cohort.episodes(base.assign(score=sb)[["harpnum", "t_rec_utc", "score"]], rb["threshold"])
e2 = cohort.episodes(d2.assign(score=s2)[["harpnum", "t_rec_utc", "score"]], r2["threshold"])
key = lambda e: set(zip(e.harpnum, e.t, e.end))
kb_, k2_ = key(eb), key(e2)
print(f"  alarm episodes (T1 rule, each run's own threshold: baseline {rb['threshold']:.4f}, D2 {r2['threshold']:.4f}):")
print(f"    baseline {len(eb)}, D2 {len(e2)}; identical (same HARP, onset, end) {len(kb_ & k2_)}, "
      f"baseline only {len(kb_ - k2_)}, D2 only {len(k2_ - kb_)}")
print(f"  TSS: baseline {rb['TSS']:.4f}, D2 {r2['TSS']:.4f}")
