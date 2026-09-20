"""Build a labelled SHARP dataset for flare forecasting (Bobra & Couvidat 2015 features).

Usage: python build_dataset.py [START] [END]     e.g. 2014-01-01 2014-02-01
Keyword queries only; no image segments.
"""
import sys, re
from datetime import datetime
import numpy as np, pandas as pd, drms
from astropy.time import Time
import astropy.units as u
import flares

if len(sys.argv) not in (1, 3):
    sys.exit("usage: python build_dataset.py [START END]   dates as YYYY-MM-DD, START inclusive, END exclusive")
START = sys.argv[1] if len(sys.argv) > 1 else "2014-01-01"
END   = sys.argv[2] if len(sys.argv) > 2 else "2014-02-01"
for d in (START, END):                                    # fail loudly on a typo'd date
    datetime.strptime(d, "%Y-%m-%d")
if START >= END:
    sys.exit(f"START ({START}) must be before END ({END})")
TAG   = f"{START}_{END}".replace("-", "")


def jsoc(d):
    """YYYY-MM-DD -> JSOC date literal YYYY.MM.DD_TAI"""
    return d.replace("-", ".") + "_TAI"


def banner():
    print("=" * 62)
    print(f"  argv          : {sys.argv[1:] or '(none -> defaults)'}")
    print(f"  START (CLI)   : {START}      END (CLI, exclusive): {END}")
    print(f"  START (JSOC)  : {jsoc(START)}   END (JSOC): {jsoc(END)}")
    print(f"  JSOC record set: hmi.sharp_cea_720s[][{jsoc(START)}-{jsoc(END)}@1h]")
    print("=" * 62)

FEATURES = ["USFLUX","TOTUSJH","TOTPOT","MEANSHR","R_VALUE","ABSNJZH","SAVNCPP","AREA_ACR"]
KEYS = ["HARPNUM","T_REC","NOAA_ARS","NOAA_NUM","QUALITY","LAT_FWT","LON_FWT"] + FEATURES


def step(msg): print(f"\n=== {msg} ===")


# ---------------------------------------------------------------- STEP 1
banner()
step("STEP 1  SHARP keywords")
c = drms.Client()
qs = f"hmi.sharp_cea_720s[][{jsoc(START)}-{jsoc(END)}@1h]"
print("query:", qs)
raw = c.query(qs, key=",".join(KEYS))
print(f"SHARP rows retrieved: {len(raw)}")
raw.to_csv(f"data/raw_sharp_{TAG}.csv", index=False)
print(f"saved data/raw_sharp_{TAG}.csv")

df = raw.copy()
df.columns = [x.lower() for x in df.columns]
df = df.rename(columns={"t_rec": "t_rec_tai"})

# expected hours: each HARP's own on-disk span, at 1h spacing
exp = 0
for h, g in df.groupby("harpnum"):
    t = pd.to_datetime(g["t_rec_tai"].str.replace("_TAI", "", regex=False), format="%Y.%m.%d_%H:%M:%S")
    exp += int((t.max() - t.min()).total_seconds() // 3600) + 1
print(f"expected hourly records (per-HARP span): {exp}; present: {len(df)}; missing: {exp - len(df)}")

# ---------------------------------------------------------------- STEP 3 (times first, needed for the padded flare window)
step("STEP 3  time handling (TAI -> UTC)")
tai = Time([s.replace("_TAI", "").replace(".", "-", 2).replace("_", " ") for s in df["t_rec_tai"]], format="iso", scale="tai")
df["t_rec_utc"] = pd.to_datetime(tai.utc.isot)
print("example:", df["t_rec_tai"].iloc[0], "->", df["t_rec_utc"].iloc[0], "UTC")

# ---------------------------------------------------------------- STEP 2
step("STEP 2  flare catalogue (HEK / SWPC)")
lo = (df["t_rec_utc"].min() - pd.Timedelta(hours=48)).to_pydatetime()
hi = (df["t_rec_utc"].max() + pd.Timedelta(hours=24)).to_pydatetime()
print(f"padded window: {lo} .. {hi}")
fl, m1 = flares.fetch(lo, hi)

# ---------------------------------------------------------------- STEP 4
step("STEP 4  NOAA mapping")
def ars(s):
    if s is None or (isinstance(s, float) and np.isnan(s)) or str(s).strip() in ("", "MISSING", "nan"):
        return []
    return [int(x) for x in str(s).split(",") if x.strip().isdigit()]

df["_ars"] = df["noaa_ars"].apply(ars)
df["noaa_ar_count"] = df["_ars"].apply(len)
df["noaa_mapping_status"] = np.where(df["noaa_ar_count"] == 0, "missing",
                             np.where(df["noaa_ar_count"] == 1, "single", "multiple"))
print(df["noaa_mapping_status"].value_counts().to_dict())

# ---------------------------------------------------------------- STEP 6
step("STEP 6  filtering")
print(f"in: {len(df)}")
df = df[df["quality"].astype(int) == 0];              print(f"after QUALITY==0: {len(df)}")
df = df[df["lon_fwt"].abs() <= 45];                   print(f"after |LON_FWT|<=45: {len(df)}")
nmiss = (df["noaa_mapping_status"] == "missing").sum()
df = df[df["noaa_mapping_status"] != "missing"];      print(f"after mapping!=missing: {len(df)}  (excluded {nmiss} missing-mapping rows)")

# ---------------------------------------------------------------- STEP 5
step("STEP 5  labels")
by_ar_m1 = {k: np.sort(v["start"].values) for k, v in m1.groupby("noaa_ar")}
by_ar_all = {k: v[["start", "cls"]].sort_values("start") for k, v in fl.groupby("noaa_ar")}

def label(row):
    t = row["t_rec_utc"]
    hi24 = t + pd.Timedelta(hours=24)
    lo48 = t - pd.Timedelta(hours=48)
    pos = 0
    prev = []
    for ar in row["_ars"]:
        s = by_ar_m1.get(ar)
        if s is not None and ((s > np.datetime64(t)) & (s <= np.datetime64(hi24))).any():
            pos = 1
        g = by_ar_all.get(ar)
        if g is not None:
            w = g[(g["start"] >= lo48) & (g["start"] < t)]
            prev.append(w)
    p = pd.concat(prev).drop_duplicates() if prev else pd.DataFrame(columns=["start", "cls"])
    return pd.Series([pos, len(p),
                      (p["cls"] == "C").sum(), (p["cls"] == "M").sum(), (p["cls"] == "X").sum()])

LABEL_COLS = ["flared_M1_next_24h", "n_flares_prev_48h", "n_C_prev_48h", "n_M_prev_48h", "n_X_prev_48h"]
if len(df):
    df[LABEL_COLS] = df.apply(label, axis=1)
else:
    # a chunk can be legitimately empty (e.g. May 2016: every record carries QUALITY bit 0x80)
    for c in LABEL_COLS:
        df[c] = pd.Series(dtype=int)
npos = int(df["flared_M1_next_24h"].sum())
print(f"positives: {npos} / {len(df)}  ({npos/max(len(df),1):.2%})")

# ---------------------------------------------------------------- STEP 7
step("STEP 7  missing values")
feat = [f.lower() for f in FEATURES] + ["lat_fwt", "lon_fwt"]
for col in feat:
    df[col] = pd.to_numeric(df[col], errors="coerce")
# drms already returns JSOC MISSING as NaN for float keywords; to_numeric above catches the rest.
# ponytail: no magnitude-based sentinel mask -- USFLUX/TOTPOT are legitimately ~1e22.
for col in feat:
    print(f"  {col:9s} {df[col].isna().mean()*100:6.2f}% missing")

out = ["harpnum","t_rec_tai","t_rec_utc","noaa_ars","noaa_ar_count","noaa_mapping_status",
       "usflux","totusjh","totpot","meanshr","r_value","absnjzh","savncpp","area_acr",
       "lat_fwt","lon_fwt","quality","flared_M1_next_24h","n_flares_prev_48h",
       "n_C_prev_48h","n_M_prev_48h","n_X_prev_48h"]
df[out].to_csv(f"data/labelled_{TAG}.csv", index=False)
print(f"\nsaved data/labelled_{TAG}.csv  ({len(df)} rows)")
