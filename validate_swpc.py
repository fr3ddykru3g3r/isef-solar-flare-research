"""Validate SWPC original event reports against HEK (which copies them), before relabelling.

Sample fixed IN ADVANCE (2026-09-21, before any SWPC results): March of each year 2011-2019.
All GOES classes are compared, not just M1+, because near solar minimum M1+ counts are ~0.
Matching: on begin minute.  Then class and region are compared on the matched pairs.
HEK region 0/NaN is 'unknown'; a SWPC region counts as agreeing only with an equal HEK region.
"""
import sys
import pandas as pd
import flares, swpc

MONTHS = [f"{y}-03" for y in range(2011, 2020)]


def compare(ym):
    lo = pd.Timestamp(f"{ym}-01"); hi = lo + pd.offsets.MonthBegin(1) - pd.Timedelta(minutes=1)
    s, n_dup = swpc.load(lo, hi)
    h = flares.fetch_raw(lo, hi)
    h["noaa_ar"] = h["noaa_ar"].where(h["noaa_ar"] > 0)          # 0 -> unknown
    m = s.merge(h, on="start", how="outer", suffixes=("_swpc", "_hek"), indicator=True)
    both = m[m["_merge"] == "both"]
    cls_ok = (both["goes_class_swpc"] == both["goes_class_hek"]).sum()
    have = both.dropna(subset=["noaa_ar_swpc", "noaa_ar_hek"])
    reg_ok = (have["noaa_ar_swpc"].astype(int) == have["noaa_ar_hek"].astype(int)).sum()
    return {"month": ym, "swpc": len(s), "swpc_dups": n_dup, "hek": len(h),
            "matched": len(both), "only_swpc": int((m["_merge"] == "left_only").sum()),
            "only_hek": int((m["_merge"] == "right_only").sum()),
            "class_agree": f"{cls_ok}/{len(both)}",
            "region_agree": f"{reg_ok}/{len(have)}",
            "swpc_region_hek_unknown": int((both["noaa_ar_swpc"].notna() & both["noaa_ar_hek"].isna()).sum()),
            "m1_swpc": int((s["flux"] >= 1e-5).sum())}, m


if __name__ == "__main__":
    rows, detail = [], []
    for ym in (sys.argv[1:] or MONTHS):
        r, m = compare(ym); rows.append(r); m["month"] = ym; detail.append(m)
        print(f"  {ym} done", file=sys.stderr, flush=True)
    t = pd.DataFrame(rows)
    t.to_csv("data/validate_swpc.csv", index=False)
    pd.concat(detail).to_csv("data/validate_swpc_detail.csv", index=False)
    print("\nSWPC originals vs HEK -- March of each year, all GOES classes")
    print(t.to_string(index=False))
    tot_m, tot_s, tot_h = t["matched"].sum(), t["swpc"].sum(), t["hek"].sum()
    print(f"\nmatched {tot_m} of {tot_s} SWPC / {tot_h} HEK events")
