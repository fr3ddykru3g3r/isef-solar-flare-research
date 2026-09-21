"""Flare catalogue from NOAA SWPC's ORIGINAL daily event reports (the catalogue HEK copies).

Source: https://www.ngdc.noaa.gov/stp/space-weather/swpc-products/daily_reports/solar_event_reports/
        YYYY/MM/YYYYMMDDevents.txt   ("Edited Events"), cached under data/swpc_events/.
Used for ALL years 2010-2024 -- never switched per year (decided by user, 2026-09-21).

Rules, each applied identically to every year:
  * only XRA lines (GOES 1-8 A X-ray events) are flares
  * begin time = the event's Begin column on that report's date, UTC
  * region: SWPC writes Reg# as 4 digits; rule is  reg < 10000 -> reg + 10000,  nothing else.
    blank Reg# = UNKNOWN region: kept in the catalogue, never joined (same rule as before)
  * dedup on (begin time, GOES class): SWPC can list one flare from two GOES satellites
    (e.g. G16 and G18); one physical flare must count once.
"""
import os, calendar, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
from flares import parse_goes

URL = ("https://www.ngdc.noaa.gov/stp/space-weather/swpc-products/daily_reports/"
       "solar_event_reports/{y}/{m:02d}/{y}{m:02d}{d:02d}events.txt")
CACHE = "data/swpc_events"
MISSING = f"{CACHE}/_missing_days.txt"      # days the archive has no report for (404)


def _path(day):
    return f"{CACHE}/{day:%Y%m%d}events.txt"


def download(day):
    """Cache one day's report. Returns 'ok', 'cached' or 'missing'."""
    if os.path.exists(_path(day)):
        return "cached"
    try:
        with urllib.request.urlopen(URL.format(y=day.year, m=day.month, d=day.day), timeout=60) as r:
            data = r.read()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return "missing"
        raise
    open(_path(day), "wb").write(data)
    return "ok"


def download_range(lo, hi, workers=8):
    """Cache every daily report in [lo, hi]; record 404 days in MISSING. Returns missing days."""
    os.makedirs(CACHE, exist_ok=True)
    days = list(pd.date_range(pd.Timestamp(lo).normalize(), pd.Timestamp(hi).normalize(), freq="D"))
    with ThreadPoolExecutor(workers) as ex:       # ponytail: 8 threads, polite to NCEI; raise if slow
        status = list(ex.map(download, days))
    missing = [d for d, s in zip(days, status) if s == "missing"]
    known = set(open(MISSING).read().split()) if os.path.exists(MISSING) else set()
    open(MISSING, "w").write("\n".join(sorted(known | {f"{d:%Y-%m-%d}" for d in missing})) + "\n")
    return missing


def missing_days():
    return set(open(MISSING).read().split()) if os.path.exists(MISSING) else set()


def to_noaa(reg):
    """The single region-conversion rule."""
    return reg + 10000 if reg < 10000 else reg


def parse_day(day):
    """All XRA events in one cached daily report -> list of dicts."""
    out = []
    if not os.path.exists(_path(day)):
        return out
    for line in open(_path(day), encoding="latin-1"):
        if line.startswith(("#", ":")) or " XRA " not in line:
            continue
        tok = line.replace("+", " ").split()
        i = tok.index("XRA")
        begin = "".join(ch for ch in tok[1] if ch.isdigit())      # strip B/U/A qualifiers
        if len(begin) != 4:
            continue                                                # begin time missing (////)
        cls = tok[i + 2] if len(tok) > i + 2 else ""
        letter, flux = parse_goes(cls)
        if letter is None:
            continue
        rest = tok[i + 3:]                                          # [flux] [Reg#]
        reg = next((int(t) for t in rest[1:] if t.isdigit()), None)
        out.append({"start": pd.Timestamp(f"{day:%Y-%m-%d} {begin[:2]}:{begin[2:]}"),
                    "goes_class": cls, "cls": letter, "flux": flux,
                    "noaa_ar": to_noaa(reg) if reg is not None else pd.NA,
                    "obs": tok[i - 2] if i >= 2 else ""})
    return out


def load(lo, hi):
    """All XRA flares with begin in [lo, hi], deduplicated. Returns (flares, n_duplicates)."""
    days = pd.date_range(pd.Timestamp(lo).normalize(), pd.Timestamp(hi).normalize(), freq="D")
    rows = [e for d in days for e in parse_day(d)]
    fl = pd.DataFrame(rows, columns=["start", "goes_class", "cls", "flux", "noaa_ar", "obs"])
    fl = fl[(fl["start"] >= pd.Timestamp(lo)) & (fl["start"] <= pd.Timestamp(hi))]
    n0 = len(fl)
    # dedup on (begin, class); if one copy has a region and the other doesn't, keep the region
    fl = (fl.sort_values("noaa_ar", na_position="last")
            .drop_duplicates(subset=["start", "goes_class"]).sort_values("start"))
    return fl.reset_index(drop=True), n0 - len(fl)


def fetch(lo, hi, verbose=True):
    """Same interface as flares.fetch: (joinable flares, joinable M1+), unknown M1+ on attrs."""
    fl, n_dup = load(lo, hi)
    unknown = fl["noaa_ar"].isna()
    n_unknown_m1 = int((unknown & (fl["flux"] >= 1e-5)).sum())
    fl = fl[~unknown].copy()
    fl["noaa_ar"] = fl["noaa_ar"].astype(int)
    m1 = fl[fl["flux"] >= 1e-5].copy()
    m1.attrs["n_unknown_m1"] = n_unknown_m1
    if verbose:
        miss = sorted(d for d in missing_days()
                      if pd.Timestamp(lo).normalize() <= pd.Timestamp(d) <= pd.Timestamp(hi))
        print(f"source: SWPC original event reports ({CACHE})")
        print(f"flares (XRA) in window: {len(fl) + int(unknown.sum())}")
        print(f"duplicates removed: {n_dup}  (on begin time, GOES class)")
        print(f"UNKNOWN region (blank Reg#), not joined: {int(unknown.sum())}  (of which M1+: {n_unknown_m1})")
        print(f"joinable: {len(fl)};  M1+ retained: {len(m1)}")
        print(f"days with no SWPC report in window: {len(miss)} {miss[:5]}")
        print("class counts:", fl["cls"].value_counts().to_dict())
    return fl, m1
