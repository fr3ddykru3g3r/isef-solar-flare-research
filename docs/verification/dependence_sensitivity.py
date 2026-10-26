"""POST-HOC sensitivity of the pre-registered 2025-26 twin result (TEST 1) to region reuse.

NOT pre-registered. Written and run by Claude AI in chat on 2026-09-28 after an external review
pointed out that the 50 pairs reuse regions on both sides. Read-only: uses the stored pairs
(data/euv_confirm/twins_le2.csv) and stored CV_box values (data/euv_confirm/results/*.json).
The pre-registered interval resamples true HARPs only (seed 0 reproduces [1.30, 9.49]).
"""
import json, os, numpy as np, pandas as pd
R = os.environ.get("ISEF_REPO") or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
D = os.path.join(R, "data", "euv_confirm")
p = pd.read_csv(f"{D}/twins_le2.csv")
cv = lambda e: float(json.load(open(f"{D}/results/{e}.json"))["primary_CV_box"])
p["cvt"] = p.true_eid.map(cv); p["cvf"] = p.false_eid.map(cv)
p["th"] = p.true_harp.astype(str); p["fh"] = p.false_harp.astype(str)
ratio = lambda a, b: np.median(a) / np.median(b)
print(f"pairs {len(p)}; ratio {ratio(p.cvt, p.cvf):.3f}; true>false {(p.cvt>p.cvf).sum()}/{len(p)}")
print(f"true HARPs {p.th.nunique()}, false HARPs {p.fh.nunique()}")
print("pairs per true HARP:", sorted(p.th.value_counts().tolist(), reverse=True))
print("pairs per false HARP (max):", p.fh.value_counts().max(), "; false HARPs used >1:", (p.fh.value_counts() > 1).sum())
# HARPs appearing on BOTH sides
both = set(p.th) & set(p.fh); print("HARPs on both sides:", len(both))
# region-level direction: per true HARP, share of its pairs where true > twin
g = p.assign(up=p.cvt > p.cvf).groupby("th").up.mean()
print(f"true HARPs with majority of pairs true>twin: {(g>0.5).sum()} of {len(g)}; exactly half: {(g==0.5).sum()}; minority: {(g<0.5).sum()}")
gm = p.assign(lr=np.log(p.cvt/p.cvf)).groupby("th").lr.median()
print(f"true HARPs with median log-ratio > 0: {(gm>0).sum()} of {len(gm)}")
def boot_side(key, B=2000, seed=0):
    rng = np.random.RandomState(seed); ks = p[key].unique(); idx = {k: np.where(p[key]==k)[0] for k in ks}; v = []
    for _ in range(B):
        ii = np.concatenate([idx[k] for k in rng.choice(ks, len(ks))]); v.append(ratio(p.cvt.values[ii], p.cvf.values[ii]))
    return np.percentile(v, [2.5, 97.5])
def pigeonhole(B=2000, seed=0):
    rng = np.random.RandomState(seed); T = p.th.unique(); F = p.fh.unique(); v = []; npairs = []
    for _ in range(B):
        wt = pd.Series(rng.choice(T, len(T))).value_counts(); wf = pd.Series(rng.choice(F, len(F))).value_counts()
        w = (p.th.map(wt).fillna(0) * p.fh.map(wf).fillna(0)).astype(int).values
        if w.sum() == 0: continue
        ii = np.repeat(np.arange(len(p)), w); npairs.append(len(ii)); v.append(ratio(p.cvt.values[ii], p.cvf.values[ii]))
    return np.percentile(v, [2.5, 97.5]), np.mean(np.array(v) <= 1), len(v), np.median(npairs)
for s in (0, 777):
    print(f"seed {s}: by true HARP {np.round(boot_side('th', seed=s),2)}; by false HARP {np.round(boot_side('fh', seed=s),2)}")
    ci, ple1, nb, mp = pigeonhole(seed=s)
    print(f"seed {s}: two-way (true AND false HARPs resampled independently) {np.round(ci,2)}; share of resamples <= 1: {ple1:.3f}; n {nb}; median pairs/resample {mp}")
