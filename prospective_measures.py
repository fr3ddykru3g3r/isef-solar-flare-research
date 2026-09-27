"""PROSPECTIVE PRE-REGISTRATION (decisions.md 2026-09-27, 2f62f88; clarification bb8a137): bursty fraction BF and late-window
restlessness CV6. Step 1 = dev 2010-2019, LABEL-BLIND compute from files on disk (data/euv_full); no downloads (the aiapy pointing
table is a JSOC keyword query, allowed). Frame loop = euv_spatial.spatial_episode / euv_masks.mask_episode (same files, SAT_DN,
update_pointing, register_cutout, hmi_to_frame): per-pixel stack on the alarm-time HMI grid, the same pixels and weighting as CV_box.
Usage: python prospective_measures.py selftest | step1_run | step1_report"""
import glob, hashlib, json, os, sys, time, warnings
import numpy as np, pandas as pd

R, OUT = "data/euv_full", "data/prospective"
H = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
warnings.filterwarnings("ignore")


def bf(V, fill):
    """BF from a frames x box-pixels stack (NaN = not finite). -> (BF, kept pixel fraction, undefined rule or '')."""
    if not fill >= 0.80:
        return np.nan, np.nan, "fill"
    keep = np.isfinite(V).sum(0) >= 0.80 * len(V)                  # c) finite in >= 80% of valid frames
    kf = float(keep.mean())
    if kf < 0.80:
        return np.nan, kf, "pixels"
    X = V[:, keep]
    floor, mean = np.nanpercentile(X, 5, axis=0), np.nanmean(X, axis=0)   # d) numpy default (linear) over finite values
    return float(1 - floor.sum() / mean.sum()), kf, ""


def cv6(s, t):
    """CV_box (euv_dctrl.cv) on valid_primary frames with T_REC in (t-6h, t]; fill over the 30 slots t-5h48m..t (valid frame within
    +-6 min, the existing fill rule). -> (CV6, fill6)."""
    from euv_dctrl import cv
    v = s[s.valid_primary & (s.t_rec > t - pd.Timedelta("6h")) & (s.t_rec <= t)]; tv = v.t_obs.to_numpy()
    slots = pd.date_range(t - pd.Timedelta("6h") + pd.Timedelta("12min"), t, freq="12min").to_numpy(); assert len(slots) == 30
    fill = float(np.mean([len(tv) > 0 and np.abs(tv - sl).min() <= np.timedelta64(6, "m") for sl in slots]))
    return (cv(tv, v.box.to_numpy()) if fill >= 0.80 else np.nan), fill


def episode(ep):
    """Per-pixel stack (frame loop copied from euv_spatial.spatial_episode), box-mean check, BF, CV6, full-window CV_box check."""
    import sunpy.map
    from astropy.io import fits
    from astropy.time import Time
    from aiapy.calibrate import update_pointing
    from aiapy.calibrate.utils import get_pointing_table
    from euv_run import register_cutout
    from euv_dctrl import samples, hmi_to_frame, frame_means, cv
    from euv_pilot import SAT_DN
    from euv_full import hmi_files, trec_of
    warnings.filterwarnings("ignore")
    t0 = time.time(); h, t = ep["harpnum"], pd.Timestamp(ep["t"])
    mp, bp = hmi_files(f"{R}/hmi/{h}", ep["t_rec_tai"])
    mag = sunpy.map.Map(mp); bitmap = fits.open(bp)[-1].data
    S, _, _ = samples(mag.data, bitmap)
    ny, nx = mag.data.shape
    s = pd.read_csv(f"{R}/series/{ep['eid']}.csv", parse_dates=["t_obs", "t_rec"], float_precision="round_trip")
    rows = s[s.valid_primary].to_dict("records")
    files = {trec_of(p): p for p in glob.glob(f"{R}/aia/{h}/*.fits")}
    ptab = get_pointing_table("JSOC", time_range=(Time(t - pd.Timedelta("26h")), Time(t + pd.Timedelta("2h"))))
    V = np.full((len(rows), ny * nx), np.nan); box_diff = 0.0
    for i, row in enumerate(rows):
        m = sunpy.map.Map(files[row["t_rec"]])
        exp = m.exposure_time.to_value("s"); raw = m.data.astype(float)
        if exp <= 0:
            raw[:] = np.nan; exp = 1.0
        raw[raw > SAT_DN] = np.nan
        try:
            m = update_pointing(m, pointing_table=ptab)
        except (IndexError, TypeError):                            # as compute_episode (header pointing kept)
            pass
        r = register_cutout(sunpy.map.Map(raw / exp, m.meta))
        idx = hmi_to_frame(mag, r)
        a, b = frame_means(r.data, idx, {"box": S["box"]})["box"], row["box"]
        box_diff = max(box_diff, 0.0 if (np.isnan(a) and np.isnan(b)) else abs(a - b) if np.isfinite(a - b) else np.inf)
        ok = idx >= 0; V[i, ok] = r.data.ravel()[idx[ok]]
    v = s[s.valid_primary]
    cvb = cv(v.t_obs.to_numpy(), v.box.to_numpy())
    B, kf, why = bf(V, ep["primary_fill"]); c6, f6 = cv6(s, t)
    res = dict(eid=ep["eid"], frames=len(rows), npix_box=ny * nx, box_diff=box_diff, cv_box_repro=cvb,
               cv_box_diff=abs(cvb - ep["primary_CV_box"]), BF=B, BF_kept_px_frac=kf, BF_undefined=why, CV6=c6, fill6=f6,
               CV6_undefined="" if np.isfinite(c6) else "fill6", elapsed_s=round(time.time() - t0, 1))
    json.dump(res, open(f"{OUT}/dev/{ep['eid']}.json", "w"))
    return res


def dev_eps():
    """LABEL-BLIND episode list: data/stage3/cohort_dev.csv read with usecols (true_alarm / delayed never read)."""
    c = pd.read_csv("data/stage3/cohort_dev.csv", usecols=["harpnum", "t", "noaa_ars", "score", "n_C"], parse_dates=["t"])
    assert len(c) == 547
    lab = pd.read_csv("data/labelled_20100501_20250101.csv", usecols=["harpnum", "t_rec_utc", "t_rec_tai"], parse_dates=["t_rec_utc"], low_memory=False)
    c = c.merge(lab, left_on=["harpnum", "t"], right_on=["harpnum", "t_rec_utc"], how="left", validate="one_to_one").drop(columns="t_rec_utc")
    assert c.t_rec_tai.notna().all()
    c["eid"] = [f"{h}_{t:%Y%m%dT%H%M}" for h, t in zip(c.harpnum, c.t)]
    num = ["primary_fill", "primary_CV_box"]
    r = pd.DataFrame([json.load(open(p)) for p in glob.glob(f"{R}/results/*.json")])
    r = r[r.eid.notna()][["eid"] + num]; r[num] = r[num].apply(pd.to_numeric, errors="coerce")
    c = c.merge(r, on="eid", how="left", validate="one_to_one")
    c["has_series"] = [os.path.exists(f"{R}/series/{e}.csv") for e in c.eid]
    return c


def selftest():
    rng = np.random.RandomState(0)
    const = np.full((120, 50), 7.0)
    burst = const.copy(); burst[rng.rand(120, 50) < 0.1] += 20.0
    b0, b1 = bf(const, 1.0)[0], bf(burst, 1.0)[0]
    assert abs(b0) < 1e-15, b0
    assert b1 > 0, b1
    holes = burst.copy(); holes[:, :15] = np.nan                   # 70% of pixels kept -> undefined; fill 0.79 -> undefined
    assert bf(holes, 1.0)[2] == "pixels" and bf(burst, 0.79)[2] == "fill"
    return b0, b1


if __name__ == "__main__" and sys.argv[1:] == ["selftest"]:
    print("BF self-test (synthetic 120-frame x 50-pixel cubes): constant cube -> BF %.3g; cube with added bursts -> BF %.4f; "
          "undefined rules (pixels kept < 80%%, fill < 80%%) trigger" % selftest())

if __name__ == "__main__" and sys.argv[1:] == ["step1_run"]:
    from concurrent.futures import ProcessPoolExecutor, as_completed
    selftest(); os.makedirs(f"{OUT}/dev", exist_ok=True); os.makedirs(f"{OUT}/logs", exist_ok=True)
    c = dev_eps(); w = os.cpu_count() - 1; log = f"{OUT}/logs/step1_run.log"; t0 = time.time()
    eps = [dict(eid=e.eid, harpnum=int(e.harpnum), t=str(e.t), t_rec_tai=e.t_rec_tai, primary_fill=float(e.primary_fill),
                primary_CV_box=float(e.primary_CV_box)) for e in c[c.has_series].itertuples() if not os.path.exists(f"{OUT}/dev/{e.eid}.json")]
    open(log, "a").write(f"{pd.Timestamp.now():%Y-%m-%d %H:%M} start: {len(eps)} episodes to compute, workers {w}\n")
    with ProcessPoolExecutor(w) as pool:
        futs = [pool.submit(episode, e) for e in eps]
        for i, f in enumerate(as_completed(futs), 1):
            f.result()
            if i % 25 == 0 or i == len(futs):
                open(log, "a").write(f"{pd.Timestamp.now():%H:%M} {i}/{len(futs)}, elapsed {(time.time() - t0) / 3600:.2f} h\n")
    open(log, "a").write(f"done: {len(eps)} episodes in {(time.time() - t0) / 3600:.2f} h, workers {w}\n")

if __name__ == "__main__" and sys.argv[1:] == ["step1_report"]:
    from scipy.stats import spearmanr
    c = dev_eps(); J = pd.DataFrame([json.load(open(p)) for p in glob.glob(f"{OUT}/dev/*.json")])
    assert len(J) == int(c.has_series.sum()) == 546, (len(J), int(c.has_series.sum()))
    # ---- checks first: STOP on any failure (no value is reported)
    fb, fc = J[~(J.box_diff < 1e-9)], J[~(J.cv_box_diff < 1e-9)]
    if len(fb) or len(fc):
        print(f"STOP: per-frame box means not reproduced in {len(fb)} episodes {fb.eid.tolist()}; CV_box not reproduced in {len(fc)} {fc.eid.tolist()}")
        sys.exit(1)
    b0, b1 = selftest()
    d = c.merge(J, on="eid", how="left")
    d["BF_undefined"] = np.where(~d.has_series, "no series", d.BF_undefined.fillna(""))
    d["CV6_undefined"] = np.where(~d.has_series, "no series", d.CV6_undefined.fillna(""))
    wall = pd.to_numeric(open(f"{OUT}/logs/step1_run.log").read().split("done: ")[-1].split(" in ")[1].split(" h")[0])
    print("PROSPECTIVE PRE-REGISTRATION — STEP 1: DEV 2010-2019, LABEL-BLIND (true_alarm and delayed never read). 2f62f88 + bb8a137.")
    print(f"checks: BF self-test: constant cube -> BF {b0:.3g}; cube with added bursts -> BF {b1:.4f}; undefined rules trigger. "
          f"Per-episode (all {len(J)} with stored series): per-frame box means of the per-pixel stack reproduce the stored series "
          f"(max |diff| {J.box_diff.max():.1e}); euv_dctrl.cv on the full 24-h valid_primary frames reproduces stored CV_box "
          f"(max |diff| {J.cv_box_diff.max():.1e})")
    print(f"\nepisodes: {len(d)} (stored series {int(d.has_series.sum())}; without stored series {int((~d.has_series).sum())}: "
          f"{d.loc[~d.has_series, 'eid'].tolist()})")
    for m in ["BF", "CV6"]:
        u = d[f"{m}_undefined"]; x = d[m].dropna()
        print(f"  {m}: defined {int(d[m].notna().sum())}, undefined {int(d[m].isna().sum())} by rule {u[u != ''].value_counts().to_dict()}; "
              f"median {x.median():.4f}, IQR [{x.quantile(.25):.4f}, {x.quantile(.75):.4f}]")
    print(f"  BF kept-pixel fraction (episodes with fill >= 80%): median {d.BF_kept_px_frac.median():.4f}, min {d.BF_kept_px_frac.min():.4f}")
    print("\nSpearman rho (label-free; pairwise complete)")
    for m in ["BF", "CV6"]:
        for v in ["primary_CV_box", "n_C", "score"]:
            k = d[m].notna() & d[v].notna(); r, p = spearmanr(d.loc[k, m], d.loc[k, v])
            print(f"  {m} vs {v:14s}: rho {r:+.4f} (p {p:.2e}, n {int(k.sum())})")
    k = d.BF.notna() & d.CV6.notna(); r, p = spearmanr(d.loc[k, "BF"], d.loc[k, "CV6"])
    print(f"  BF vs CV6           : rho {r:+.4f} (p {p:.2e}, n {int(k.sum())})")
    d[["eid", "harpnum", "t", "has_series", "primary_fill", "primary_CV_box", "frames", "npix_box", "BF", "BF_kept_px_frac", "BF_undefined",
       "CV6", "fill6", "CV6_undefined", "box_diff", "cv_box_diff"]].to_csv(f"{OUT}/dev_values.csv", index=False)
    print(f"\nsaved {OUT}/dev_values.csv sha256 {H(f'{OUT}/dev_values.csv')}")
    print(f"wall (compute) {wall:.2f} h, workers {os.cpu_count() - 1}")
