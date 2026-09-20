"""SWPC flare catalogue from HEK, shared by build_dataset.py and checks.py."""
import re
import numpy as np, pandas as pd
from sunpy.net import Fido, attrs as a

LETTER = {"A": 1e-8, "B": 1e-7, "C": 1e-6, "M": 1e-5, "X": 1e-4}


def parse_goes(s):
    """'M1.5' -> ('M', 1.5e-5).  Unparseable -> (None, nan)."""
    m = re.match(r"^([ABCMX])([\d.]*)$", str(s).strip())
    if not m:
        return None, np.nan
    return m.group(1), LETTER[m.group(1)] * (float(m.group(2)) if m.group(2) else 1.0)


def fetch(lo, hi, verbose=True):
    """SWPC flares with start time in [lo, hi]. Returns (all_flares, m1_plus)."""
    res = Fido.search(a.Time(lo, hi), a.hek.EventType("FL"), a.hek.FRM.Name == "SWPC")["hek"]
    st = res["event_starttime"]
    fl = pd.DataFrame({
        "start": pd.to_datetime(np.asarray(st.to_datetime() if hasattr(st, "to_datetime") else st)),
        "noaa_ar": pd.to_numeric(pd.Series(np.asarray(res["ar_noaanum"])), errors="coerce"),
        "goes_class": pd.Series(np.asarray(res["fl_goescls"])).astype(str).str.strip(),
    })
    n0 = len(fl)
    fl = fl.drop_duplicates(subset=["start", "noaa_ar", "goes_class"])
    fl[["cls", "flux"]] = fl["goes_class"].apply(lambda s: pd.Series(parse_goes(s)))
    fl = fl.dropna(subset=["noaa_ar", "flux"])
    fl["noaa_ar"] = fl["noaa_ar"].astype(int)
    m1 = fl[fl["flux"] >= 1e-5]          # M1.0 and above, parsed numerically here, not catalogue-side
    if verbose:
        print(f"flares retrieved: {n0}")
        print(f"duplicates removed: {n0 - len(fl) - 0}  (on start_time, noaa_ar, goes_class)")
        print(f"parsed & AR-matched: {len(fl)};  M1+ retained: {len(m1)}")
        print("class counts:", fl["cls"].value_counts().to_dict())
    return fl, m1
