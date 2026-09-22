"""Checker for EUV pilot downloads: counts, wavelength, coverage, box containment, gaps."""
import glob, sys
import numpy as np, pandas as pd, sunpy.map
from astropy.time import Time
from euv_download import EP, ROOT, MARGIN, box_from_item1

EXP = {2: (94, pd.Timedelta("12min"), 120), 3: (1600, pd.Timedelta("12min"), 120),
       4: (94, pd.Timedelta("12s"), 1800)}
SPAN = {2: "24h", 3: "24h", 4: "6h"}


def utc(s):
    """AIA T_OBS is UTC ('Z'); HMI-style '_TAI' strings are converted with astropy."""
    if s.endswith("_TAI"):
        return Time(s[:-4].replace("_", " ").replace(".", "-", 2), scale="tai").utc.datetime
    return s.rstrip("Z")


def check(h, t, item):
    wl, cad, n_exp = EXP[item]
    fs = sorted(glob.glob(f"{ROOT}/{h}/{item}/*.fits"))
    ms = [sunpy.map.Map(f) for f in fs]
    tobs = pd.to_datetime([utc(m.meta["t_obs"]) for m in ms])
    wls = sorted({int(m.meta["wavelnth"]) for m in ms})
    # expected slots (t-span, t], matched to nearest frame within half a cadence
    slots = pd.date_range(t - pd.Timedelta(SPAN[item]) + cad, t, freq=cad)
    d = np.array([np.abs((tobs - s).total_seconds()).min() if len(tobs) else np.inf for s in slots])
    gaps = [str(s) for s, x in zip(slots, d) if x > cad.total_seconds() / 2]
    # box: frame nearest t must contain the HARP box (margin removed); tracking keeps shape fixed
    b = box_from_item1(h); w, hh = b["width"] - 2 * MARGIN, b["height"] - 2 * MARGIN
    m = ms[int(np.argmin(np.abs((tobs - t).total_seconds())))]
    bl, tr = m.bottom_left_coord, m.top_right_coord
    inside = (bl.Tx.value <= b["x"] - w / 2 and tr.Tx.value >= b["x"] + w / 2 and
              bl.Ty.value <= b["y"] - hh / 2 and tr.Ty.value >= b["y"] + hh / 2)
    shapes = {m.data.shape for m in ms}
    return dict(harpnum=h, item=item, files=len(fs), expected=n_exp, wavelengths=wls, wl_ok=wls == [wl],
                first=tobs.min(), last=tobs.max(), n_gaps=len(gaps), gaps=";".join(gaps),
                box_inside_at_t=inside, shapes=len(shapes))


if __name__ == "__main__":
    items = [int(x) for x in sys.argv[1:]] or [2, 3]
    out = pd.DataFrame([check(int(e.harpnum), e.t, it) for e in EP.itertuples() for it in items])
    out.to_csv(f"{ROOT}/check.csv", index=False)
    print(out.drop(columns="gaps").to_string(index=False))
    for r in out[out.n_gaps > 0].itertuples():
        print(f"gaps HARP {r.harpnum} item {r.item}: {r.gaps}")
