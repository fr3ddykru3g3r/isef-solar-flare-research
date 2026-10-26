"""SWPC days whose report reads 'NO EVENT REPORTS.' -- genuinely quiet, or not compiled?
Cross-check only: count HEK/SWPC flares on those days, by class. HEK is NOT a label source here."""
import glob, sys
import pandas as pd
import flares

empty = sorted(pd.Timestamp(f.split("/")[-1][:8]) for f in glob.glob("data/swpc_events/*events.txt")
               if "NO EVENT REPORTS" in open(f, encoding="latin-1").read())
e = pd.DataFrame({"day": empty}); e["year"] = e["day"].dt.year
rows = []
for y, g in e.groupby("year"):
    h = flares.fetch_raw(pd.Timestamp(f"{y}-01-01"), pd.Timestamp(f"{y+1}-01-01"))
    h["day"] = h["start"].dt.normalize(); h["cls"] = h["goes_class"].str[0]
    on = h[h["day"].isin(set(g["day"]))]
    days_with = on.groupby("day").size()
    rows.append({"year": y, "empty_days": len(g), "empty_days_HEK_has_any": len(days_with),
                 "HEK_B": int((on["cls"] == "B").sum()), "HEK_C": int((on["cls"] == "C").sum()),
                 "HEK_M1plus": int((on["flux"] >= 1e-5).sum()),
                 "M1plus_days": sorted(on.loc[on["flux"] >= 1e-5, "day"].dt.strftime("%Y-%m-%d").unique())})
    print(f"  {y} done", file=sys.stderr, flush=True)
t = pd.DataFrame(rows); t.to_csv("data/empty_days_check.csv", index=False)
print(t.to_string(index=False))
