"""POST-HOC RE-ANALYSIS (decisions.md 2026-09-27, 68e57b1) — NOT an untouched test. A vs A+R4a vs COMBO = A + n_B + R4a
(Phase F F3 candidate; definitions exactly as F3), dev 541 fold models, frozen dev tau (>= 88% weighted true kept), applied to
two already-analysed sets (never pooled). Usage: python nb_r4a_reanalysis.py freeze | checks"""
import glob, hashlib, inspect, json, os, sys, time, warnings
import numpy as np, pandas as pd
import joblib, swpc
import phase_f, euv_spatial
from sklearn.metrics import roc_auc_score
from phase_f import load_base, prep, tau_keep, op_stats, wlogloss, A_COLS, DEV_END
from euv_heldout import fit_folds, predict

warnings.filterwarnings("ignore")
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
ROOT = "data/nb_r4a"
MODELS = {"A": A_COLS, "A_R4a": A_COLS + ["R4a"], "COMBO": A_COLS + ["n_B", "R4a"]}
F3_ROW = {"A_R4a": "R4a", "COMBO": "n_B + R4a"}
H = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
fmt = lambda v: f"{v:.4f}"


def n_b(coh, lo, hi):
    """= phase_f.item_F3 history join, line for line: joinable SWPC events (swpc.fetch; K2 true scale), regions in noaa_ars,
    start in [t-48h, t), deduplicated; class counts B/C/M/X. Returns (n_B, join reproduces n_C/n_M/n_X for every episode)."""
    fl, _ = swpc.fetch(pd.Timestamp(lo), pd.Timestamp(hi), verbose=False)
    by_ar = {k: v[["start", "cls"]].sort_values("start") for k, v in fl.groupby("noaa_ar")}
    cnt = []
    for e in coh.itertuples():
        prev = [g[(g.start >= e.t - pd.Timedelta(hours=48)) & (g.start < e.t)] for ar in
                [int(a) for a in str(e.noaa_ars).split(",") if a.strip().isdigit()] if (g := by_ar.get(ar)) is not None]
        p = pd.concat(prev).drop_duplicates() if prev else pd.DataFrame(columns=["start", "cls"])
        cnt.append({k: int((p.cls == k).sum()) for k in "BCMX"})
    cnt = pd.DataFrame(cnt)
    return cnt.B.to_numpy(), all((cnt[k].to_numpy() == coh[f"n_{k}"].to_numpy()).all() for k in "CMX")


def load_frozen():
    hs = json.load(open(f"{ROOT}/model_hashes.json"))
    assert all(H(f) == h for f, h in hs.items()), "frozen n_B + R4a files changed"
    TH = json.load(open(f"{ROOT}/thresholds.json"))
    M = {n: [(lambda d: (d["scaler"], d["model"], d["cols"]))(joblib.load(f"{ROOT}/models/{n}_fold{k}.joblib")) for k in range(5)] for n in MODELS}
    return hs, TH, M


def test_sets():
    """LABEL-BLIND: true_alarm / delayed are never read (usecols). PRIMARY = euv_heldout R4a primary set; SECONDARY = TEST 1 s3 set."""
    cols = ["harpnum", "t", "score", "n_C", "n_M", "n_X", "noaa_ars"]
    js = lambda d, k: pd.DataFrame([json.load(open(p)) for p in glob.glob(f"{d}/*.json")])[["eid"] + k]
    out, und = {}, {}
    for name, coh, n0, root, extra, lo, hi in [
            ("PRIMARY 2021/23/24 single-region", "data/stage5/cohort_test_primary.csv", 313, "data/euv_test", [], "2020-12-29", "2025-01-01 23:59"),
            ("SECONDARY 2025-26 <=2-region", "data/euv_confirm/cohort_le2.csv", 387, "data/euv_confirm", ["primary_CV_box"], "2024-12-29", "2026-08-18 23:59")]:
        c = pd.read_csv(coh, usecols=cols, parse_dates=["t"]); assert len(c) == n0
        c["eid"] = [f"{h}_{t:%Y%m%dT%H%M}" for h, t in zip(c.harpnum, c.t)]
        r = js(f"{root}/results", ["primary_fill"] + extra); r[r.columns[1:]] = r[r.columns[1:]].apply(pd.to_numeric, errors="coerce")
        c = c.merge(r, on="eid", how="left").merge(js(f"{root}/spatial", ["R4a"]), on="eid", how="left")
        base = (c.primary_fill >= 0.80) & (c.primary_CV_box.notna() if extra else True)
        und[name] = c.loc[base & c.R4a.isna(), "eid"].tolist()
        c = c[base & c.R4a.notna()].reset_index(drop=True)
        c["weight"] = 1 / c.groupby("harpnum").harpnum.transform("size")
        c["n_B"], ok = n_b(c, lo, hi); assert ok, f"{name}: join does not reproduce n_C, n_M, n_X"
        out[name] = c
    return out, und


if __name__ == "__main__" and sys.argv[1:] == ["freeze"]:
    t00 = time.time()
    print("POST-HOC RE-ANALYSIS (68e57b1) — NOT an untouched test. FREEZE: dev only; no test set is read in this step.")
    src = inspect.getsource(phase_f.item_F3).splitlines()
    i0 = next(i for i, l in enumerate(src) if "fl, _ = swpc.fetch" in l); i1 = next(i for i, l in enumerate(src) if "coh = coh.assign(n_B" in l)
    print("\nDEFINITIONS (quoted; no changes)")
    print("n_B — phase_f.item_F3 (B = K2 true flux in [1e-7, 1e-6), swpc.class_of; joinable events only; no transform):")
    print("\n".join("    " + l for l in src[i0:i1 + 1]))
    print("R4a — euv_spatial.spatial_episode (median over consecutive valid_primary frame pairs <= 24 min apart of the excess kurtosis "
          "of the whole-box running difference; no transform):")
    ks = inspect.getsource(euv_spatial._kurt_skew).splitlines(); sp = inspect.getsource(euv_spatial.spatial_episode).splitlines()
    print("\n".join("    " + l for l in ks + [l for l in sp if "d = V[i] - V[i - 1]" in l or 'p["kappa_box"]' in l or "med = lambda" in l
                                                  or "R4a=med" in l]))
    print(f"models: {', '.join(f'{k} = {v}' for k, v in MODELS.items())}; euv_heldout.fit_folds (= euv_spatial.cv_fit, Step 6 settings: "
          "Stage 4 folds, 1/n per HARP weights, training-fold StandardScaler, LogisticRegression L2 C=1 lbfgs); new-set prediction = mean of 5 fold models; "
          "tau = phase_f.tau_keep (highest dev OOF threshold keeping >= 88% weighted true, as 04b6f4f)")
    dv = load_base()
    nb, ok = n_b(dv, "2010-04-28", DEV_END); assert ok, "dev join does not reproduce n_C, n_M, n_X"
    f3n = pd.read_csv("data/phase_f/F3_n_B.csv"); dv["n_B"] = nb
    assert (dv.set_index("eid").n_B.loc[f3n.eid].to_numpy() == f3n.n_B.to_numpy()).all(), "n_B does not reproduce F3_n_B.csv"
    c = prep(dv, dv.P & dv.R4a.notna()); assert len(c) == 541
    y, w = c.true_alarm.to_numpy(), c.weight.to_numpy()
    f3 = pd.read_csv("data/phase_f/F3_eval.csv", float_precision="round_trip").set_index("candidate")
    os.makedirs(f"{ROOT}/models", exist_ok=True); out, hashes, P = {}, {}, {}
    for name, cols in MODELS.items():
        ms, p = fit_folds(c, cols); P[name] = p
        tau = tau_keep(p, y, w); k = p >= tau; tk, fr, pr = op_stats(y, w, k)
        out[name] = dict(cols=cols, tau=tau, dev_oof_logloss=wlogloss(y, p, w), dev_oof_AUC=roc_auc_score(y, p, sample_weight=w),
                         dev_oof_true_kept_w=tk, dev_oof_false_removed_w=fr, true_kept_n=f"{int((k & (y == 1)).sum())}/{int(y.sum())}",
                         false_removed_n=f"{int((~k & (y == 0)).sum())}/{int((y == 0).sum())}")
        for f, (sc, mdl, cl) in enumerate(ms):
            fn = f"{ROOT}/models/{name}_fold{f}.joblib"
            assert not os.path.exists(fn), f"{fn} exists; never overwrite"
            joblib.dump({"scaler": sc, "model": mdl, "cols": cl}, fn); hashes[fn] = H(fn)
    # 1a — reproduce dev F3 exactly (delta, AUC, false removed / true kept counts and weighted %, tau)
    rep = []
    for name, row in F3_ROW.items():
        r, o, a = f3.loc[row], out[name], out["A"]
        chk = dict(model=name, F3_row=row, delta=a["dev_oof_logloss"] - o["dev_oof_logloss"], F3_delta=r.delta, AUC=o["dev_oof_AUC"], F3_AUC=r.AUC_Ax,
                   false_removed_n=o["false_removed_n"], F3_false_removed_n=r.false_removed_n_Ax, true_kept_n=o["true_kept_n"],
                   F3_true_kept_n=r.true_kept_n_Ax, false_removed_w=o["dev_oof_false_removed_w"], F3_false_removed_w=r.false_removed_Ax,
                   tau=o["tau"], F3_tau=r.tau_Ax)
        assert abs(chk["delta"] - r.delta) < 1e-12 and abs(chk["AUC"] - r.AUC_Ax) < 1e-12 and abs(chk["false_removed_w"] - r.false_removed_Ax) < 1e-12
        assert chk["false_removed_n"] == r.false_removed_n_Ax and chk["true_kept_n"] == r.true_kept_n_Ax and chk["tau"] == r.tau_Ax
        assert abs(a["dev_oof_AUC"] - r.AUC_A) < 1e-12 and a["false_removed_n"] == r.false_removed_n_A and a["tau"] == r.tau_A
        rep.append(chk)
    c[["eid", "harpnum", "t", "fold", "weight", "n_B", "R4a"]].to_csv(f"{ROOT}/dev_rows.csv", index=False)
    json.dump(out, open(f"{ROOT}/thresholds.json", "w"), indent=1)
    for f in [f"{ROOT}/dev_rows.csv", f"{ROOT}/thresholds.json"]:
        hashes[f] = H(f)
    json.dump(hashes, open(f"{ROOT}/model_hashes.json", "w"), indent=1)
    print(f"\ncheck: the join reproduces n_C, n_M, n_X for all {len(dv)} dev episodes and n_B equals data/phase_f/F3_n_B.csv for all {len(f3n)}")
    print(f"dev set: {len(c)} episodes (primary fill >= 80%, R4a defined), true {int(y.sum())}, false {int((y == 0).sum())}, HARPs {c.harpnum.nunique()}")
    print("\n1a. DEV F3 REPRODUCED EXACTLY (|diff| < 1e-12; counts and tau identical); delta = LL(A) - LL(model), + = helps; OOF, >= 88% weighted true kept")
    print(pd.DataFrame(rep).to_string(index=False, float_format=lambda v: f"{v:.6f}"))
    print("\nFROZEN (dev OOF):")
    for name, o in out.items():
        print(f"  {name:6s} cols {o['cols']}: tau {o['tau']:.10f}; LL {o['dev_oof_logloss']:.4f}, AUC {o['dev_oof_AUC']:.4f}; true kept {o['true_kept_n']} "
              f"({o['dev_oof_true_kept_w']:.4f} w), false removed {o['false_removed_n']} ({o['dev_oof_false_removed_w']:.4f} w)")
    for f, h in hashes.items():
        print(f"  sha256 {h}  {f}")
    print(f"wall {time.time() - t00:.1f} s")

if __name__ == "__main__" and sys.argv[1:] == ["checks"]:
    t00 = time.time(); hs, TH, M = load_frozen()
    print("\n" + "=" * 110 + "\nSTEP 1 — LABEL-BLIND CHECKS (true_alarm and delayed not read; no outcome printed)")
    print(f"integrity: {len(hs)} frozen files hash-verified (models, thresholds.json, dev_rows.csv); "
          + ", ".join(f"tau_{k} {v['tau']:.10f}" for k, v in TH.items()))
    S, und = test_sets()
    print("\n1b. EPISODE COUNTS (weights 1/n per HARP within each set); n_B join reproduces the cohort n_C, n_M, n_X for every episode")
    for name, c in S.items():
        print(f"  {name}: {len(c)} episodes, HARPs {c.harpnum.nunique()}; R4a undefined among fill-eligible episodes: {len(und[name])} {und[name]}; "
              f"n_B undefined: {int(c.n_B.isna().sum())}; n_B median {c.n_B.median():.1f}, IQR [{c.n_B.quantile(.25):.1f}, {c.n_B.quantile(.75):.1f}], "
              f"max {c.n_B.max()}, zero {int((c.n_B == 0).sum())}")
    print("\n1c. B-CLASS ATTRIBUTION (phase_f.item_F3 code: swpc.load per calendar year, cls == 'B', fraction with a NOAA region number)")
    cov = []
    for y in list(range(2010, 2020)) + list(range(2021, 2027)):
        fl, _ = swpc.load(pd.Timestamp(f"{y}-01-01"), pd.Timestamp(f"{y}-12-31 23:59")); b = fl[fl.cls == "B"]
        days = sum(os.path.exists(swpc._path(d)) for d in pd.date_range(f"{y}-01-01", f"{y}-12-31"))
        cov.append(dict(year=y, days_cached=days, B_events=len(b), with_region=int(b.noaa_ar.notna().sum()),
                        frac_with_region=b.noaa_ar.notna().mean() if len(b) else np.nan))
    cov = pd.DataFrame(cov); f3c = pd.read_csv("data/phase_f/F3_B_coverage.csv", float_precision="round_trip")
    d = cov[cov.year < 2020].reset_index(drop=True)
    assert (d[["year", "B_events", "with_region"]].to_numpy() == f3c[["year", "B_events", "with_region"]].to_numpy()).all()
    m_year, m_pool = d.frac_with_region.mean(), d.with_region.sum() / d.B_events.sum()
    t_ = cov[cov.year > 2020].copy(); t_["diff_vs_mean_pp"] = 100 * (t_.frac_with_region - m_year); t_["diff_vs_pooled_pp"] = 100 * (t_.frac_with_region - m_pool)
    print(cov.to_string(index=False, float_format=fmt))
    print(f"  dev rows reproduce data/phase_f/F3_B_coverage.csv; dev average: mean of per-year fractions {m_year:.4f}, pooled {m_pool:.4f}")
    print(t_[["year", "frac_with_region", "diff_vs_mean_pp", "diff_vs_pooled_pp"]].to_string(index=False, float_format=lambda v: f"{v:+.2f}" if abs(v) > 1 else f"{v:.4f}"))
    bad = t_[(t_.diff_vs_mean_pp.abs() > 20) | (t_.diff_vs_pooled_pp.abs() > 20)]
    print(f"  rule (> 20 pp vs either dev average in any test year): {'n_B NOT COMPARABLE ACROSS YEARS — TEST NOT RUN ' + str(bad.year.tolist()) if len(bad) else 'no test year exceeds 20 pp'}")
    print("\n1d. BASELINE GUARD: weighted % of ALL episodes with p_A >= tau_A (frozen A; mean of 5 dev fold models)")
    for name, c in S.items():
        pA = predict(M["A"], c); k = pA >= TH["A"]["tau"]; kw = (c.weight * k).sum() / c.weight.sum()
        print(f"  {name}: A keeps {kw:.4f} weighted ({int(k.sum())}/{len(c)} episodes) -> "
              f"{'PRIMARY comparison not interpretable (baseline does not filter); only matched retention reported' if kw > 0.95 else 'baseline filters (<= 95%); PRIMARY comparison stands'}")
    print(f"\nwall {time.time() - t00:.1f} s. STOP — evaluation only on 'run the n_B + R4a re-analysis once'.")
