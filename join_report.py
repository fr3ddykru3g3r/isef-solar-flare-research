"""Per-year M1+ flare -> HARP join diagnostics.

A flare can only be joined if HEK gives it a usable NOAA region number.
ar_noaanum <= 0 or NaN means "region unknown" (NOT region zero) and is never joined --
joining it would silently produce false-negative labels.

Usable-year threshold fixed in advance: a year is USABLE if >= 90% of its M1+ flares
carry a usable region number.  Set 2026-09-21, before any results were seen.
"""
import glob, sys
import pandas as pd
import flares

THRESHOLD = 0.90
YEARS = range(2010, 2025)


def sharp_noaa_by_year():
    """{year: set(NOAA numbers appearing in NOAA_ARS of that year's raw SHARP files)}"""
    out = {}
    for f in sorted(glob.glob("data/raw_sharp_*.csv")):
        stem = f.split("raw_sharp_")[1][:8]
        if len(stem) != 8 or not stem.isdigit():
            continue
        y = int(stem[:4])
        d = pd.read_csv(f, usecols=["NOAA_ARS"], low_memory=False)
        s = out.setdefault(y, set())
        for v in d["NOAA_ARS"].dropna().astype(str):
            s.update(int(x) for x in v.split(",") if x.strip().isdigit())
    return out


def label_stats_by_year():
    """{year: (positive rows, distinct HARPs with a positive)} from the labelled chunk files."""
    out = {}
    for f in sorted(glob.glob("data/labelled_*.csv")):
        stem = f.split("labelled_")[1][:8]
        if len(stem) != 8 or not stem.isdigit():
            continue
        d = pd.read_csv(f, usecols=["harpnum", "t_rec_utc", "flared_M1_next_24h"], low_memory=False)
        if not len(d):
            continue
        d["year"] = pd.to_datetime(d["t_rec_utc"]).dt.year
        for y, g in d.groupby("year"):
            pos = g[g["flared_M1_next_24h"] == 1]
            n, h = out.get(y, (0, set()))
            out[y] = (n + len(pos), h | set(pos["harpnum"]))
    return out


def build():
    sharp = sharp_noaa_by_year()
    labels = label_stats_by_year()
    rows = []
    for y in YEARS:
        # m1 holds ONLY joinable M1+ flares; the unjoinable ones are counted in attrs
        _, m1 = flares.fetch(pd.Timestamp(f"{y}-01-01"), pd.Timestamp(f"{y+1}-01-01"), verbose=False)
        unknown = m1.attrs.get("n_unknown_m1", 0)
        total = len(m1) + unknown                 # all M1+ flares retrieved this year
        known = sharp.get(y, set())
        joined = int(m1["noaa_ar"].isin(known).sum()) if len(m1) else 0
        npos, pos_harps = labels.get(y, (0, set()))
        rows.append({"year": y, "m1_total": total, "m1_unknown_region": unknown,
                     "pct_usable_region": (total - unknown) / total if total else float("nan"),
                     "pct_joining_harp": joined / total if total else float("nan"),
                     "pos_rows": npos, "pos_harps": len(pos_harps)})
        print(f"  {y} done", file=sys.stderr, flush=True)
    df = pd.DataFrame(rows)
    df["verdict"] = df["pct_usable_region"].apply(
        lambda p: "USABLE" if p >= THRESHOLD else ("no M1+ flares" if pd.isna(p) else "UNUSABLE"))
    return df


def show(df):
    print(f"\nper-year M1+ flare join report (threshold: >= {THRESHOLD:.0%} usable region)")
    print("M1+ only.  unknown_region = M1+ flares HEK gives no NOAA number for; they are")
    print("never joined, so they are label noise (missed positives) even in passing years.\n")
    print("year  M1+  unknown  %usable  %joined  pos_rows  pos_HARPs  verdict")
    for _, r in df.iterrows():
        pu = "    n/a" if pd.isna(r["pct_usable_region"]) else f"{r['pct_usable_region']:7.1%}"
        pj = "    n/a" if pd.isna(r["pct_joining_harp"]) else f"{r['pct_joining_harp']:7.1%}"
        print(f"{r['year']}  {r['m1_total']:4d}  {r['m1_unknown_region']:7d}  {pu:>7}  {pj:>7}"
              f"  {r['pos_rows']:8d}  {r['pos_harps']:9d}  {r['verdict']}")
    bad = df[df["verdict"] == "UNUSABLE"]
    print(f"\nyears below threshold: {list(bad['year']) or 'none'}")
    return bad


if __name__ == "__main__":
    d = build()
    d.to_csv("data/join_report.csv", index=False)
    show(d)
