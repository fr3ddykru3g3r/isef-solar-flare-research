"""Audit 2018-01-01 -> 2020-12-31 (report only; no labels changed).

1. every SWPC M1+ event under K2 (true flux >= 1e-5)
2. every GOES M1+ peak (goes_xrs.peaks, primary + secondary fill) over the 3 years, matched to SWPC
   M1+ events within +-30 min (same rule as completeness_check.py); unmatched listed
3. for each SWPC M1+ event, why it produced (or did not produce) positive rows, traced stage by stage.
   Positive rows for a flare starting at T are rows with t_rec_utc in [T-24h, T) of a HARP whose
   NOAA_ARS contains the flare's region.  A row that survives every filter but is not labelled
   positive in the labelled file is a BUG.
"""
import glob
import numpy as np, pandas as pd
from astropy.time import Time
import goes_xrs, swpc

LO, HI = pd.Timestamp("2018-01-01"), pd.Timestamp("2020-12-31 23:59")
WINDOW = pd.Timedelta(minutes=30)

# ---------------------------------------------------------------- 1
ev, _ = swpc.load(LO, HI)
m1 = ev[ev["flux"] >= 1e-5].reset_index(drop=True)
print(f"1. SWPC M1+ events under K2, {LO:%Y-%m-%d} -> {HI:%Y-%m-%d}: {len(m1)}")
print(m1[["start", "peak", "goes_class", "flux", "cls", "noaa_ar", "obs"]]
      .rename(columns={"goes_class": "reported", "flux": "true_flux", "cls": "K2_class"}).to_string(index=False))

# ---------------------------------------------------------------- 2
days = pd.date_range(LO.normalize(), HI.normalize(), freq="D")
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor(8) as ex:
    parts = list(ex.map(lambda d: goes_xrs.day_minutes(d)[0], days))
s = pd.concat(parts).sort_index()
pk = pd.DataFrame(goes_xrs.peaks(s))
t = m1["peak"].fillna(m1["start"])
if len(pk):
    pk["matched_swpc"] = [((t - p).abs() <= WINDOW).any() for p in pk["goes_peak"]]
print(f"\n2. GOES M1+ peaks (true flux >= {goes_xrs.M1:.1e}), {len(days)} days, coverage {len(s)/(len(days)*1440):.1%}: "
      f"{len(pk)} peaks, {int(pk['matched_swpc'].sum()) if len(pk) else 0} matched to SWPC within +-30 min")
if len(pk):
    un = pk[~pk["matched_swpc"]]
    print(f"   unmatched: {len(un)}")
    if len(un):
        rows = []
        for _, p in un.iterrows():
            near = ev.assign(dt=(ev["peak"].fillna(ev["start"]) - p["goes_peak"]).abs()).nsmallest(1, "dt")
            n = near.iloc[0] if len(near) else None
            rows.append({"goes_peak": p["goes_peak"], "true_flux": f"{p['goes_flux_true']:.2e}",
                         "true_class": p["true_class"],
                         "nearest_swpc": "" if n is None else f"{n['goes_class']} ({n['obs']}) AR {n['noaa_ar']} "
                                                               f"peak {n['peak']:%m-%d %H:%M}, {n['dt']}"})
        print(pd.DataFrame(rows).to_string(index=False))

# ---------------------------------------------------------------- 3
raw = pd.concat([pd.read_csv(f, dtype={"NOAA_ARS": str, "T_REC": str})
                 for f in sorted(glob.glob("data/raw_sharp_201[789]*_*.csv") + glob.glob("data/raw_sharp_202[01]*_*.csv"))
                 if f.split("_")[-1][:8].isdigit() and len(f.split("_")[-2]) == 8], ignore_index=True)
raw = raw.drop_duplicates(["HARPNUM", "T_REC"])
tai = Time([x.replace("_TAI", "").replace(".", "-", 2).replace("_", " ") for x in raw["T_REC"]], format="iso", scale="tai")
raw["t_utc"] = pd.to_datetime(tai.utc.isot)
raw["ars"] = raw["NOAA_ARS"].fillna("").apply(lambda v: {int(x) for x in v.split(",") if x.strip().isdigit()})
lab = pd.read_csv("data/labelled_20100501_20250101.csv", parse_dates=["t_rec_utc"], low_memory=False)
lab = lab[(lab["t_rec_utc"] >= LO - pd.Timedelta(days=2)) & (lab["t_rec_utc"] <= HI + pd.Timedelta(days=2))]
lab["key"] = lab["harpnum"].astype(str) + "|" + lab["t_rec_tai"]
excl = pd.concat([pd.read_csv(f, parse_dates=["t_rec_utc"]) for f in glob.glob("data/excluded_missing_swpc_20*.csv")
                  if pd.read_csv(f).shape[0]], ignore_index=True) if glob.glob("data/excluded_missing_swpc_*.csv") else pd.DataFrame()

print("\n3. per SWPC M1+ event: rows that should be positive, stage by stage")
out = []
for _, e in m1.iterrows():
    T, ar = e["start"], e["noaa_ar"]
    r = {"start": T, "class": e["cls"] + f"{e['flux'] / {'X': 1e-4, 'M': 1e-5}[e['cls']]:.1f}", "region": ar}
    if pd.isna(ar):
        r.update(reason="no region (SWPC Reg# blank)"); out.append(r); continue
    ar = int(ar)
    harps = raw.loc[raw["ars"].apply(lambda s: ar in s), "HARPNUM"].unique()
    if len(harps) == 0:
        r.update(reason="region not in any SHARP NOAA_ARS"); out.append(r); continue
    w = raw[raw["HARPNUM"].isin(harps) & (raw["t_utc"] >= T - pd.Timedelta(hours=24)) & (raw["t_utc"] < T)]
    q = w[w["QUALITY"] == 0]
    lon = q[q["LON_FWT"].abs() <= 45]
    r.update(harps=",".join(map(str, harps)), raw_rows_24h=len(w), after_quality=len(q), after_lon45=len(lon))
    if len(w) == 0:
        reason = "HARP has no SHARP records in the 24h before"
    elif len(q) == 0:
        reason = "QUALITY filter (no QUALITY==0 row in window)"
    elif len(lon) == 0:
        reason = "HARP outside +-45 deg (all QUALITY==0 rows have |LON_FWT| > 45)"
    else:
        keys = lon["HARPNUM"].astype(str) + "|" + lon["T_REC"]
        L = lab[lab["key"].isin(keys)]
        ex = len(excl) and excl.merge(lon.rename(columns={"HARPNUM": "harpnum"})[["harpnum", "t_utc"]],
                                      left_on=["harpnum", "t_rec_utc"], right_on=["harpnum", "t_utc"]).shape[0]
        pos = L[L["flared_M1_next_24h"] == 1]
        r.update(in_labelled=len(L), positive=len(pos), excluded_missing_day=int(ex or 0),
                 single_pos=int((pos["noaa_ar_count"] == 1).sum()))
        if len(pos) == len(lon):
            reason = "OK: all surviving rows positive" + ("" if r["single_pos"] else " -- multi-region only (not in primary subset)")
        elif len(L) + int(ex or 0) < len(lon):
            reason = "BUG: rows survive filters but are missing from the labelled file"
        else:
            reason = "BUG: rows in labelled file but not labelled positive"
        if T.year == 2020:
            reason += " | 2020 excluded (decision L)"
    r["reason"] = reason
    out.append(r)
o = pd.DataFrame(out)
print(o.to_string(index=False))
print(f"\nBUG count: {int(o['reason'].str.startswith('BUG').sum())}")
