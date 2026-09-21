"""Completeness of SWPC M1+ events against the GOES X-ray flux itself.  REPORT ONLY -- no label changes.

Sample: March of each year 2011-2019 (same sample as validate_swpc.py).
Rules fixed before running (me, 2026-09-21):
  GOES M1+ peak : a run of consecutive good minutes with flux >= goes_xrs.M1 (true flux; 1.0e-5 under
                  decision K2, was 1.43e-5 under K), primary satellite with secondary gap fill (H, I).
                  Runs separated by <= 5 minutes are merged into one peak.  Peak = the run's max.
  match         : an SWPC M1+ event (harmonised scale, K2: true flux) whose peak time -- or begin time if the peak is
                  missing -- lies within +-30 min of the GOES peak.
"""
import pandas as pd
import goes_xrs, swpc

MONTHS = [f"{y}-03" for y in range(2011, 2020)]
MERGE_GAP = pd.Timedelta(minutes=5)
WINDOW = pd.Timedelta(minutes=30)


def goes_peaks(s):
    """M1+ peaks from a 1-minute flux series."""
    above = s[s >= goes_xrs.M1]
    if above.empty:
        return []
    runs, cur = [], [above.index[0]]
    for t in above.index[1:]:
        if t - cur[-1] <= MERGE_GAP:
            cur.append(t)
        else:
            runs.append(cur); cur = [t]
    runs.append(cur)
    out = []
    for r in runs:
        seg = s[r[0]:r[-1]]
        out.append({"goes_peak": seg.idxmax(), "goes_flux_true": float(seg.max()),
                    "true_class": goes_xrs_class(seg.max())})
    return out


def goes_xrs_class(f):
    for letter, lo in (("X", 1e-4), ("M", 1e-5), ("C", 1e-6)):
        if f >= lo:
            return f"{letter}{f / lo:.1f}"
    return f"{f:.1e}"


rows, unmatched = [], []
for ym in MONTHS:
    lo = pd.Timestamp(f"{ym}-01"); hi = lo + pd.offsets.MonthBegin(1)
    days = pd.date_range(lo, hi - pd.Timedelta(days=1), freq="D")
    s = pd.concat([goes_xrs.day_minutes(d)[0] for d in days]).sort_index()
    peaks = goes_peaks(s)
    ev, _ = swpc.load(lo - WINDOW, hi + WINDOW)
    ev = ev[ev["flux"] >= 1e-5].copy()                        # SWPC M1+ on the harmonised scale
    ev["t"] = ev["peak"].fillna(ev["start"])
    n_match = 0
    for p in peaks:
        hit = ev[(ev["t"] - p["goes_peak"]).abs() <= WINDOW]
        if len(hit):
            n_match += 1
        else:
            unmatched.append({"month": ym, **p})
    rows.append({"month": ym, "goes_M1_peaks": len(peaks), "matched": n_match,
                 "unmatched": len(peaks) - n_match, "swpc_M1_events": len(ev),
                 "goes_coverage": len(s) / (len(days) * 1440)})
    print(f"  {ym} done", flush=True)

t = pd.DataFrame(rows)
t.to_csv("data/completeness_check.csv", index=False)
print("\nGOES M1+ peaks vs SWPC M1+ events, March 2011-2019 (+-30 min)")
print(t.to_string(index=False, formatters={"goes_coverage": "{:.1%}".format}))
print(f"\ntotal: {t['goes_M1_peaks'].sum()} GOES M1+ peaks, {t['matched'].sum()} matched, "
      f"{t['unmatched'].sum()} unmatched")
if unmatched:
    print("\nunmatched GOES M1+ peaks:")
    print(pd.DataFrame(unmatched).to_string(index=False))
