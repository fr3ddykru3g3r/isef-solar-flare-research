# Decisions

## 2026-09-21 — initial dataset build (January 2014)

- **Hourly sampling via JSOC `@1h`**: the query `hmi.sharp_cea_720s[][...@1h]` returns records
  that exist at hourly slots. No interpolation. 10145 of 10268 expected hourly records present
  (123 missing, counted per-HARP over each HARP's own first→last span).
- **TAI→UTC with astropy**: `Time(..., scale="tai").utc`. The `_TAI` suffix is never just stripped.
  `2014.01.01_00:00:00_TAI` = `2013-12-31 23:59:25 UTC` (35 s). Both columns stored; all window
  comparisons in UTC.
- **Flare catalogue**: HEK, `frm_name = SWPC` only — one operational catalogue, no cross-pipeline
  duplicates of the same physical flare. 193 retrieved, 0 duplicates on
  (start_time, noaa_ar, goes_class), 30 M1+ after local numeric parsing.
- **Broad fetch, local filter**: GOES class parsed to a numeric flux (`M1.5 → 1.5e-5`) in Python
  and thresholded at `>= 1e-5`. No catalogue-side `GOESCls > "M1.0"` — string comparison there
  mishandles the boundary.
- **Padded window**: first SHARP time − 48 h to last + 24 h, so the prev-48h and next-24h windows
  are complete at both edges.
- **NOAA mapping**: `NOAA_ARS` parsed into a list → status single / multiple / missing.
  Missing rows kept in the raw CSV, excluded from the labelled CSV (2473 rows dropped):
  blank means "association unknown", not "no flare"; labelling them 0 injects false negatives.
- **Multi-region HARPs (ANY rule)**: positive if *any* associated NOAA region flares; previous
  counts are the deduplicated union over associated regions. Dropping them would systematically
  remove the most magnetically complex patches.
- **Windows (half-open)**: `next24 = (t, t+24h]`, `prev48 = [t-48h, t)`.
- **Missing values**: `drms` already returns JSOC MISSING as NaN for float keywords, so no
  magnitude-based sentinel mask is applied — USFLUX/TOTPOT are legitimately ~1e22. Reported only;
  no filling or dropping (modelling decision, deferred).
- **Date range is a parameter**: `python build_dataset.py START END`, defaults 2014-01-01 2014-02-01.

## 2026-09-21 — verification session

### Part 1 — date discrepancy (RESOLVED, no bug)
`build_dataset.py 2014-02-01 2014-03-01` produces
`hmi.sharp_cea_720s[][2014.02.01_TAI-2014.03.01_TAI@1h]` — reproduced directly.
The January query string reported came from a **no-argument** run, which uses the
defaults `2014-01-01 2014-02-01`. No offset, no stale string, argument order is (START, END).
Mitigations added so this can never be ambiguous again:
- every run prints a banner with `argv`, the parsed CLI dates, the JSOC date literals and the
  full record-set string, *before* querying;
- dates are validated with `strptime`, `START < END` is enforced, and a wrong argument count
  exits with a usage message instead of silently falling back to the defaults.
- START is inclusive, END is exclusive.
- SWPC flare fetching moved to `flares.py` so `checks.py` and `build_dataset.py` cannot drift apart.

### Part 2 — sanity checks (`checks.py`, all PASS, January 2014)
- **CHECK 1 PASS** — X1.2 at 2014-01-07 18:04 UTC, NOAA 11944 → HARP 3563. All 21 rows present in
  `[t0-24h, t0)` are labelled 1; the first rows after t0 are 0. 7 of the 11 rows earlier than
  t0−24h are also 1, correctly, because other M1+ flares from 11944 fall inside *their* windows.
  The visible gaps (−25.1h → −22.1h, −13.1h → −11.1h) are genuinely absent hourly records, not
  dropped joins — consistent with the 123 missing hours reported for January.
- **CHECK 2 PASS** — median USFLUX 4.02e22 (positive) vs 5.76e21 (negative), **6.98×**;
  median TOTUSJH 3040 vs 412, **7.39×**. Distributions separate in the expected direction.
- **CHECK 3** — 2715 rows but only **23 distinct HARPNUMs**, 5 of which contain a positive row.
  Rows per HARP: mean 118, median 141, min 21, max 178. The effective independent sample size is
  the number of regions, not the number of rows; any train/test split must be grouped by HARPNUM.
- **CHECK 4 PASS** — missing-mapping rows have median USFLUX 1.63e20 vs 5.91e21 for mapped rows
  (**0.028×**), and **0.0%** of them exceed the mapped median. They are minor patches that never
  received a NOAA designation. Excluding them is not discarding real data.
