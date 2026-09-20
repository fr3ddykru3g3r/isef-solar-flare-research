"""Run build_dataset.py over a long range in monthly chunks, resumably, then summarise.

Usage: python run_all.py [START END]      default 2010-05-01 2025-01-01
A chunk is skipped if its labelled CSV already exists, so re-running resumes.
"""
import sys, subprocess
from datetime import date
import numpy as np, pandas as pd

START = sys.argv[1] if len(sys.argv) > 1 else "2010-05-01"
END   = sys.argv[2] if len(sys.argv) > 2 else "2025-01-01"
PY    = sys.executable


def months(start, end):
    """[(chunk_start, chunk_end), ...] month boundaries, half-open."""
    s, e = date.fromisoformat(start), date.fromisoformat(end)
    out, cur = [], s
    while cur < e:
        nxt = date(cur.year + cur.month // 12, cur.month % 12 + 1, 1)
        out.append((cur.isoformat(), min(nxt, e).isoformat()))
        cur = nxt
    return out


chunks = months(START, END)
print(f"{len(chunks)} monthly chunks from {START} to {END}\n")
for i, (a, b) in enumerate(chunks, 1):
    tag = f"{a}_{b}".replace("-", "")
    done = f"data/labelled_{tag}.csv"
    import os
    if os.path.exists(done):
        print(f"[{i}/{len(chunks)}] {a} -> {b}  SKIP (already on disk)")
        continue
    print(f"[{i}/{len(chunks)}] {a} -> {b}  running...", flush=True)
    r = subprocess.run([PY, "build_dataset.py", a, b], capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-2000:]); print(r.stderr[-2000:])
        sys.exit(f"chunk {a}..{b} FAILED -- fix and re-run, completed chunks will be skipped")
    tail = [l for l in r.stdout.splitlines() if "SHARP rows retrieved" in l or "positives:" in l]
    print("          " + " | ".join(t.strip() for t in tail), flush=True)

# ------------------------------------------------------------------ concatenate
TAG = f"{START}_{END}".replace("-", "")
raw = pd.concat([pd.read_csv(f"data/raw_sharp_{a}_{b}.csv".replace("-", ""), low_memory=False)
                 for a, b in chunks], ignore_index=True)
lab = pd.concat([pd.read_csv(f"data/labelled_{a}_{b}.csv".replace("-", ""), parse_dates=["t_rec_utc"],
                             low_memory=False) for a, b in chunks], ignore_index=True)
raw.to_csv(f"data/raw_sharp_{TAG}.csv", index=False)
lab.to_csv(f"data/labelled_{TAG}.csv", index=False)
print(f"\nwrote data/raw_sharp_{TAG}.csv ({len(raw)}) and data/labelled_{TAG}.csv ({len(lab)})")

# ------------------------------------------------------------------ full summary
r = raw.copy(); r.columns = [c.lower() for c in r.columns]
feat = ["usflux", "totusjh", "totpot", "meanshr", "r_value", "absnjzh", "savncpp", "area_acr",
        "lat_fwt", "lon_fwt"]
for c in feat + ["quality"]:
    r[c] = pd.to_numeric(r[c], errors="coerce")
miss = r["noaa_ars"].isna() | r["noaa_ars"].astype(str).str.strip().isin(["", "nan", "MISSING"])
nars = r["noaa_ars"].astype(str).str.count(",") + 1

print("\n" + "=" * 62 + f"\nFULL SUMMARY  {START} .. {END}\n" + "=" * 62)
print(f"raw SHARP rows retrieved : {len(r)}")
print("mapping status           :", {"missing": int(miss.sum()),
                                     "single": int((~miss & (nars == 1)).sum()),
                                     "multiple": int((~miss & (nars > 1)).sum())})
s1 = r[r["quality"] == 0]
s2 = s1[s1["lon_fwt"].abs() <= 45]
s3 = s2[~(s2["noaa_ars"].isna() | s2["noaa_ars"].astype(str).str.strip().isin(["", "nan", "MISSING"]))]
print(f"after QUALITY==0         : {len(s1)}")
print(f"after |LON_FWT|<=45      : {len(s2)}")
print(f"after mapping!=missing   : {len(s3)}   (labelled file: {len(lab)})")

npos = int(lab["flared_M1_next_24h"].sum())
print(f"positives                : {npos} / {len(lab)}  ({npos/len(lab):.2%})")

n = lab.groupby("harpnum").size()
print(f"distinct HARPNUMs        : {lab['harpnum'].nunique()}")
print(f"rows per HARPNUM         : mean {n.mean():.1f}  median {n.median():.0f}  min {n.min()}  max {n.max()}")
print(f"HARPNUMs with a positive : {int(lab.groupby('harpnum')['flared_M1_next_24h'].max().sum())}")

print("\nper-feature missingness (labelled file):")
for c in feat:
    print(f"  {c:9s} {pd.to_numeric(lab[c], errors='coerce').isna().mean()*100:6.2f}%")

print("\npositive rate per year:")
y = lab.groupby(lab["t_rec_utc"].dt.year)["flared_M1_next_24h"].agg(["size", "sum"])
y["rate"] = y["sum"] / y["size"]
for yr, row in y.iterrows():
    print(f"  {yr}  rows {int(row['size']):7d}  pos {int(row['sum']):6d}  {row['rate']:7.2%}")
