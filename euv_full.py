"""FULL EUV STUDY, 94 A only (decisions.md 2026-09-23 amendment). Outputs only under data/euv_full/.
Usage: python euv_full.py hmi_check | dryrun | hmi | run | counts"""
import glob, hashlib, io, json, os, socket, sys, tarfile, time, urllib.request
socket.setdefaulttimeout(120)
import numpy as np, pandas as pd, sunpy.map, drms, astropy.units as u
from astropy.io import fits
from euv_download import EMAIL
from euv_pilot import pil_mask, ar_mask

R = "data/euv_full"
for sub in ["dryrun", "hmi", "aia", "series", "results", "logs"]:
    os.makedirs(f"{R}/{sub}", exist_ok=True)
MARGIN = 50.0


def log(msg, f="logs/run.log"):
    print(msg, flush=True)
    with open(f"{R}/{f}", "a") as fh:
        fh.write(f"{pd.Timestamp.now():%Y-%m-%d %H:%M:%S} {msg}\n")


# ---------------------------------------------------------------- HMI masks: direct access (url_quick, as-is) + keyword header
def hmi_direct(harp, trec, dest, keys):
    """download magnetogram+bitmap as-is; rebuild headers from a keyword query (keys = header keys of the exported files).
    Returns (magnetogram path, bitmap path, seconds)."""
    t0 = time.time(); os.makedirs(dest, exist_ok=True)
    c = drms.Client(email=EMAIL)
    ds = f"hmi.sharp_720s[{harp}][{trec}]"
    r = c.export(ds + "{magnetogram,bitmap}", method="url_quick", protocol="as-is")
    if r.status != 0 or not len(r.urls):
        raise RuntimeError(f"url_quick failed {ds}: status {r.status}")
    kw = c.query(ds, key=",".join(keys)).iloc[0]
    out = {}
    for _, u_ in r.urls.iterrows():
        seg = u_.filename.replace(".fits", "")
        raw = urllib.request.urlopen(u_.url).read()
        with fits.open(io.BytesIO(raw)) as hd:
            hdu = hd[1] if len(hd) > 1 else hd[0]
            data = hdu.data.astype(np.float64) if seg == "magnetogram" else hdu.data
        h = fits.Header()
        for k in keys:
            v = kw.get(k)
            if v is None or (isinstance(v, float) and np.isnan(v)) or (isinstance(v, str) and v.strip() == ""):
                continue
            v = v.item() if hasattr(v, "item") else v
            if isinstance(v, str):
                v = "".join(ch if 32 <= ord(ch) < 127 else " " for ch in v)   # version strings contain newlines
            h[k] = v
        p = f"{dest}/hmi.sharp_720s.{harp}.{trec.replace('.', '').replace(':', '')}.{seg}.fits"
        fits.PrimaryHDU(data=data, header=h).writeto(p + ".tmp", overwrite=True); os.replace(p + ".tmp", p)
        out[seg] = p
    return out["magnetogram"], out["bitmap"], time.time() - t0


WCS_KEYS = None


def header_keys(ref_file):
    h = fits.getheader(ref_file, 1) if len(fits.open(ref_file)) > 1 else fits.getheader(ref_file)
    skip = {"SIMPLE", "BITPIX", "NAXIS", "NAXIS1", "NAXIS2", "EXTEND", "XTENSION", "PCOUNT", "GCOUNT", "TFIELDS",
            "ZIMAGE", "ZBITPIX", "ZNAXIS", "ZNAXIS1", "ZNAXIS2", "ZTILE1", "ZTILE2", "ZCMPTYPE", "ZNAME1", "ZVAL1",
            "ZNAME2", "ZVAL2", "ZSIMPLE", "ZQUANTIZ", "ZDITHER0", "BLANK", "BZERO", "BSCALE", "CHECKSUM", "DATASUM",
            "COMMENT", "HISTORY", ""}
    return [k for k in h.keys() if k not in skip and not k.startswith(("TTYPE", "TFORM", "ZHECKSUM", "ZDATASUM"))]


def hmi_check():
    """step 2a: direct access vs the pilot's exported files, 3 pilot records."""
    from euv_download import EP
    from euv_dctrl import samples, hmi_to_frame
    rows = []
    ref0 = glob.glob("data/euv_pilot/4231/1/*magnetogram*.fits")[0]
    keys = header_keys(ref0)
    exp = pd.read_csv("data/euv_pilot/download_log.csv"); exp = exp[exp["item"] == 1].set_index("harpnum").wall_s
    for e in EP.itertuples():
        h = int(e.harpnum)
        m_old = sunpy.map.Map(glob.glob(f"data/euv_pilot/{h}/1/*magnetogram*.fits")[0])
        b_old = fits.open(glob.glob(f"data/euv_pilot/{h}/1/*bitmap*.fits")[0])[-1].data
        mp, bp, dt = hmi_direct(h, e.t_rec_tai, f"{R}/dryrun/hmi_direct/{h}", keys)
        m_new = sunpy.map.Map(mp); b_new = fits.getdata(bp)
        a, b = m_old.data.astype(float), m_new.data.astype(float)
        fin = np.isfinite(a) & np.isfinite(b)
        S_old, *_ = samples(m_old.data, b_old); S_new, *_ = samples(m_new.data, b_new)
        aia = sunpy.map.Map(sorted(glob.glob(f"data/euv_pilot/{h}/2/*.fits"))[-1])
        idx_old, idx_new = hmi_to_frame(m_old, aia), hmi_to_frame(m_new, aia)
        rows.append(dict(harpnum=h, shape_equal=a.shape == b.shape, nan_pattern_equal=bool((np.isnan(a) == np.isnan(b)).all()),
                         max_abs_diff_finite=float(np.nanmax(np.abs(a[fin] - b[fin]))) if fin.any() else np.nan,
                         bitmap_equal=bool((np.asarray(b_old) == np.asarray(b_new)).all()),
                         pil_diff_px=int((pil_mask(m_old.data) != pil_mask(m_new.data)).sum()),
                         ar_diff_px=int((ar_mask(m_old.data) != ar_mask(m_new.data)).sum()),
                         dctrl_samples_equal=all(np.array_equal(S_old[k], S_new[k]) for k in S_old),
                         aia_mapping_equal=bool(np.array_equal(idx_old, idx_new)),
                         direct_s=round(dt, 1), export_wall_s=float(exp.get(h, np.nan))))
    df = pd.DataFrame(rows)
    df["PASS"] = (df.shape_equal & df.nan_pattern_equal & (df.max_abs_diff_finite == 0) & df.bitmap_equal
                  & (df.pil_diff_px == 0) & (df.ar_diff_px == 0))
    df.to_csv(f"{R}/dryrun/hmi_direct_check.csv", index=False)
    pd.set_option("display.width", 250); log("\n" + df.to_string(index=False), "logs/dryrun.log")
    json.dump({"keys": keys}, open(f"{R}/hmi_header_keys.json", "w"))
    return bool(df.PASS.all())


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "hmi_check":
        ok = hmi_check(); log(f"step 2a HMI direct access: {'PASS' if ok else 'FAIL'}", "logs/dryrun.log")
