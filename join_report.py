"""Per-year M1+ flare -> HARP join diagnostics.

A flare can only be joined if HEK gives it a usable NOAA region number.
ar_noaanum <= 0 or NaN means "region unknown" (NOT region zero) and is never joined --
joining it would silently produce false-negative labels.

Usable-year threshold fixed in advance: a year is USABLE if >= 90% of its M1+ flares
carry a usable region number.  Set 2026-09-21, before any results were seen.
"""
import os, sys
import pandas as pd
import flares, chunks

THRESHOLD = 0.90
YEARS = range(2010, 2025)


def sharp_noaa_by_year():
    """{year: set(NOAA numbers appearing in NOAA_ARS of that year's raw SHARP chunk files)}"""
    out = {}
    for a, f in chunks.files("raw_sharp"):
        d = pd.read_csv(f, usecols=["NOAA_ARS"], low_memory=False)
        s = out.setdefault(int(a[:4]), set())
        for v in d["NOAA_ARS"].dropna().astype(str):
            s.update(int(x) for x in v.split(",") if x.strip().isdigit())
    return out


def label_stats_by_year():
    """{year: (positive rows, distinct HARPs with a positive)} from the labelled chunk files."""
    out = {}
    for _, f in chunks.files("labelled"):
        d = pd.read_csv(f, usecols=["harpnum", "t_rec_utc", "flared_M1_next_24h"], low_memory=False)
        if not len(d):
            continue
        d["year"] = pd.to_datetime(d["t_rec_utc"]).dt.year
        for y, g in d.groupby("year"):
            pos = g[g["flared_M1_next_24h"] == 1]
            n, h = out.get(y, (0, set()))
            out[y] = (n + len(pos), h | set(pos["harpnum"]))
    return out


def year_window(y):
    """Year y clipped to the SHARP range, so 2010 does not count Jan-Apr flares with no SHARP data."""
    lo = max(pd.Timestamp(f"{y}-01-01"), pd.Timestamp(chunks.RANGE[0]))
    hi = min(pd.Timestamp(f"{y+1}-01-01"), pd.Timestamp(chunks.RANGE[1]))
    return lo, hi


def m1_for_year(y):
    """Joinable M1+ flares and the unknown-region M1+ count for year y, cached on disk."""
    path = f"data/hek_m1_{y}.csv"
    if os.path.exists(path):
        m1 = pd.read_csv(path)
        unknown = int(open(path + ".unknown").read())
    else:
        _, m1 = flares.fetch(*year_window(y), verbose=False)
        unknown = m1.attrs.get("n_unknown_m1", 0)
        m1.to_csv(path, index=False)
        open(path + ".unknown", "w").write(str(unknown))
    return m1, unknown


def build():
    sharp = sharp_noaa_by_year()
    labels = label_stats_by_year()
    rows = []
    for y in YEARS:
        # m1 holds ONLY joinable M1+ flares; unknown = M1+ flares with no usable region
        m1, unknown = m1_for_year(y)
        total = len(m1) + unknown                 # all M1+ flares retrieved this year
        known = sharp.get(y, set())
        joined = int(m1["noaa_ar"].isin(known).sum()) if len(m1) else 0
        npos, pos_harps = labels.get(y, (0, set()))
        rows.append({"year": y, "m1_total": total, "m1_unknown_region": unknown,
                     "pct_usable_region": (total - unknown) / total if total else float("nan"),
                     "m1_joined": joined,
                     "pct_joining_harp": joined / total if total else float("nan"),
                     "pos_rows": npos, "pos_harps": len(pos_harps)})
        print(f"  {y} done", file=sys.stderr, flush=True)
    df = pd.DataFrame(rows)
    df["verdict"] = df["pct_usable_region"].apply(
        lambda p: "USABLE" if p >= THRESHOLD else ("no M1+ flares" if pd.isna(p) else "UNUSABLE"))
    return df


def show(df):
    if "m1_joined" not in df:     # older cached csv: recover the exact integer from the fraction
        df["m1_joined"] = (df["pct_joining_harp"].fillna(0) * df["m1_total"]).round().astype(int)
    print(f"\nper-year M1+ flare join report (threshold: >= {THRESHOLD:.0%} usable region)")
    print("M1+ only.  unknown = M1+ flares HEK gives no NOAA number for; never joined, so they")
    print("are label noise (missed positives) even in passing years.")
    print("joined = M1+ flares whose region appears in >= 1 HARP's NOAA_ARS that year.\n")
    print("year   M1+  unknown  %usable  joined  %joined  pos_rows  pos_HARPs  verdict")
    for _, r in df.iterrows():
        pu = "    n/a" if pd.isna(r["pct_usable_region"]) else f"{r['pct_usable_region']:7.1%}"
        pj = "    n/a" if pd.isna(r["pct_joining_harp"]) else f"{r['pct_joining_harp']:7.1%}"
        print(f"{r['year']}  {r['m1_total']:4d}  {r['m1_unknown_region']:7d}  {pu:>7}  {r['m1_joined']:6d}"
              f"  {pj:>7}  {r['pos_rows']:8d}  {r['pos_harps']:9d}  {r['verdict']}")
    bad = df[df["verdict"] == "UNUSABLE"]
    print(f"\nyears below threshold: {list(bad['year']) or 'none'}")
    return bad


if __name__ == "__main__":
    d = build()
    d.to_csv("data/join_report.csv", index=False)
    show(d)
