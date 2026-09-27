"""2025-26 RE-TEST: CV_box as a filter on top of model C (decisions.md 2026-09-27, 25fcd66). Frozen euv_extra models only.
checks: label-blind Step 1 (a-d). run: only after the user's "run the 2025-26 filter re-test once".
Usage: python euv_confirm_retest.py checks | run"""
import glob, hashlib, json, sys, time, warnings
import numpy as np, pandas as pd, joblib
from euv_confirm_tests import log_r

T, X = "data/euv_confirm", "data/euv_extra"
NAMES = ["A", "A_CV", "C", "C_CV"]
H = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
warnings.filterwarnings("ignore")
LABEL_FREE = ["harpnum", "t", "score", "n_C", "n_M", "n_X", "noaa_ars"]


def load_models():
    hs = json.load(open(f"{X}/model_hashes.json"))
    bad = [f for f, v in hs.items() if H(f) != v]
    assert not bad, f"hash mismatch: {bad}"
    assert H(f"{X}/thresholds.json") == "7a34507c20d37756906e4ad6dfaf9069c48ad74bff5b42521a4dd4f1c573c6ad"
    TH = json.load(open(f"{X}/thresholds.json"))
    M = {m: [(d["scaler"], d["model"], d["cols"]) for d in (joblib.load(f"{X}/models/{m}_fold{k}.joblib") for k in range(5))] for m in NAMES}
    return hs, TH, M


def evaluable(cols):
    c = pd.read_csv(f"{T}/cohort_le2.csv", usecols=cols, parse_dates=["t"])
    c["eid"] = [f"{h}_{t:%Y%m%dT%H%M}" for h, t in zip(c.harpnum, c.t)]
    r = pd.DataFrame([json.load(open(p)) for p in glob.glob(f"{T}/results/*.json")])[["eid", "primary_fill", "primary_CV_box"]]
    r[["primary_fill", "primary_CV_box"]] = r[["primary_fill", "primary_CV_box"]].apply(pd.to_numeric, errors="coerce")
    c = c.merge(r, on="eid", how="left")
    c["logR"] = log_r(c, pd.Timestamp("2024-12-29"), pd.Timestamp("2026-08-18 23:59"))      # TEST 2: all 387 le2 episodes, same window
    t1 = c[(c.primary_fill >= 0.80) & c.primary_CV_box.notna()]                                 # TEST 1 evaluable rule (ae1b174)
    e = c[(c.primary_fill >= 0.80) & np.isfinite(c.primary_CV_box) & (c.primary_CV_box > 0)].reset_index(drop=True)
    e["log10_CV_box"] = np.log10(e.primary_CV_box)
    e["weight"] = 1 / e.groupby("harpnum").harpnum.transform("size")
    return c, t1, e


pred = lambda ms, c: np.mean([m.predict_proba(sc.transform(c[cols]))[:, 1] for sc, m, cols in ms], axis=0)

if __name__ == "__main__" and sys.argv[1:] == ["checks"]:
    hs, TH, M = load_models()
    c, t1, e = evaluable(LABEL_FREE)                             # no true_alarm / delayed column is read
    print("STEP 1 — LABEL-BLIND CHECKS (true_alarm and delayed not read; no outcome printed)")
    miss = sorted(set(t1.eid) ^ set(e.eid))
    print(f"a) evaluable set: {len(e)} episodes, {e.harpnum.nunique()} HARPs; TEST 1 evaluable set: {len(t1)} episodes, {t1.harpnum.nunique()} HARPs; "
          f"mismatch: {len(miss)} {miss}" + (" (reason: CV_box <= 0 or non-finite)" if miss else ""))
    need = sorted({col for m in NAMES for _, _, cols in M[m] for col in cols})
    na = {col: int(e[col].isna().sum()) if col in e else "MISSING COLUMN" for col in need}
    c2 = c.copy(); c2["logR2"] = log_r(c2, pd.Timestamp("2024-12-29"), pd.Timestamp("2026-08-18 23:59"))
    cons = bool(((c.logR < np.log1p(48)) == ((c.n_C + c.n_M + c.n_X) >= 1)).all())
    print(f"b) model input columns {need}: missing values {na}; R: euv_confirm_tests.log_r, the function TEST 2 used, on all 387 le2 "
          f"episodes with TEST 2's event window 2024-12-29 -> 2026-08-18 23:59 (C1+ = K2 flux >= 1e-6, start in (t-48h, t), cap 48); "
          f"repeat identical {bool(np.array_equal(c.logR, c2.logR2))}; (R < 48) <=> (n_C+n_M+n_X >= 1) for all 387: {cons}")
    print(f"c) hash checks: {len(hs)} files in model_hashes.json match; thresholds.json matches 7a34507c...; frozen tau "
          + ", ".join(f"{m} {TH[m]['tau']:.6f}" for m in NAMES))
    w = e.weight.to_numpy(); keep = {}
    for m in NAMES:
        k = pred(M[m], e) >= TH[m]["tau"]; keep[m] = (float((w * k).sum() / w.sum()), int(k.sum()))
    print("d) BASELINE GUARD — weighted % of ALL evaluable episodes with p >= tau (label-blind): "
          + "; ".join(f"{m} {100 * keep[m][0]:.2f}% ({keep[m][1]}/{len(e)})" for m in NAMES))
    guard = keep["C"][0] > 0.95
    print(f"   C keeps > 95% of all episodes: {guard} -> " + ("BASELINE THRESHOLD DOES NOT FILTER — TEST NOT RUN" if guard else "guard passed"))
    json.dump(dict(n=len(e), harps=int(e.harpnum.nunique()), keep={m: keep[m][0] for m in NAMES}, guard_fail=guard),
              open(f"{T}/retest_checks.json", "w"), indent=1)
