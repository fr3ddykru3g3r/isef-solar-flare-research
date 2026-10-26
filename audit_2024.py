"""Why is the 2024 positive rate 14%?  Real activity, duplicates, or a few multi-region HARPs?"""
import pandas as pd
import flares

print("M1+ flares per month, 2024 (HEK/SWPC)")
print("month    retrieved  dups_removed  M1+_joinable  M1+_unknown_region")
for m in range(1, 13):
    lo = pd.Timestamp(f"2024-{m:02d}-01"); hi = lo + pd.offsets.MonthBegin(1)
    res = flares.Fido.search(flares.a.Time(lo, hi), flares.a.hek.EventType("FL"),
                             flares.a.hek.FRM.Name == "SWPC")["hek"]
    n_raw = len(res)
    fl, m1 = flares.fetch(lo, hi, verbose=False)
    raw = flares.fetch_raw_m1(lo, hi)             # dedup'd, includes unknown-region
    # duplicates = raw rows minus rows after (start, noaa_ar, goes_class) dedup, all classes
    import numpy as np
    st = res["event_starttime"]
    allfl = pd.DataFrame({"start": pd.to_datetime(np.asarray(st.to_datetime())),
                          "noaa_ar": np.asarray(res["ar_noaanum"]),
                          "goes_class": np.asarray(res["fl_goescls"])})
    dups = n_raw - len(allfl.drop_duplicates(subset=["start", "noaa_ar", "goes_class"]))
    print(f"2024-{m:02d}  {n_raw:9d}  {dups:12d}  {len(m1):12d}  {m1.attrs['n_unknown_m1']:18d}")

lab = pd.read_csv("data/labelled_20100501_20250101.csv", parse_dates=["t_rec_utc"], low_memory=False)
y = lab[lab["t_rec_utc"].dt.year == 2024]
pos = y[y["flared_M1_next_24h"] == 1]
print(f"\n2024 labelled rows: {len(y)}   positives: {len(pos)} ({len(pos)/len(y):.2%})")
print(f"positive rows by noaa_mapping_status: {pos['noaa_mapping_status'].value_counts().to_dict()}")
print(f"all rows by noaa_mapping_status     : {y['noaa_mapping_status'].value_counts().to_dict()}")

top = (pos.groupby("harpnum")
          .agg(pos_rows=("flared_M1_next_24h", "size"), noaa_ar_count=("noaa_ar_count", "max"),
               noaa_ars=("noaa_ars", "last"))
          .sort_values("pos_rows", ascending=False))
top["share_of_2024_pos"] = top["pos_rows"] / len(pos)
print(f"\ntop 10 HARPs by positive rows (of {len(top)} HARPs with a 2024 positive):")
print(top.head(10).to_string(formatters={"share_of_2024_pos": "{:.1%}".format}))
print(f"\ntop 10 share of all 2024 positives: {top.head(10)['pos_rows'].sum()/len(pos):.1%}")

# same rate with multi-region HARPs set aside, for comparison only (NOT a filter change)
s = y[y["noaa_mapping_status"] == "single"]
print(f"positive rate, single-region rows only (comparison, not a filter): "
      f"{s['flared_M1_next_24h'].mean():.2%} of {len(s)}")
for yr in (2014, 2024):
    g = lab[lab["t_rec_utc"].dt.year == yr]
    print(f"{yr}: rows {len(g)}, distinct HARPs {g['harpnum'].nunique()}, "
          f"HARPs with a positive {g.loc[g['flared_M1_next_24h']==1,'harpnum'].nunique()}")
