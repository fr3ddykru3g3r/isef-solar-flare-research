"""Combined EUV test, Phases 2-3 (decisions.md 2026-09-23). No true-vs-false comparison of dCV anywhere.
Usage: python euv_cad.py select | hmi | verify_crop | syn [wl] | cv | cutouts | cv_cut"""
import glob, json, os, socket, sys, tarfile, time, urllib.request
socket.setdefaulttimeout(120)                      # a dead connection (e.g. after sleep) fails and is retried
from concurrent.futures import ThreadPoolExecutor
import numpy as np, pandas as pd, sunpy.map, astropy.units as u, drms
from astropy.io import fits
from scipy.stats import spearmanr
from sunpy.coordinates import propagate_with_solar_surface
import swpc
from euv_dctrl import samples, hmi_to_frame, frame_means, summarise, SYN
from euv_pilot import flare_excluded, SAT_DN
from euv_download import EMAIL

ROOT, MARGIN = "data/euv_cad", 50.0
CADS = [2, 3, 6, 12]
os.makedirs(ROOT, exist_ok=True)
A = f"{ROOT}/alarms.csv"
d_of = lambda e: f"{ROOT}/{int(e.harpnum)}_{pd.Timestamp(e.t):%Y%m%dT%H%M}"


def log(msg):
    print(msg, flush=True)
    with open(f"{ROOT}/run.log", "a") as f:
        f.write(f"{pd.Timestamp.now():%Y-%m-%d %H:%M:%S} {msg}\n")


def alarms():
    return pd.read_csv(A, parse_dates=["t"])


# ---------------------------------------------------------------- selection
def select():
    c = pd.read_csv("data/stage3/cohort_dev.csv", parse_dates=["t"])
    s = pd.concat([c[c.true_alarm == 1].sample(8, random_state=1), c[c.true_alarm == 0].sample(7, random_state=1)])
    s = s.iloc[np.random.RandomState(1).permutation(len(s))].reset_index(drop=True)
    lab = pd.read_csv("data/labelled_20100501_20250101.csv", usecols=["harpnum", "t_rec_utc", "t_rec_tai", "lon_fwt"],
                      parse_dates=["t_rec_utc"], low_memory=False)
    s = s.merge(lab, left_on=["harpnum", "t"], right_on=["harpnum", "t_rec_utc"], how="left", validate="one_to_one")
    s["order"] = range(1, len(s) + 1)
    s[["order", "harpnum", "t", "t_rec_tai", "noaa_ars", "lon_fwt", "true_alarm"]].to_csv(A, index=False)
    log(f"selected {len(s)} alarms -> {A}")


# ---------------------------------------------------------------- JSOC (url-tar)
def jsoc_tar(ds, dest, proc=None):
    """one url-tar export; returns timing dict. Unpacks FITS into dest, deletes the tar."""
    os.makedirs(dest, exist_ok=True)
    c = drms.Client(email=EMAIL); t0 = time.time()
    r = c.export(ds, method="url-tar", protocol="fits", process=proc) if proc else c.export(ds, method="url-tar", protocol="fits")
    if r.status == 7:
        raise RuntimeError(f"JSOC status 7: {r._d.get('error')}")
    while True:
        try:
            r.wait(sleep=20, timeout=6 * 3600); break
        except (TimeoutError, ConnectionError, OSError) as err:
            log(f"wait retry: {err!r}"); time.sleep(60)
    if not r.has_succeeded():
        raise RuntimeError(f"export failed {r.status} {ds}")
    t1 = time.time()
    for k in range(5):
        try:
            r.download(dest, timeout=600); break
        except (TimeoutError, ConnectionError, OSError) as err:
            log(f"tar retry {k + 1}: {err!r}"); time.sleep(30)
    nb = 0
    for tp in glob.glob(f"{dest}/*.tar"):
        nb += os.path.getsize(tp)
        with tarfile.open(tp) as tf:
            for m in tf.getmembers():
                if m.isfile() and m.name.endswith(".fits"):
                    m.name = os.path.basename(m.name); tf.extract(m, dest)
        os.remove(tp)
    return dict(request_id=r.id, prep_s=round(t1 - t0, 1), download_s=round(time.time() - t1, 1), bytes=nb)


def hmi():
    a = alarms()
    ds = ",".join(f"hmi.sharp_720s[{int(e.harpnum)}][{e.t_rec_tai}]{{magnetogram,bitmap}}" for e in a.itertuples())
    tmp = f"{ROOT}/_hmi"
    try:
        info = jsoc_tar(ds, tmp); log(f"HMI: one multi-set export {info}")
    except Exception as err:
        log(f"HMI multi-set export failed ({err!r}); sequential")
        for e in a.itertuples():
            info = jsoc_tar(f"hmi.sharp_720s[{int(e.harpnum)}][{e.t_rec_tai}]{{magnetogram,bitmap}}", tmp); log(f"HMI {e.harpnum} {info}")
    for e in a.itertuples():                       # sort files into each alarm's folder
        d = f"{d_of(e)}/1"; os.makedirs(d, exist_ok=True)
        tag = f".{int(e.harpnum)}.{e.t_rec_tai.replace('.', '').replace(':', '').replace('_TAI', '_TAI')}"
        for f in glob.glob(f"{tmp}/hmi.sharp_720s.{int(e.harpnum)}.*.fits"):
            hd = fits.getheader(f, 1) if len(fits.open(f)) > 1 else fits.getheader(f)
            if str(hd.get("T_REC", "")).startswith(e.t_rec_tai[:19]):
                os.replace(f, f"{d}/{os.path.basename(f)}")
        assert len(glob.glob(f"{d}/*.fits")) == 2, (e.harpnum, glob.glob(f"{d}/*"))
    log("HMI: 2 files in each of the 15 alarm folders")


# ---------------------------------------------------------------- synoptic with crop-on-download
def edge_coords(mag):
    ny, nx = mag.data.shape
    ys = np.r_[np.zeros(nx), np.full(nx, ny - 1), np.arange(ny), np.arange(ny)]
    xs = np.r_[np.arange(nx), np.arange(nx), np.zeros(ny), np.full(ny, nx - 1)]
    return mag.pixel_to_world(xs * u.pix, ys * u.pix)


def crop(full, mag, edges):
    with propagate_with_solar_surface():
        px, py = full.world_to_pixel(edges.transform_to(full.coordinate_frame))
    pad = MARGIN / full.scale[0].to_value("arcsec / pix")
    x0, x1 = np.nanmin(px.value) - pad, np.nanmax(px.value) + pad
    y0, y1 = np.nanmin(py.value) - pad, np.nanmax(py.value) + pad
    fy, fx = full.data.shape
    x0, y0 = max(int(np.floor(x0)), 0), max(int(np.floor(y0)), 0)
    x1, y1 = min(int(np.ceil(x1)), fx - 1), min(int(np.ceil(y1)), fy - 1)
    return full.submap([x0, y0] * u.pix, top_right=[x1, y1] * u.pix)


def syn_slots(t, cad=2):
    return pd.date_range(t - pd.Timedelta("24h") + pd.Timedelta(f"{cad}min"), t, freq=f"{cad}min").round("2min")


def syn(wl=94, workers=12):
    a = alarms(); jobs = []
    for e in a.itertuples():
        d = f"{d_of(e)}/syn{wl}"; os.makedirs(d, exist_ok=True)
        mag = sunpy.map.Map(glob.glob(f"{d_of(e)}/1/*magnetogram*.fits")[0])
        for s in syn_slots(pd.Timestamp(e.t)):
            jobs.append((d, mag, s))
    edges = {}
    st = dict(n=0, err=0, bytes_full=0, bytes_crop=0, t0=time.time())

    def one(j):
        d, mag, s = j
        fn = f"AIA{s:%Y%m%d_%H%M}_{wl:04d}.fits"; out = f"{d}/{fn}"
        if os.path.exists(out):
            return "skip"
        tmp = out + ".full"
        for k in range(5):
            try:
                urllib.request.urlretrieve(f"{SYN}/{s:%Y/%m/%d}/H{s:%H}00/{fn}", tmp); break
            except Exception as err:
                if "404" in str(err):
                    return "404"
                st["err"] += 1; time.sleep(10)
        else:
            return "fail"
        full = sunpy.map.Map(tmp)
        key = id(mag)
        if key not in edges:
            edges[key] = edge_coords(mag)
        cm = crop(full, mag, edges[key])
        cm.save(out + ".tmp.fits", overwrite=True); os.replace(out + ".tmp.fits", out)
        st["bytes_full"] += os.path.getsize(tmp); st["bytes_crop"] += os.path.getsize(out)
        os.remove(tmp)
        return "ok"

    res = {"ok": 0, "skip": 0, "404": 0, "fail": 0}
    todo = [j for j in jobs if not os.path.exists(f"{j[0]}/AIA{j[2]:%Y%m%d_%H%M}_{wl:04d}.fits")]
    log(f"synoptic {wl}: {len(jobs)} slots, {len(todo)} to fetch, {workers} connections")
    i = 0
    while i < len(todo):
        batch = todo[i:i + 500]; e0 = st["err"]; b0 = time.time()
        with ThreadPoolExecutor(workers) as ex:
            for r in ex.map(one, batch):
                res[r] += 1
        i += len(batch); dt = time.time() - b0
        log(f"  {i}/{len(todo)}: {len(batch) / dt:.2f} files/s, errors in batch {st['err'] - e0}, totals {res}")
        if st["err"] > e0 and workers > 6:
            workers = 6; log("  errors -> dropping to 6 connections")
    tot = time.time() - st["t0"]
    n = max(res["ok"], 1)
    log(f"synoptic {wl} done: {res}; wall {tot:.0f} s; {res['ok'] / tot:.2f} files/s; "
        f"MB/1000 frames full {st['bytes_full'] / n * 1000 / 1e6:.0f}, cropped {st['bytes_crop'] / n * 1000 / 1e6:.1f}")
    json.dump(dict(res, wall_s=tot, workers_end=workers, bytes_full=st["bytes_full"], bytes_crop=st["bytes_crop"]),
              open(f"{ROOT}/syn{wl}_stats.json", "w"))


# ---------------------------------------------------------------- per-frame means (any source) -> series
def series(e, files, source, ptab=None):
    from euv_dctrl import frames
    mag = sunpy.map.Map(glob.glob(f"{d_of(e)}/1/*magnetogram*.fits")[0])
    bm = fits.open(glob.glob(f"{d_of(e)}/1/*bitmap*.fits")[0])[-1].data
    S, short, n = samples(mag.data, bm)
    rows = []
    for to, q, exp, r in frames(files, source, ptab):
        rows.append(dict(t_obs=to, quality=q, exptime=exp, **frame_means(r.data, hmi_to_frame(mag, r), S)))
    s = pd.DataFrame(rows).sort_values("t_obs").reset_index(drop=True)
    t = pd.Timestamp(e.t)
    ev, _ = swpc.load(t - pd.Timedelta("2D"), t)
    regions = {int(x) for x in str(e.noaa_ars).split(",") if x.strip()}
    ex, _, _, _ = flare_excluded(s.t_obs, ev, regions)
    med = s.loc[(s.quality == 0) & (s.exptime > 0), "exptime"].median()
    s["valid"] = ~ex & (s.quality == 0) & s.box.notna() & (s.exptime >= 0.5 * med)
    return s, S, short, n


def at_cadence(s, t, cad):
    """nearest valid frame within +-cad/2 of each slot; returns (subseries, filled fraction)"""
    slots = pd.date_range(t - pd.Timedelta("24h") + pd.Timedelta(f"{cad}min"), t, freq=f"{cad}min")
    v = s[s.valid].reset_index(drop=True)
    if not len(v):
        return v, 0.0
    tt = v.t_obs.to_numpy()
    pick = []
    for sl in slots.to_numpy():
        j = int(np.argmin(np.abs(tt - sl)))
        if abs(tt[j] - sl) <= np.timedelta64(int(cad * 30), "s"):
            pick.append(j)
    return v.iloc[sorted(set(pick))].reset_index(drop=True), len(pick) / len(slots)


def cv_all(source, wl, ids=None, tag=None):
    a = alarms() if ids is None else alarms().iloc[ids]
    out = []
    for e in a.itertuples():
        t0 = time.time()
        sub = "syn" if source == "synoptic" else "cut"
        files = sorted(glob.glob(f"{d_of(e)}/{sub}{wl}/*.fits"))
        ptab = None
        if source == "cutout":
            from astropy.time import Time
            from aiapy.calibrate.utils import get_pointing_table
            t = pd.Timestamp(e.t)
            ptab = get_pointing_table("JSOC", time_range=(Time(t - pd.Timedelta("26h")), Time(t + pd.Timedelta("2h"))))
        s, S, short, n = series(e, files, source, ptab)
        s.to_csv(f"{d_of(e)}/series_{sub}{wl}.csv", index=False)
        for cad in CADS:
            v, fill = at_cadence(s, pd.Timestamp(e.t), cad)
            r = summarise(v.assign(valid=True), S, short, n, f"{source}_{wl}_{cad}min") if len(v) >= 3 else {}
            out.append(dict(order=e.order, harpnum=e.harpnum, t=e.t, source=source, wl=wl, cad_min=cad,
                            files=len(files), filled_frac=round(fill, 4), alarm_valid=fill >= 0.90,
                            dCV=r.get("dCV", np.nan), dCV_sd=r.get("dCV_sd", np.nan), CV_PIL=r.get("CV_PIL", np.nan),
                            CV_ctrl=r.get("CV_ctrl", np.nan), CV_box=r.get("CV_box", np.nan), n_pix=n, ctrl_short=short,
                            proc_s=round(time.time() - t0, 1)))
        log(f"cv {source} {wl} alarm {e.order} HARP {e.harpnum}: {len(files)} files, {time.time() - t0:.0f} s")
    df = pd.DataFrame(out)
    df.to_csv(f"{ROOT}/cv_{tag or source}_{wl}.csv", index=False)
    return df


def agreement(df, ref=2):
    """per cadence vs ref: Spearman rho (bootstrap CI, 2,000, seed 0) and median |diff|, alarms valid at both."""
    w = df.pivot_table(index="order", columns="cad_min", values="dCV")
    ok = df.pivot_table(index="order", columns="cad_min", values="alarm_valid")
    rows = []
    for c in [x for x in CADS if x != ref]:
        m = (ok[c] > 0) & (ok[ref] > 0) & w[c].notna() & w[ref].notna()
        x, y = w.loc[m, c].to_numpy(), w.loc[m, ref].to_numpy()
        rho = spearmanr(x, y).statistic if len(x) > 2 else np.nan
        rng = np.random.RandomState(0); bs = []
        for _ in range(2000):
            ix = rng.randint(0, len(x), len(x))
            if len(set(ix)) > 2:
                v = spearmanr(x[ix], y[ix]).statistic
                if np.isfinite(v):
                    bs.append(v)
        lo, hi = np.percentile(bs, [2.5, 97.5]) if bs else (np.nan, np.nan)
        med = float(np.median(np.abs(x - y))) if len(x) else np.nan
        rows.append(dict(cad_min=c, ref_min=ref, n=len(x), spearman=round(rho, 4), rho_lo=round(lo, 4), rho_hi=round(hi, 4),
                         median_abs_diff=round(med, 4), PASS=bool(rho >= 0.9 and med <= 0.02)))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- crop verification on the 3 pilot HARPs
def verify_crop():
    from euv_download import EP
    out = []
    for e in EP.itertuples():
        h = int(e.harpnum)
        mag = sunpy.map.Map(glob.glob(f"data/euv_pilot/{h}/1/*magnetogram*.fits")[0])
        bm = fits.open(glob.glob(f"data/euv_pilot/{h}/1/*bitmap*.fits")[0])[-1].data
        S, short, n = samples(mag.data, bm); ed = edge_coords(mag)
        full_rows, crop_rows, bf, bc = [], [], 0, 0
        for f in sorted(glob.glob(f"data/euv_pilot/{h}/syn_94/*.fits")):
            m = sunpy.map.Map(f); cm = crop(m, mag, ed)
            p = f"/tmp/_crop_{h}.fits"; cm.save(p, overwrite=True); cm = sunpy.map.Map(p)
            bf += os.path.getsize(f); bc += os.path.getsize(p)
            for mm, rows in [(m, full_rows), (cm, crop_rows)]:
                rows.append(dict(t_obs=pd.Timestamp(mm.meta["t_obs"].rstrip("Z")), valid=True,
                                 **frame_means(mm.data.astype(float), hmi_to_frame(mag, mm), S)))
        a_ = summarise(pd.DataFrame(full_rows), S, short, n, "full")
        b_ = summarise(pd.DataFrame(crop_rows), S, short, n, "crop")
        nf = len(full_rows)
        out.append(dict(harpnum=h, frames=nf, dCV_full=a_["dCV"], dCV_crop=b_["dCV"],
                        abs_diff=abs(a_["dCV"] - b_["dCV"]), PASS=abs(a_["dCV"] - b_["dCV"]) < 1e-6,
                        MB_per_1000_full=round(bf / nf * 1000 / 1e6, 1), MB_per_1000_crop=round(bc / nf * 1000 / 1e6, 1)))
    df = pd.DataFrame(out); df.to_csv(f"{ROOT}/verify_crop.csv", index=False); log(df.to_string(index=False))


# ---------------------------------------------------------------- Phase 3: JSOC 2-min cutouts (url-tar), overlap test
def cut_spec(e, wl=94):
    mag = sunpy.map.Map(glob.glob(f"{d_of(e)}/1/*magnetogram*.fits")[0])
    bl, tr = mag.bottom_left_coord, mag.top_right_coord
    x0, x1 = sorted([bl.Tx.to_value("arcsec"), tr.Tx.to_value("arcsec")]); y0, y1 = sorted([bl.Ty.to_value("arcsec"), tr.Ty.to_value("arcsec")])
    t = pd.Timestamp(e.t); fmt = lambda x: x.strftime("%Y-%m-%dT%H:%M:%SZ")
    im = {"im_patch": {"t_ref": t.strftime("%Y-%m-%dT%H:%M:%S"), "t": 0, "r": 0, "c": 0, "locunits": "arcsec",
                       "boxunits": "arcsec", "x": round((x0 + x1) / 2, 1), "y": round((y0 + y1) / 2, 1),
                       "width": round(x1 - x0 + 2 * MARGIN, 1), "height": round(y1 - y0 + 2 * MARGIN, 1)}}
    return f"aia.lev1_euv_12s[{fmt(t - pd.Timedelta(hours=24) + pd.Timedelta(minutes=2))}-{fmt(t)}@2m][{wl}]{{image}}", im


def cutouts(n=10, wl=94):
    """first n alarms (seed-1 order). Overlap test: submit the next export as soon as the previous is complete,
    while its tar downloads; on a 'pending export' rejection, revert to sequential and log the response."""
    import threading
    a = alarms().head(n); c = drms.Client(email=EMAIL); overlap = True; rows = []
    pending = []                                         # (e, request, t_submit)
    dl_threads = []

    def download(e, r, t_sub, t_ready):
        d = f"{d_of(e)}/cut{wl}"; os.makedirs(d, exist_ok=True); t1 = time.time()
        for k in range(5):
            try:
                r.download(d, timeout=900); break
            except (TimeoutError, ConnectionError, OSError) as err:
                log(f"tar retry {k + 1}: {err!r}"); time.sleep(30)
        nb = 0
        for tp in glob.glob(f"{d}/*.tar"):
            nb += os.path.getsize(tp)
            with tarfile.open(tp) as tf:
                for m in tf.getmembers():
                    if m.isfile() and m.name.endswith(".fits"):
                        m.name = os.path.basename(m.name); tf.extract(m, d)
            os.remove(tp)
        rows.append(dict(order=e.order, harpnum=e.harpnum, request_id=r.id, prep_s=round(t_ready - t_sub, 1),
                         download_s=round(time.time() - t1, 1), tar_bytes=nb, files=len(glob.glob(f"{d}/*.fits"))))
        log(f"cutout {e.order} HARP {e.harpnum}: {rows[-1]}")

    for e in a.itertuples():
        d = f"{d_of(e)}/cut{wl}"
        if len(glob.glob(f"{d}/*.fits")) >= 700:
            log(f"cutout {e.order}: present, skipped"); continue
        ds, proc = cut_spec(e, wl)
        while True:
            t_sub = time.time()
            r = c.export(ds, method="url-tar", protocol="fits", process=proc)
            if r.status == 7:                            # second pending export rejected
                msg = r._d.get("error", "")
                if overlap:
                    log(f"OVERLAP REJECTED: {msg!r} -> reverting to sequential")
                    overlap = False
                for th in dl_threads:
                    th.join()
                time.sleep(20); continue
            break
        while True:
            try:
                r.wait(sleep=20, timeout=6 * 3600); break
            except (TimeoutError, ConnectionError, OSError) as err:
                log(f"wait retry: {err!r}"); time.sleep(60)
        if not r.has_succeeded():
            raise RuntimeError(f"export failed {r.status} {ds}")
        t_ready = time.time()
        th = threading.Thread(target=download, args=(e, r, t_sub, t_ready)); th.start(); dl_threads.append(th)
        if not overlap:
            th.join()
    for th in dl_threads:
        th.join()
    pd.DataFrame(rows).to_csv(f"{ROOT}/cutout_timing.csv", index=False)
    log(f"cutouts done; overlap mode kept: {overlap}")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "select":
        select()
    elif cmd == "hmi":
        hmi()
    elif cmd == "verify_crop":
        verify_crop()
    elif cmd == "syn":
        syn(int(sys.argv[2]) if len(sys.argv) > 2 else 94)
    elif cmd == "cv":
        df = cv_all("synoptic", int(sys.argv[2]) if len(sys.argv) > 2 else 94)
        g = agreement(df); g.to_csv(f"{ROOT}/agreement_synoptic.csv", index=False); log(g.to_string(index=False))
    elif cmd == "cutouts":
        cutouts()
    elif cmd == "cv_cut":
        df = cv_all("cutout", 94, ids=list(range(10)), tag="cutout")
        g = agreement(df); g.to_csv(f"{ROOT}/agreement_cutout.csv", index=False); log(g.to_string(index=False))
