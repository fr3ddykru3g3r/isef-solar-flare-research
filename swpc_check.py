"""Cross-check HEK/SWPC M1+ flares against SWPC's ORIGINAL daily event reports.

Source: NOAA SWPC "Edited Events" daily files, archived at NCEI:
  https://www.ngdc.noaa.gov/stp/space-weather/swpc-products/daily_reports/solar_event_reports/YYYY/MM/YYYYMMDDevents.txt
Only XRA (GOES X-ray) lines are used.  SWPC writes Reg# as 4 digits after region 10000
(e.g. 2975 = NOAA 12975), so 10000 is added to any Reg# below 10000.

This is a CHECK ONLY.  It does not change the label source (see decisions.md).
Usage: python swpc_check.py YYYY-MM [YYYY-MM ...]      default: 2014-03 2022-03
"""
import os, sys, urllib.request, calendar
import pandas as pd
import flares

URL = "https://www.ngdc.noaa.gov/stp/space-weather/swpc-products/daily_reports/solar_event_reports/{y}/{m:02d}/{y}{m:02d}{d:02d}events.txt"
CACHE = "data/swpc_events"


def day_file(y, m, d):
    """Download (once) and return the text of one SWPC daily event report."""
    os.makedirs(CACHE, exist_ok=True)
    path = f"{CACHE}/{y}{m:02d}{d:02d}events.txt"
    if not os.path.exists(path):
        with urllib.request.urlopen(URL.format(y=y, m=m, d=d), timeout=60) as r:
            open(path, "wb").write(r.read())
    return open(path, encoding="latin-1").read()


def parse_xra(text, y, m, d):
    """M1+ XRA events from one daily report -> list of dicts (begin UTC, class, SWPC region)."""
    out = []
    for line in text.splitlines():
        if " XRA " not in line or line.startswith("#"):
            continue
        tok = line.replace("+", " ").split()
        i = tok.index("XRA")
        begin, cls = tok[1], tok[i + 2]          # tok[0]=event no., tok[1]=begin time
        begin = "".join(ch for ch in begin if ch.isdigit())   # strip B/U/A qualifiers
        letter, flux = flares.parse_goes(cls)
        if len(begin) != 4 or flux != flux or flux < 1e-5:  # flux != flux is the NaN test
            continue
        reg = tok[i + 4] if len(tok) > i + 4 and tok[i + 4].isdigit() else None
        reg = None if reg is None else (int(reg) + 10000 if int(reg) < 10000 else int(reg))
        out.append({"start": pd.Timestamp(f"{y}-{m:02d}-{d:02d} {begin[:2]}:{begin[2:]}"),
                    "goes_class": cls, "swpc_region": reg})
    return out


def check_month(ym):
    y, m = map(int, ym.split("-"))
    swpc = []
    for d in range(1, calendar.monthrange(y, m)[1] + 1):
        swpc += parse_xra(day_file(y, m, d), y, m, d)
    s = pd.DataFrame(swpc)

    # HEK side: need the unknown-region flares too, so fetch raw and keep them
    lo, hi = pd.Timestamp(f"{y}-{m:02d}-01"), pd.Timestamp(f"{y}-{m:02d}-01") + pd.offsets.MonthBegin(1)
    hek = flares.fetch_raw_m1(lo, hi)

    # match on (begin minute, GOES class)
    s["key"] = s["start"].dt.strftime("%Y-%m-%d %H:%M") + " " + s["goes_class"]
    hek["key"] = hek["start"].dt.strftime("%Y-%m-%d %H:%M") + " " + hek["goes_class"]
    mg = s.merge(hek[["key", "noaa_ar"]], on="key", how="outer", indicator=True)

    both = mg[mg["_merge"] == "both"]
    print(f"\n=== {ym} ===")
    print(f"M1+ in SWPC original reports : {len(s)}   (with Reg#: {s['swpc_region'].notna().sum()})")
    print(f"M1+ in HEK (frm_name=SWPC)    : {len(hek)}   (usable region: {(hek['noaa_ar'] > 0).sum()})")
    print(f"matched on begin+class        : {len(both)}")
    print(f"only in SWPC originals        : {(mg['_merge'] == 'left_only').sum()}")
    print(f"only in HEK                   : {(mg['_merge'] == 'right_only').sum()}")
    agree = (both["swpc_region"] == both["noaa_ar"]).sum()
    hek_lost = ((both["noaa_ar"].fillna(0) <= 0) & both["swpc_region"].notna()).sum()
    print(f"region agrees (matched)       : {agree} / {len(both)}")
    print(f"SWPC has Reg#, HEK has 0/NaN  : {hek_lost}   <- region lost between SWPC and HEK")
    cols = ["start", "goes_class", "swpc_region", "noaa_ar", "_merge"]
    print(mg.sort_values("start")[cols].to_string(index=False))
    return mg


if __name__ == "__main__":
    for ym in (sys.argv[1:] or ["2014-03", "2022-03"]):
        check_month(ym)
