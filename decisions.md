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

## 2026-09-21 — flare/HARP join defect, and the decisions taken because of it

### The defect (found by me, mid-run)
Whole years were producing zero M1+ positives while raw SHARP row counts were *rising*
(2021-12: 0 positives from 2307 rows; 2022-01: 0 from 1790; 2022-03: 0 from 1538). A genuine
solar-minimum zero comes with *low* row counts, so this was the opposite signature.

Cause: HEK returns the flares, but with `ar_noaanum = 0`. March 2022 — 258 SWPC flares, of which
**246 carry no usable region number**; every M1+ flare that month has `ar_noaanum = 0`. The code
dropped flares whose region was *NaN*, but `0` is a valid integer: it survived, joined against
NOAA region "0", matched no HARP, and emitted a clean, silent `0` label. False negatives, not
quiet Sun.

January 2014 is unaffected (27 M1+ with real region numbers), which is exactly why CHECK 1–4 all
passed. **CHECK 1 structurally could not catch this** — it only exercises a month where the join
works. That is the lesson: a check that samples one good month certifies nothing about the rest.

### Decisions

**1. `ar_noaanum <= 0` or NaN = UNKNOWN region; never joined.  (decided by: user, approved 2026-09-21)**
Reason: same principle already agreed for `noaa_mapping_status = "missing"` — absence of an
association is not evidence of absence of a flare. Joining or zero-labelling them injects false
negatives. They are excluded from the join and *counted* per year instead.
Consequence: these are label noise (missed positives) even in years that pass the threshold, so
the count is reported per year, not just per failing year.
Implementation: `flares.py`; the unknown M1+ count is computed *before* the drop and carried on
`m1.attrs["n_unknown_m1"]`.

**2. Usable-year threshold: >= 90% of M1+ flares must carry a usable region number.
   (decided by: user; fixed 2026-09-21 BEFORE any per-year results were seen)**
Reason: pre-registering the threshold prevents fitting it to whatever the data turned out to be.
**No catalogue-source switch, and no mixing of catalogue methods across years** — the train/test
split is chronological, so a per-year method change would confound period with method.
Table: PENDING: per-year join report (`data/join_report.csv`, running).

**3. Flare catalogue stays SWPC via HEK.  (decided by: user)**
No source switch while the join defect is being characterised. SWAN-SF is to be used as a
**cross-check only**, not as a label source. A check against the original SWPC event lists is
**PENDING** — not yet specified or run; nothing in this repo depends on it yet.

**4. `QUALITY == 0` stays.  (decided by: user; I asked, having found whole months excluded)**
May 2016: all 4907 raw records carry bit `0x00000080` = `QUAL_TEMPERROR`, so the month yields
zero rows. What JSOC actually documents
(http://jsoc.stanford.edu/doc/data/hmi/Quality_Bits/QUALITY.notes, modified 2017-09-19), verbatim:
  "In cases where 45s or 720s data exists and there is a code error detected we will set bit 0x80
   for existing records while they are waiting replacement with reprocesed data."
It enumerates exactly one case: **Sept 2017** (CALVER64 / modL, pending reprocessing of
`hmi.S_720s`, "should not be visible once the reprocessing is done").
**No documented case covers May 2016**, and those records still carried `0x80` when queried on
2026-09-21 — so we have no JSOC statement that they were reprocessed, and none explaining the flag.
Correction to my earlier framing: I initially read the bit *name* as suggesting the data were
fine. That was wrong and the user corrected it. `0x80` is a flagged processing error; it is not
evidence about the underlying data in either direction. We do not infer quality from a bit name.
Bit meanings are quoted verbatim with their JSOC source in `quality_report.py`.
Table: PENDING: per-month QUALITY counts (`quality_report.py`, runs after the chunk run).

**5. CHECK 5 — per-year join coverage.  (decided by: user)**
Fails any year below the 90% threshold. M1+ only. Reports per year: M1+ retrieved,
M1+ with unknown region, % usable region, % joining >= 1 HARP, positive rows, distinct positive
HARPs. The last two are for the user to fix the train/val/test split before any model is trained.
Reuses `join_report.build()` rather than duplicating the logic.
Table: PENDING: same as decision 2.

### Implementation choices (decided by: me — mechanical, no science content)
- **Empty-frame guards.** Two crashes, both legitimate-empty rather than buggy:
  (a) May 2016 — every record fails `QUALITY == 0`, so `df.apply` on an empty frame returned no
  columns; (b) Nov 2019 — deep solar minimum, HEK returned *zero* SWPC events, so the result table
  had no columns at all. Both now yield an empty/zero-label chunk, which is the correct answer.
  Neither guard changes any filter or window.
- **Retry on transient errors only** (`run_all.py`): timeouts, connection resets, 502/503 —
  5 attempts, 60s * attempt backoff. Hard errors still abort immediately, so real bugs are not
  papered over by retries. Added after four JSOC interruptions on the 2020-12 chunk alone.
- **Bug fixed while reporting:** the "duplicates removed" line was conflating deduplication with
  the unknown-region drops (it read 246 for March 2022, when 0 were duplicates). Counted separately now.
- **Bug fixed after the user's note:** once `fetch` began dropping unknown-region flares, the join
  report would have counted zero unknowns for every year — showing 100% usable everywhere and
  passing CHECK 5 silently. Caught only because the user asked for the unknown count per usable
  year. The count is now taken before the drop.
- **Date banner / CLI validation** (earlier today, see previous entry) — kept.

### Not yet done
- PENDING: per-year join table (decisions 2 and 5)
- PENDING: per-month QUALITY table (decision 4)
- PENDING: SWPC originals cross-check (decision 3)
- No relabelling has been run. Raw SHARP chunk files are unaffected by any of this and remain
  valid; only the labelled files for low-coverage years are suspect.

## 2026-09-21 — flare source switched to SWPC originals; multi-region and missing-day rules

### Evidence that prompted the switch (found by me; `swpc_check.py`)
HEK copies SWPC's catalogue but loses region numbers that SWPC recorded:

| month   | M1+ SWPC / HEK | matched (time+class) | SWPC has Reg# | HEK usable region | region agrees |
|---------|----------------|----------------------|---------------|-------------------|---------------|
| 2014-03 | 23 / 23        | 23                   | 23            | 23                | 23 / 23       |
| 2022-03 | 14 / 14        | 14                   | 13            | **0**             | **0 / 14**    |

The events are the same flares; only the region field is lost, and only in HEK.

### Decision A — flare labels from SWPC original daily event reports, ALL years 2010–2024
**(decided by: user, 2026-09-21)**
Reason: it is the same catalogue HEK copies, and it keeps the region numbers HEK drops in later
years. **One source for the whole range, never switched per year** — the split is chronological,
so a per-year source change would confound period with catalogue.
Source: NCEI archive of SWPC "Edited Events",
`https://www.ngdc.noaa.gov/stp/space-weather/swpc-products/daily_reports/solar_event_reports/`.
Rules (`swpc.py`, identical for every year):
- XRA lines only; begin time = Begin column on the report date, UTC.
- **Region: one explicit rule, `Reg# < 10000 -> Reg# + 10000`**, nothing else. Blank Reg# = unknown,
  never joined (same principle as decision 1 of the previous entry).
- **Dedup on (begin time, GOES class)**, logged per year — guards against one flare listed from two
  GOES satellites (e.g. G16 and G18). If one copy has a region and the other doesn't, the copy with
  the region is kept.
- The HEK-based labels are **kept** in `data/labels_hek/` for comparison, not deleted.
Preconditions set by the user before relabelling:
1. Validation, SWPC vs HEK: flares, times, class, region, one month per year 2011–2019.
   Sample fixed in advance by me: **March of each year**. Reported **all-class**, and **M1+-only**
   where there are enough events. PENDING: validation table.
2. % of converted SWPC regions found in SHARP `NOAA_ARS` for the same period. PENDING: table.
3. Dedup removals per year. PENDING: table.
Then: relabel all 176 chunks from cached raw (no JSOC re-download), rerun checks 1–5 against the
SWPC source with the **same 90% threshold**, regenerate the per-year table.
PENDING: post-relabel per-year table.

Regression evidence that relabelling from cache is faithful (me): with `FLARE_SOURCE=hek`,
labels regenerated from the cached raw files are **byte-identical** to the original HEK labels for
2014-01 and 2019-11 (the latter has only single-region mappings, the case where `NOAA_ARS` could
otherwise read back from CSV as a float and silently lose its region). A first run of this test
falsely "passed" because the run crashed and I compared the archive with itself; the test now
deletes its output first, so a crash cannot pass.

### Decision B — multi-region HARPs  (decided by: user, 2026-09-21)
Prompted by the 2024 audit: 80% of 2024 positive rows (3,656 / 4,596) came from multi-region HARPs;
positive rate 4.51% on single-region rows vs 31.5% on multi-region rows; HARPs of up to 11 NOAA
regions; mean regions per multi-region HARP 3.79 in 2024 vs 2.0–2.8 in 2010–2022. Under the ANY rule
an 11-region patch is positive whenever any one of its regions flares.
- **Primary analysis: single-region HARPs only (`noaa_ar_count == 1`).**
- **Robustness: repeat with the ANY rule on all HARPs.**
- **Fallback, fixed now before results: if single-region gives < 40 positive HARPs in the candidate
  test years, use `noaa_ar_count <= 2` instead.**
- **The dataset is NOT filtered.** A `region_group` column ("1", "2", "3+") is added so every analysis
  selects its own subset from one file.
Note (me): the fallback depends on "candidate test years", which are not chosen yet. The per-year
counts below are reported for all three groups so the fallback can be evaluated once the split is
fixed; it cannot be evaluated before then.
PENDING: per year, rows / positives / positive HARPs for (a) single-region, (b) <= 2, (c) all.

### Decision C — days with no SWPC report  (decided by: user, 2026-09-21)
**Any row whose 24h label window `(t, t+24h]` overlaps a day with no SWPC report gets label =
unknown and is excluded from the labelled file.** Count reported per year.
Reason: a missing report means "flares unknown", not "no flares"; labelling those rows 0 would be
false negatives — same principle as the missing-mapping and unknown-region rules.
Implementation (me): a missing day is one the NCEI archive returns 404 for (listed in
`data/swpc_events/_missing_days.txt`). Excluded rows are written to
`data/excluded_missing_swpc_<chunk>.csv` so the exclusion is auditable, not silent.
Note (me): the rule as specified covers the forward 24h label window. The backward 48h window
(`n_*_prev_48h` features) can also overlap a missing day, which would *undercount* prior flares.
That is a feature, not a label, and I have not changed it — flagged for your decision.
PENDING: excluded rows per year.

## 2026-09-21 — fallback timing, and incomplete flare history  (decided by: user)

**Fallback (Decision B).** Applied by the user when choosing the split, from the per-year
`region_group` counts, **before any model is trained**. Not applied in this dataset build.

**Decision D — `history_incomplete` column.**
`history_incomplete = True` if the backward window `(t-48h, t]` overlaps a day with no SWPC report.
In those rows `n_flares_prev_48h` and `n_C/M/X_prev_48h` may be undercounted.
- **Rows are kept** — they remain usable for **gate training on SHARP features only**.
- **Excluded from the cohort analysis**, because flare history is its mandatory control.
Reason: a missing report makes the history unknown, not zero; keeping the SHARP features avoids
throwing away magnetic data that is unaffected.
Implementation (me): overlap of `(t-48h, t]` with day `[D, D+1d)` is `t-48h < D+1d and t >= D`.
The counting window itself is `[t-48h, t)`; the two differ only when `t` falls exactly on midnight,
which cannot happen here (hourly `T_REC` converts to `hh:59:2x` UTC), so the flag and the counts
cover the same span. HEK comparison labels carry `history_incomplete = False` — the missing-day
rules apply to the SWPC source only.
PENDING: `history_incomplete` rows per year.

## 2026-09-21 — validation verdict; empty SWPC reports resolved with GOES XRS  (decided by: user)

### Validation: PASS — SWPC original event reports are the label source
March 2011–2019, SWPC vs HEK (`validate_swpc.py`, sample fixed in advance):
- 1,281 of 1,285 SWPC events matched HEK on begin time; **class agreement 100%** on matched pairs.
- **Region agreement: 1 disagreement in ~1,100** pairs (2011-03-09 C5.0: SWPC 11169, HEK 11165).
- **M1+-only** (months with >= 5 SWPC M1+ — fixed in advance): 2011, 2012, 2014, 2015 → 96 of 97
  matched, class and region 100% on matched.
- 0 duplicates removed in every sampled month.
- Found in passing (me): the same flare can carry different begin times in the two catalogues
  (2015-03-02 M1.1 AR 12290: 08:52 HEK vs 09:37 SWPC; 2012-03-29 C7.7: 72 min; 2013-03-10 B6.7: 1 h).
  Rare, but exactly what flips a label at the 24h edge. SWPC's time is used, consistently.
- 2014-03: 3 flares where SWPC has a region and HEK does not — HEK's region loss predates 2020.

### The gap found during validation (me)
The NCEI archive has a file for **every** day 2010-04-29 → 2025-01-02 (5,363 files, **0 × 404**), so
decisions C and D as first implemented would exclude nothing. But many files read only
`NO EVENT REPORTS.` — 39 (2010), 2 each (2011–13), 25 (2016), 79 (2017), 196 (2018), 236 (2019),
193 (2020), 61 (2021). Some are genuinely quiet; **2017-03-14 is empty in SWPC while HEK lists 32
flares.** The file alone cannot distinguish "no flares" from "report not compiled".
I offered three options; **the user rejected all three** (genuine-zero, all-missing, HEK-flagged).

### Decision E — GOES XRS 1–8 Å flux decides what an empty-report day means
For each empty-report day, take the **GOES XRS 1–8 Å daily maximum, 1-minute data, primary
satellite**:
- **max >= 1e-5 W/m² (M1)** → day is **MISSING for labels**: exclude rows whose `(t, t+24h]`
  overlaps it (decision C, now driven by this rule).
- **max >= 1e-6 W/m² (C1)** → day is **incomplete for history**: `history_incomplete = True` for rows
  whose `(t-48h, t]` overlaps it (decision D, now driven by this rule).
- **otherwise** → **genuine zero**: the day is quiet and the empty report is trusted.
Reason: the X-ray flux is the physical measurement flare classes are defined from, so it answers
directly whether a flare of the relevant class could have been missed — independent of any
catalogue. It does not depend on HEK.
Note (me): an M1 day is also a C1 day, so it sets both flags.
PENDING: per year — empty days, days flagged missing (M1), days flagged incomplete (C1).

### Decision F — history control is C/M/X only
`n_B` is **not** a history feature; the flare-history control uses `n_C_prev_48h`, `n_M_prev_48h`,
`n_X_prev_48h` only. (`n_flares_prev_48h` still counts all classes — see note.)
Note (me): the labelled file has never had an `n_B_prev_48h` column; B flares only entered
through the all-class total `n_flares_prev_48h`. Flagged for the user: if the total should also
exclude B, that is a change to a feature definition, and I have not made it.

### Decision G — HEK stays cross-check only
HEK flare counts on SWPC-empty days are reported **as a sanity check against the GOES rule**, never
used to flag days or set labels. PENDING: HEK-on-empty-days vs GOES-rule comparison.

Then: relabel all 176 chunks. PENDING: post-relabel tables.

## 2026-09-21 — GOES data gaps and the flare-history control  (decided by: user)

Context (me): testing the GOES rule on 2017-03-14 (SWPC report empty, HEK lists 32 flares at
B2–B5) — GOES-15 and GOES-16 both show an A-level day (max 1.9e-8 and 2.6e-8 W/m², all minutes,
flagged or not), ~10x below B2. The SWPC empty report was correct; HEK's entries for that day do
not correspond to anything in the X-ray flux. First direct evidence that HEK, used as the
cross-check, can be wrong in the opposite direction from the gap it was meant to catch.

**Decision H — no primary GOES data on a day.** Fall back to the **secondary** satellite
(Table 11, secondary column). If **neither** has data, the day is **missing**: label exclusion
**and** `history_incomplete`.

**Decision I — partial coverage.** Primary gaps are **filled with secondary `good_data` minutes**.
If combined coverage is **< 90% of the day AND the day would otherwise be "genuine zero"**, the day
is **missing** (label exclusion + `history_incomplete`). Days reaching M1 or C1 on partial data keep
that classification — a flare seen in part of a day is still a flare.
Reason: a quiet reading over part of a day cannot rule out a flare in the unseen part; a flare
reading over part of a day already establishes one.
PENDING: coverage distribution, and how many days this rule flags.

**Decision J — `n_flares_prev_48h`.** **Kept in the file, excluded from all analysis.** The flare
history control is **`n_C_prev_48h`, `n_M_prev_48h`, `n_X_prev_48h` only.**
Reason: the total includes B flares, which decision F removed from the history control. Keeping the
column preserves the raw count; excluding it keeps B out of every analysis.

Implementation (me): the secondary column of Table 11 is transcribed alongside the primary; minutes
are combined per UTC minute (primary where good, else secondary where good), so a minute is never
counted twice.

## 2026-09-21 — RESULTS: GOES empty-day table and HEK sanity check (fills PENDING for E, H, I, G)

`goes_xrs.py` → `data/goes_empty_days.csv`; 835 empty-report days, 1,510 GOES files.
**No empty-report day reaches M1** — no M1+ flare is hidden behind an empty SWPC report in 2010–2024.

| year | empty | genuine zero | incomplete C1 | missing: no data (H) | missing: low cov (I) | label-missing | history-incomplete |
|------|------:|-----:|---:|---:|---:|---:|---:|
| 2010 |  39 |  34 | 0 | 5 | 0 | 5 | 5 |
| 2011 |   2 |   2 | 0 | 0 | 0 | 0 | 0 |
| 2012 |   2 |   1 | 1 | 0 | 0 | 0 | 1 |
| 2013 |   2 |   2 | 0 | 0 | 0 | 0 | 0 |
| 2016 |  25 |  24 | 0 | 0 | 1 | 1 | 1 |
| 2017 |  79 |  78 | 1 | 0 | 0 | 0 | 1 |
| 2018 | 196 | 195 | 0 | 0 | 1 | 1 | 1 |
| 2019 | 236 | 235 | 0 | 0 | 1 | 1 | 1 |
| 2020 | 193 | 192 | 1 | 0 | 0 | 0 | 1 |
| 2021 |  61 |  61 | 0 | 0 | 0 | 0 | 0 |
| **all** | **835** | **824** | **3** | **5** | **3** | **8** | **11** |

- **H (no data):** 2010-06-15, 08-22, 08-23, 12-18, 12-25 — all inside 2010 windows where Table 11 lists
  **no secondary satellite**, so no fallback existed.
- **I (coverage):** 27 days had primary coverage < 90%; the secondary fill brought 19 above 90%, leaving 8
  (the 5 above + 2016-09-12 at 89.9%, 2018-07-27 at 38.0%, 2019-09-25 at 87.6% — all quiet, so missing).
  Coverage distribution: 756 days >= 99%, 49 at 95–99%, 22 at 90–95%, 2 at 80–90%, 6 below 50%.
- **C1 days:** 2012-01-29, 2017-07-20, 2020-09-26.

**HEK sanity check (decision G):** HEK lists flares on only 3 empty days (2017-03-08, 03-09, 03-14),
45 B-class, 0 C, 0 M1+. On all three GOES has 100% coverage and daily maxima 9.6e-8, 7.1e-8, 2.6e-8 —
**all below B1.0**, so HEK's B2–B5 entries are inconsistent with the measured flux. Conversely, GOES
finds C1+ on 3 days where HEK lists nothing. The two agree on the result that matters (0 M1+ on
empty days); where they disagree, the X-ray flux shows HEK is wrong. Supports keeping HEK
cross-check only.

## 2026-09-21 — OPEN: SWPC flare-class scale changes at end of 2019 (found by me; awaiting user)
NCEI readme §3.1: pre-GOES-16 operational fluxes carried SWPC scaling factors (0.7 for XRS-B) that
the science data removes; "flare indices for the operational data were reported as 42% (1.0/0.7)
smaller than for the science GOES 13-15 and GOES-R data". SWPC's own `Obs` column shows its XRA events
came from **GOES-13/14/15 through 2019-11** and **GOES-16/18 from 2019-12**. So "SWPC class >= M1.0"
means **1.43e-5 W/m² true flux before 2019-12 and 1.0e-5 after** — a 30% drop in the label threshold
across the chronological split. (Table 11's GOES-16 primary date, 2017-02-07, is for science data,
not SWPC's operational source.)
Not affected: decision E — no empty day reached even 1.0e-5, so the result above holds on either scale.
Options put to the user: (a) harmonise to true irradiance per event from its `Obs` satellite
[recommended by me]; (b) harmonise to the old scale; (c) leave as reported.
**Relabel is on hold until decided.**

## 2026-09-21 — Decision K: flare-class scale harmonised to the OLD operational scale  (decided by: user)

Resolves the open item above. **Option (b).**
Reason (user): comparability with Bobra & Couvidat (2015), SWAN-SF, and published SWPC forecast
verification, all of which use the old operational scale for 2010–2019.

- **SWPC events from GOES-16/17/18/19 (per each event's `Obs` column): flux × 0.7 before classifying.**
  Events from GOES-13/14/15 are used **as reported**. The satellite is read per event, never inferred
  from the date.
- **Applies to labels AND to the `n_C/M/X_prev_48h` history features** — one scale for everything.
- **GOES science-flux thresholds (true flux), all years:** **M1 = 1.43e-5 W/m², C1 = 1.43e-6 W/m²** —
  used by decision E (empty-day rule) and by the March 2011–2019 completeness check.
  Empty-day C1 flags re-derived at 1.43e-6.
- **Report per year how many events changed class under the conversion.**

Implementation notes (me):
- The reported class and flux are kept alongside the harmonised ones (`goes_class_reported`,
  `flux_reported`), so the conversion is auditable per event.
- Dedup stays on (begin time, **reported** class), as specified earlier — dedup identifies the same
  physical listing, which is a property of the report, not of the scale.
- Consequence worth knowing: on the harmonised scale a GOES-16/18-era event needs a reported class of
  **>= M1.5** to be M1+ (M1.4 × 0.7 = 9.8e-6 = C9.8; M1.5 × 0.7 = 1.05e-5 = M1.0). The same applies
  at the C1 boundary for history counts.
- The thresholds are used exactly as given (1.43e-5, 1.43e-6); 1e-5/0.7 = 1.4286e-5, so the given
  value is 0.1% above the exact conversion. Stated for completeness; no effect on any class boundary,
  since SWPC reports one decimal place.

## 2026-09-21 — RESULTS: relabel on SWPC originals, old operational scale (fills PENDING for A, B, C, D, K)

All 176 chunks relabelled from cached raw SHARP (no JSOC re-download). HEK-era labels kept in
`data/labels_hek/`.

**Scale conversion (decision K), per year** (`data/scale_conversion_report.csv`): 2010–2018 no events
converted (all GOES-13/14/15). Converted from GOES-16/18 and class changes:
2019: 3 / 0 · 2020: 550 / 121 · 2021: 2,064 / 470 · 2022: 3,131 / 590 · 2023: 3,213 / 434 ·
2024: 3,765 / 494. M1+ as reported → harmonised: 2020 2→1, 2021 29→16, 2022 195→117,
2023 365→202, **2024 935→545** (−42%). Part of the late-period rise in positives was the scale.
Also: 5 XRA events attributed to `SDO` (none M1+) kept as reported, counted `scale_unverified`
(decision K does not cover them); 2 events with impossible begin times skipped (all B-class, 2020).

**Empty-day flags at decision-K thresholds:** 2 days moved C1 → genuine zero (2012-01-29,
2020-09-26; peaks between 1.0e-6 and 1.43e-6). Final: 8 label-missing, 9 history-incomplete days.
Max peak on any empty day: 1.95e-6.

**Whole range:** 255,292 labelled rows (255,460 before the missing-day rule; −168), **10,146 positives
(3.97%)**, 2,053 HARPs, 254 with a positive.

**Missing-day rules (C, D), per year:** excluded — 2010: 168, all other years 0.
history_incomplete — 2010: 224, 2017: 56 (the 2017-07-20 C1 day), all other years 0.
The 3 low-coverage missing days (2016-09-12, 2018-07-27, 2019-09-25) exclude 0 rows because no labelled
row lies within 24h/48h of them — verified against the pre-exclusion row set. The 2017-07-20 C1 day
keeps its 14 label-window rows, as specified (C1 marks history incomplete, not the label missing).

**Per year, region subsets (decision B)** — rows / positives / positive HARPs:

| year | single (primary) | <= 2 (fallback) | all (robustness) |
|------|------------------|-----------------|------------------|
| 2010 |  7,134 /  61 /  3 |  7,805 /    81 /  4 |  7,805 /    81 /  4 |
| 2011 | 17,311 / 484 / 10 | 21,996 /   657 / 17 | 23,915 /   747 / 22 |
| 2012 | 17,008 / 183 /  6 | 21,703 /   485 / 14 | 23,100 /   781 / 21 |
| 2013 | 21,924 / 454 / 17 | 25,711 /   602 / 23 | 28,024 /   790 / 29 |
| 2014 | 17,215 / 568 / 13 | 21,819 /   761 / 17 | 25,475 / 1,273 / 30 |
| 2015 | 19,555 / 569 / 12 | 22,973 /   618 / 15 | 24,421 /   715 / 17 |
| 2016 |  4,637 /   0 /  0 |  5,200 /    67 /  1 |  5,329 /    67 /  1 |
| 2017 |  4,784 / 124 /  3 |  5,233 /   124 /  3 |  5,233 /   124 /  3 |
| 2018 |  3,472 /   0 /  0 |  3,472 /     0 /  0 |  3,472 /     0 /  0 |
| 2019 |  2,128 /   0 /  0 |  2,128 /     0 /  0 |  2,128 /     0 /  0 |
| 2020 |  4,240 /   0 /  0 |  4,331 /     0 /  0 |  4,481 /     0 /  0 |
| 2021 | 10,940 / 134 /  5 | 11,958 /   156 /  6 | 12,386 /   178 /  7 |
| 2022 | 18,536 / 246 /  9 | 22,218 /   453 / 15 | 24,685 /   695 / 20 |
| 2023 | 21,659 / 420 / 15 | 27,080 /   772 / 25 | 32,367 / 1,337 / 44 |
| 2024 | 20,863 / 666 / 16 | 25,725 / 1,307 / 27 | 32,471 / 3,358 / 57 |

Positive rate, all rows: 2014 5.00%, 2024 10.34% (was 14.15% on HEK before harmonisation).

**Checks on SWPC (January 2014 file for 1–4):**
- CHECK 1 PASS — X1.2 2014-01-07 18:04, NOAA 11944 → HARP 3563; all 21 rows in [t0−24h, t0) = 1.
- CHECK 2 PASS — median USFLUX positive/negative **12.87×** (HEK: 6.98×), TOTUSJH **15.87×** (HEK: 7.39×).
- CHECK 3 — 23 HARPs, 5 with a positive (descriptive).
- CHECK 4 PASS — unchanged (does not depend on flare source).
- **CHECK 5 FAIL — 2020 only.** 2020 has exactly **1** M1+ flare (harmonised) and SWPC gives it no region:
  0 of 1 usable → below the pre-registered 90%. Reported as a FAIL; the rule was not changed.
  Maximum label cost: one missed positive episode in a year that is otherwise all zeros.
  Whether a percentage threshold should apply to a one-flare year is the user's decision.
  All other years with M1+ flares pass (2021 100%, 2022 90.6%, 2023 97.5%, 2024 96.0%).

**Per-year join table (SWPC)** (`data/join_report_swpc.csv`): %usable 93.8–100% in every year with
>= 8 M1+ flares; `%in_SHARP` 100% except 2014 (91.7%: 16 M1+ flares with a region no HARP contains)
and 2024 (99.6%); dups removed per year 0–5.

## 2026-09-21 — RESULT: completeness check, GOES M1+ peaks vs SWPC (report only; no label changes)

`completeness_check.py`, March 2011–2019. Rules fixed before running (me): a GOES M1+ peak is a run of
good minutes >= 1.43e-5 W/m² true flux (old-scale M1, decision K), primary with secondary fill; runs
<= 5 min apart are merged; a match is an SWPC harmonised M1+ event whose peak (begin if peak missing)
is within ±30 min.

| month | GOES M1+ peaks | matched | unmatched | SWPC M1+ | GOES coverage |
|-------|---:|---:|---:|---:|---:|
| 2011-03 | 24 | 22 | 2 | 22 | 94.6% |
| 2012-03 | 21 | 21 | 0 | 22 | 86.3% |
| 2013-03 |  3 |  3 | 0 |  3 | 87.5% |
| 2014-03 | 22 | 22 | 0 | 23 | 94.4% |
| 2015-03 | 29 | 29 | 0 | 29 | 97.9% |
| 2016–2019-03 | 0 | 0 | 0 | 0 | 95.8–100% |
| **total** | **99** | **97** | **2** | | |

The 2 unmatched peaks (2011-03-08 21:41 and 22:23, both old-scale M1.0) lie on the decay of SWPC's
M1.4 in AR 11165 (begin 19:46, peak 20:16, end 21:19): the old-scale flux drifts from 1.36e-5 at 20:30
to ~9e-6 by 22:00 and re-crosses the threshold twice, > 5 min after the previous crossing. My merge rule
split one decay into extra "peaks"; SWPC treats it as one event. **Interpretation (me): no distinct GOES
M1+ flare is missing from SWPC in this sample.** Caveat: 2012-03 and 2013-03 have 86–88% GOES coverage;
a peak inside a gap where neither satellite has data is invisible to this check.

## 2026-09-21 — Decisions L, M, N  (decided by: user)

**L. 2020 excluded entirely.** It fails CHECK 5 under the pre-registered rule (1 M1+ flare, no region,
0% usable). **The rule is unchanged**; the year is dropped rather than the threshold adjusted.

**M. Region rule, from the fallback test (decision B).** Positive HARPs, single-region, 2021–2024 =
5 + 9 + 15 + 16 = **45 >= 40**, so **primary = single-region** (`noaa_ar_count == 1`).
**Robustness = `<= 2` regions and all HARPs (ANY rule).** The fallback is not triggered.

**N. Split.**
- **Test = 2021–2024, untouched until final evaluation.**
- **Train + validation = 2010–2019.**
- **Validation = random 25% of the 2010–2019 HARPs, assigned at HARP level, fixed seed, stratified so
  it contains positive HARPs.**
- **Assert: no HARPNUM in more than one set.**
- Written to `data/split.csv` (HARPNUM → train / val / test), SHA-256 recorded below.
- **No model is trained** — waiting on the signed research plan.

### RESULT: split (decision N) — `make_split.py` → `data/split.csv` (moved to `frozen/split.csv`, see below)
**SHA-256 `f3ab4056dd7b123aa8116b5d76650ddd916805139ee262381f9a7ffda728d145`** (rerun reproduces it).
Seed 20260921. 2020 removed first: 255,292 → 250,811 rows (−4,481); 34 HARPs exist only in 2020 and
are not in the split. 2,019 HARPs: train 913, val 305, test 801.
**Assert passed: no HARPNUM in more than one set; every HARP assigned.** No HARP has rows in both
2010–2019 and 2021–2024 (asserted in code). One HARP spans 2020→2021: its 2020 rows are dropped, its
2021 rows are in test; its early-2021 `n_*_prev_48h` still count late-2020 flares — decision L drops
2020 *rows*, not 2020 flares from the catalogue.
Stratification (me, fixed before running): three HARP strata from 2010–2019 rows — positive in
single-region rows (64 HARPs → 16 val), positive only in multi-region rows (62 → 16), negative
(1,092 → 273); 25% of each, rounded. This guarantees primary-subset positives in validation, not only
ANY-rule positives.

| set | subset | rows | positive rows | HARPs | positive HARPs | positive rate |
|-----|--------|-----:|------:|----:|---:|------:|
| train | single |  87,115 | 1,862 | 742 |  48 | 2.14% |
| train | <= 2   | 103,553 | 2,608 | 860 |  71 | 2.52% |
| train | all    | 111,991 | 3,480 | 913 |  94 | 3.11% |
| val   | single |  28,053 |   581 | 244 |  16 | 2.07% |
| val   | <= 2   |  34,487 |   787 | 290 |  23 | 2.28% |
| val   | all    |  36,911 | 1,098 | 305 |  32 | 2.97% |
| test  | single |  71,998 | 1,466 | 605 |  45 | 2.04% |
| test  | <= 2   |  86,981 | 2,688 | 709 |  73 | 3.09% |
| test  | all    | 101,909 | 5,568 | 801 | 128 | 5.46% |

HARP counts differ across subsets because `noaa_ar_count` is per row: a HARP can be single-region in
some hours and multi-region in others, so it appears in every subset whose rows it has.
**No model trained.** Waiting on the signed research plan.

## 2026-09-21 — Decision N2: model selection by grouped CV  (decided by: user; before any model is trained)

- **Threshold and hyperparameters are chosen by grouped 5-fold cross-validation over ALL 2010–2019
  HARPs** — train and val from `split.csv` **pooled**.
- **Folds: GroupKFold on HARPNUM**, **stratified by the same three HARP strata** as the split
  (positive in single-region rows / positive only in multi-region rows / negative), **fixed seed**.
- **Decision threshold = the one maximising TSS on the pooled out-of-fold scores.**
- **`split.csv` test assignment is unchanged**: 2021–2024 stays untouched until final evaluation.
- **Not implemented yet** — waiting on the signed research plan.

Notes (me), recorded for when this is implemented; none changes the decision:
- Under N2 the `train` / `val` labels in `split.csv` no longer separate data used for selection;
  both feed the CV pool. The file (and its SHA-256 above) is left exactly as written, so the test
  assignment it certifies is unaffected.
- Seed: the decision says "fixed seed" without a value. Unless told otherwise I will use the split's
  seed, **20260921**, and record the per-fold HARP and positive-HARP counts before any fitting.
- Expected fold size for the primary subset: 64 single-region-positive HARPs in 2010–2019 → about
  13 per fold, so each fold's TSS rests on ~13 independent positive regions.
- Pooling out-of-fold scores to pick one threshold assumes the five fold models produce scores on a
  comparable scale. If the models are poorly calibrated relative to each other, the pooled
  threshold can differ from each fold's own optimum; worth reporting the per-fold optimal thresholds
  alongside the pooled one when this runs.

## 2026-09-21 — N2 details approved; decisions O, Q, R  (decided by: user; before any model is trained)

**N2 details (approved):**
- Seed **20260921**.
- **Per-fold optimal thresholds are reported alongside the pooled out-of-fold threshold.**
- **Test scores = mean of the 5 fold models' scores. No refit on the full 2010–2019 set.**

**Decision O — expand SHARP keywords to the Bobra & Couvidat (2015) feature set.**
List their features from the paper (arXiv:1411.1405); show which are missing from the current 8;
re-query **only the missing keywords** for the **existing rows** (same record set, same filters);
merge on HARPNUM + T_REC; **verify row counts and labels unchanged.** Data only.

**Decision Q (final) — the gate.**
**Primary gate = reproduction of the Bobra & Couvidat (2015) SVM with their feature set.**
SolarMonitor = optional robustness gate only. **No further gate changes.**

**Decision R — research question and analysis plan (supersedes P).**
Note (me): no decision P appears in this log. R is recorded as superseding a "P" that was not written
down here; if P was decided elsewhere, its content should be added for the record.

*Question:* does 24h magnetic evolution add information beyond current magnetic risk and recent flare
history for separating M1+ **true alarms** from **false alarms**?
- **Trends:** fitted 24h slope of **USFLUX** and **TOTUSJH**; window **strictly before** the alarm time;
  **relative slope = slope / window mean**; **require >= 18 of 24 hourly points, else exclude.**
- **Primary analysis:** within the alarm cohort, logistic model **(gate score + n_C, n_M, n_X)** vs the
  **same + the 2 trends**. Fit on 2010–2019 (grouped CV, per N2), **evaluate once on 2021–2024.**
  **Metric: held-out log-loss difference, region-level bootstrap 95% CI.**
- **Supporting:** score-matched pairs.
- **Exploratory:** delayed alarms = no M1+ in (t, t+24h] and >= 1 M1+ in (t+24h, t+48h];
  **complete follow-up required.**
- **Pre-stated: a wide or inconclusive CI is an expected possible outcome.**

Consistency with earlier decisions (me, no change made):
- The history control is n_C, n_M, n_X only (J); cohort rows with `history_incomplete = True` are
  excluded from this analysis (D).
- "Complete follow-up" for delayed alarms needs the (t+24h, t+48h] window free of label-missing days;
  the current missing-day rule (C) only checks (t, t+24h]. To be implemented as an extra condition
  for the exploratory analysis only — the labelled file is not changed.

## 2026-09-21 — Decision O: findings (me) — two items need a user decision

Source: Bobra & Couvidat (2015), arXiv:1411.1405, **Table 1** (25 SHARP parameters, F-score ranked);
§5.1: the SVM uses **the first 13** ("Included"), chosen where a cubic fit to TSS vs feature count peaks.

| B&C 13 (Included) | have | | B&C Discarded (12) | have |
|---|---|---|---|---|
| TOTUSJH  | yes | | MEANSHR | **yes** (in our 8, but B&C discard it) |
| TOTBSQ   | **not a JSOC keyword** | | MEANGAM | fetched |
| TOTPOT   | yes | | MEANGBT | fetched |
| TOTUSJZ  | fetched | | MEANGBZ | fetched |
| ABSNJZH  | yes | | MEANGBH | fetched |
| SAVNCPP  | yes | | MEANJZH | fetched |
| USFLUX   | yes | | TOTFY   | **not a JSOC keyword** |
| AREA_ACR | yes | | MEANJZD | fetched |
| TOTFZ    | **not a JSOC keyword** | | MEANALP | fetched |
| MEANPOT  | fetched | | TOTFX   | **not a JSOC keyword** |
| R_VALUE  | yes | | EPSY    | **not a JSOC keyword** |
| EPSZ     | **not a JSOC keyword** | | EPSX    | **not a JSOC keyword** |
| SHRGT45  | fetched | | | |

**Item 1 — BLOCKING for decision Q.** The 7 Lorentz-force parameters (TOTBSQ, TOTFX, TOTFY, TOTFZ,
EPSX, EPSY, EPSZ) are **not keywords in `hmi.sharp_cea_720s` or `hmi.sharp_720s`** (checked against the
live JSOC key lists, 2026-09-21). B&C describe them as adapted from Fisher et al. (2012); they are
computed from the vector-field image data. Three are in the 13-feature SVM set (TOTBSQ, TOTFZ, EPSZ).
Reproducing the 13-feature gate exactly therefore conflicts with the keyword-only constraint.
Options put to the user: (1) compute the 3 from image segments — faithful, breaks keyword-only, large
download; (2) reproduce with the **10 of 13** available as keywords and document the deviation;
(3) other. SWAN-SF carries the parameters but ends in 2018 (no 2021–2024 test coverage) and is
cross-check only. **No option acted on.**

**Item 2 — reproduction difference, flagged, not acted on.** B&C (§5) discard SHARP entries with
**QUALITY > 65536** (0x10000). This dataset keeps **QUALITY == 0** (user decision, retained after the
May 2016 finding). The gate will therefore be trained on a stricter subset than B&C used. Recorded so the
"reproduction" claim can state it; the filter is not changed.

**Done under O (data only):** the **10 missing keywords that exist** are being re-queried for the
existing record sets (`fetch_extra.py` → `data/raw_sharp_extra_<chunk>.csv`; original raw files
untouched), merged 1:1 on HARPNUM + T_REC with an assert. Pre-O labelled file SHA-256 (for the
"labels unchanged" check): `d69ecbc46f3150d149915178a5d533d80156f83372287c56b09e7d280a55f632`.
PENDING: fetch completion, row-count and label verification.

## 2026-09-21 — Decisions on P, the gate features, QUALITY, and git  (decided by: user)

**1. Decision P.** P was drafted but never sent; its content was superseded by R before adoption.
**R supersedes an unadopted draft P.** (Replaces my earlier note that P "was not written down here".)

**2. Lorentz-force features: option 2. Decision Q amended.**
Q now reads: **primary gate = Bobra & Couvidat-style SVM, 10 of 13 features; TOTBSQ, TOTFZ, EPSZ
unavailable as keywords.** ("Reproduction" is withdrawn as a description.)
**The gate uses exactly these 10 features and no others** — B&C Table 1 "Included" features that exist
as SHARP keywords, in Table 1 rank order:

  1. TOTUSJH   2. TOTPOT   3. TOTUSJZ   4. ABSNJZH   5. SAVNCPP
  6. USFLUX    7. AREA_ACR 8. MEANPOT   9. R_VALUE  10. SHRGT45

(B&C ranks 1, 3, 4, 5, 6, 7, 8, 10, 11, 13; ranks 2 TOTBSQ, 9 TOTFZ, 12 EPSZ unavailable.)
**Not in the gate:** MEANSHR and every other SHARP parameter, including B&C's 12 "Discarded".
The gate's test TSS will be reported against B&C's published TSS later, as a check.

**Correction (user, 2026-09-21):** the instruction's examples of features to exclude named R_VALUE and
AREA_ACR; **those examples were an error by the user**. The gate is **exactly the 10 listed above,
including R_VALUE and AREA_ACR.** (The conflict flag previously recorded here is withdrawn.)

**3. QUALITY: keep == 0.** Documented as a **stricter-than-B&C difference**: B&C (2015, §5) discard only
QUALITY > 65536 (0x10000); this dataset keeps QUALITY == 0. The gate is trained on a stricter subset.

**4. Git.**
- `data/` added to `.gitignore` and **removed from tracking** (`git rm -r --cached data`); **no files
  deleted on disk** (617 entries in `data/` before and after).
- **Frozen artefacts are tracked under `frozen/`:** `data/split.csv` → **`frozen/split.csv`**
  (SHA-256 unchanged: `f3ab4056dd7b123aa8116b5d76650ddd916805139ee262381f9a7ffda728d145`);
  `make_split.py` writes there. Future `frozen_spec.json` goes in `frozen/` too.
- **SHA-256 of the combined files at this point (post-relabel, pre-O merge):**
  - `data/labelled_20100501_20250101.csv`:
    `d69ecbc46f3150d149915178a5d533d80156f83372287c56b09e7d280a55f632`
  - `data/raw_sharp_20100501_20250101.csv`:
    `2a65e05ba070dec1aca9bad546ba4825503eff04deb56774b964b1e542a8b28f`
  The labelled hash will change when the decision-O keywords are merged (new columns); it will be
  re-recorded then, alongside the check that labels and row counts are unchanged.
- Note (me): `git rm --cached` does not remove files from **history**. Past commits still contain
  `data/`, including the 137 MB raw CSV, so pushing this repository to GitHub would still be rejected
  (100 MB file limit). Fixing that requires rewriting history (e.g. `git filter-repo`), which is
  destructive — not done; the user's call.

## 2026-09-21 — Repository policy, and the pre-registration exploratory run  (decided by: user)

**Git history is not rewritten.** Commit hashes cited in this log are the audit trail.
**137 MB raw CSV remains in history; repo is not to be pushed; a separate clean code-only repo will
be made if sharing is needed.** The repository stays local.

### Pre-registration exploratory run — `verification/` (AI-generated, run via Codex)
Recorded for transparency and for the **AI-use disclosure**. Not part of the final analysis.

- **What:** `verification/freeze.py` fits comparators and freezes predictions; `verification/evaluate.py`
  scores the frozen predictions under three views (row-mapped, per flare episode, first alert per
  episode) with a bootstrap (10,000 draws, seed 20260921). Models: `xgb_joint`
  (XGBClassifier, 300 trees, depth 4, lr 0.05, 5 seeds), `xgb_nohist`, `proxy_pastflare`
  (rule: any M/X flare in the previous 48h), `climatology` (constant).
- **Who / how:** AI-generated, run via **Codex**, concurrently with this session's chunk run. I (Claude)
  did not write or run it; my `git add -A` swept it into commits `fce77b9` and `82198fa`, which is how
  it entered the repository.
- **When (file mtimes, 2026-09-21):** `freeze.py` 01:27:53, `frozen.csv` 01:28:09, `evaluate.py` and the
  three tables 01:28:55 — while the chunk run had reached about April 2016, which is where the data stops.
- **Labels:** the **HEK-era** labels (since superseded by SWPC originals, decision A).
- **Features:** the original 8 SHARP keywords (**including MEANSHR**), LAT_FWT, LON_FWT, and
  **`n_flares_prev_48h`**, n_C/n_M/n_X_prev_48h — several since excluded (decisions J, Q).
- **Data period:** 2010-05-01 → 2016-04-13 (137,991 rows). **Chronological split:** fit 2010-05 → 2014-07,
  threshold 2014-07 → 2015-04, **score 2015-04 → 2016-04**.
- **Results were seen by the user.** Table 1 (score period, row-mapped TSS): xgb_joint 0.808,
  xgb_nohist 0.829, proxy_pastflare 0.495, climatology 0.000. Full tables in `verification/out/`.
- **Test set (2021–2024) not touched:** 0 rows from 2021–2024 in `frozen.csv` (verified).
- **Results are not used in the final analysis.** Note: the score period now lies inside the
  2010–2019 development pool used for grouped CV (N2), so these numbers are an earlier look at data
  that will be cross-validated on — disclosed here, test set unaffected.
- **Files (SHA-256):**
  - `verification/freeze.py` `e83033ae8bcd0c6080bee0a5d2087315029490e32395b58a0f723d2f548c4fc7`
  - `verification/evaluate.py` `91b7cb5ca60b1112aa45a50bf92494c1ade86466d1aa499da503ee319307ed6d`
  - `verification/out/frozen.csv` `041d7a6f964630ff629748ef7a4915773a2d1bb25d33bc9378283aa249a35710`
    — **untracked from git, kept on disk** (23 MB)
  - `verification/out/table1_views.csv` `936dd8a3c17048e4573e41b67b43b700eaa64d88d3443e28bee873e29ffdbb3c`
  - `verification/out/table2_decomposition.csv` `155fa607a7e03f8ff6d9040c2c227c3f65b2fa7da9058a83de7a7349ee51dd9f`
  - `verification/out/table3_bootstrap.csv` `542e475019c4ac3fa4bb2d4238093dbd14f4f7a10ca0d5cd79e823e3e11d0f50`
- **Code stays tracked** (`verification/*.py`, and the three small tables).

### AI-use disclosure — running list (me)
- **Claude (Anthropic), via Claude Code:** wrote and ran the data pipeline in this repository
  (`build_dataset.py`, `swpc.py`, `goes_xrs.py`, `run_all.py`, `checks.py`, `join_report.py`,
  `make_split.py`, `fetch_extra.py` and the audit/validation scripts) and drafted the non-decision
  entries in this log. Every scientific decision is recorded above as the user's.
- **Codex:** generated and ran `verification/` (exploratory run above).

## 2026-09-21 — RESULT: decision O keyword merge (fills PENDING under O)

- `fetch_extra.py`: **176 / 176 chunks**, no failures; same record-set strings as the original query,
  keywords only. Original raw chunk files untouched.
- Merged in `build_dataset.py` on HARPNUM + T_REC with `validate="one_to_one"` and an assert that every
  raw row matches and the extras have the same row count. **The assert held in all 176 chunks** (a
  mismatch stops the build). Example: 2024-05 — "1:1, 10378 rows"; rerunning that chunk reproduces the
  file byte-for-byte.
- **Verification against the pre-O file** (SHA-256 `d69ecbc4…`):
  - rows: **255,292 → 255,292**
  - **every pre-existing column identical — every value, every row, same order** (not only labels);
    positives 10,146 unchanged
  - 10 new columns appended: totusjz, meanpot, shrgt45, meangam, meangbt, meangbz, meangbh, meanjzh,
    meanjzd, meanalp
  - missingness of new columns: totusjz 0.000%, meanpot / shrgt45 / meangam 0.022%, the rest 0.029%.
    Not filled or dropped (unchanged policy).
- **New SHA-256, combined labelled file (post-O):**
  `85b88518e4672e676c451aa8f5fe78d5b1b08ed2e40e9cb70a02520f74bee245`
- Combined raw file **unchanged**: `2a65e05ba070dec1aca9bad546ba4825503eff04deb56774b964b1e542a8b28f`
  (extras live in `data/raw_sharp_extra_<chunk>.csv`, not in the raw files).
- All 10 gate features (decision Q) are now in the labelled file: TOTUSJH, TOTPOT, TOTUSJZ, ABSNJZH,
  SAVNCPP, USFLUX, AREA_ACR, MEANPOT, R_VALUE, SHRGT45.
- `frozen/split.csv` is unaffected: HARP set and assignment depend only on rows, which did not change.
**No model trained.**

## 2026-09-21 — Decision S: 6-hourly thinning for gate training; parallelism; timing  (decided by: user)

- **For gate training only**, thin dev (2010–2019) rows to **one per HARP every 6 hours
  (T_REC hour ∈ {0, 6, 12, 18})**. **Scoring, alarms and the cohort stay hourly.**
- CV folds / grid points run in parallel, **n_jobs = performance cores − 1**. This machine (Apple M5):
  4 performance + 6 efficiency cores → **n_jobs = 3**.
- **Time one SVM fit on one fold and report before launching the grid; if the full grid would exceed
  ~3 hours, stop and report.**

### Finding (me) — the {0, 6, 12, 18} grid hits two systematically bad hours. NOT implemented; awaiting user.
Raw SHARP records exist at every hour, but **at 06:00 and 18:00 TAI 99.5% fail QUALITY == 0**
(hour 06: 216 of 45,181 pass; hour 18: 220 of 44,312; every other hour 84–95%). Their QUALITY is
dominated by **0x00010000 `QUAL_LOWINTERPNUM`** — JSOC QUALITY.txt: "the number of averaging points is
lower than TempIntNum, AND/OR 2 interpolation points were separated by more than the cadence" — often
with 0x400 `QUAL_NOCOSMICRAY` (values 65536, 66560). Hours 07–09 and 19 are mildly depleted (84–93%).
Consequence: the specified grid keeps 00 and 12 and almost nothing at 06 and 18 — **9.5% of dev rows
survive instead of ~16.7%**, and the sampling is effectively 12-hourly.
Side note: B&C's cutoff QUALITY > 65536 keeps exactly the 0x10000-only records that QUALITY == 0
drops — plausibly why they chose it. Decision 3 (keep == 0) is unchanged.
T_REC hour is taken in **TAI** (the native slots; the UTC equivalent is hh:59:2x of the previous hour).

### Blocking questions (me)
1. **The timing fit is a model fit.** Standing instruction since decision N: "Train nothing — waiting on
   the signed research plan." S asks for one SVM fit to time it. Not run until the user confirms it is
   authorised (the fitted model would be discarded, used for timing only).
2. **No hyperparameter grid has been specified**, so the full-grid time cannot be estimated.
   For reference only (not a proposal) — verified in B&C (2015) §5: a single setting, not a grid:
   RBF kernel, C = 4, γ = 0.075, tolerance 1e-8 on the relative change in the cost function, class-
   imbalance ratio N/P = 16.5 in both training and testing sets, penalty ratio C1/C2 = 2.0 (positive/negative).

## 2026-09-21 — Decision S amended  (decided by: user; before any model; supersedes the S grid and timing step)

**1. Thinning grid = T_REC TAI hours {4, 10, 16, 22}** (gate training only; scoring, alarms and cohort
stay hourly). Chosen to avoid the QUAL_LOWINTERPNUM slots 06/18 and the depleted 07–09 / 19.
**Documented: QUALITY == 0 systematically excludes TAI 06:00 and 18:00 (99.5% of records there fail it);
kept deliberately.**
Result (dev = 2010–2019, 2020 excluded):
- rows **148,902 → 27,482 (18.5%)**; HARPs 1,218 → 1,213
  (18.5% rather than 1/6 because 06/18 are almost empty, so the surviving rows sit in ~22 usable hours)

| subset | rows | positive rows | negatives | **natural N/P** | positive HARPs |
|--------|-----:|------:|-------:|------:|---:|
| single (primary) | 21,237 | 455 | 20,782 | **45.7** | 63 (of 64 in dev) |
| <= 2 | 25,469 | 633 | 24,836 | **39.2** | 93 |
| all | 27,482 | 853 | 26,629 | **31.2** | 123 |

**2. Hyperparameters: B&C (2015) fixed values, no grid.** RBF kernel, **C = 4, γ = 0.075, tol = 1e-8,
class-weight ratio C1/C2 = 2.0** (positive / negative). **StandardScaler fitted inside each training fold
only.** Documented differences from B&C:
- **γ is not retuned for 10 vs 13 features.** With fewer features the typical squared distance between
  scaled points is smaller, so the same γ gives a relatively wider kernel than B&C's.
- **No negative subsampling to N/P = 16.5.** Natural N/P after thinning is used (table above: 45.7 for
  the primary subset — ~2.8× B&C's).
- Scaling (noted by me): B&C subtract the **median** and divide by the standard deviation (§5);
  StandardScaler subtracts the **mean**. B&C remark the median "appears to slightly improve the results".
  Recorded as a difference; not changed.

**3. Timing-fit step dropped.** Guard kept: **if the 5-fold run exceeds 3 hours, stop and report.**

**Train nothing until the user confirms the research plan is signed.**

## 2026-09-21 — STOP instruction: check for running training / model output (me)
The user ordered all training stopped and any model output recorded as discarded unseen.
**Checked: nothing to stop and nothing to discard.** No project process was running (the only
processes were the ChatGPT/Codex desktop app and MCP servers, none working in this repository); no
model artefacts exist in the project (`*.pkl`, `*.joblib`, `*.model`, fold / OOF / prediction / score
files); no file newer than commit `b423ca4`; working tree clean. No training has been run in this
repository by Claude at any point. (The only model outputs in the repository remain the Codex
exploratory run in `verification/`, recorded above.)

## 2026-09-21 — Decision K2: TRUE irradiance scale  (decided by: user; SUPERSEDES K; before any results seen)

**Switch to option (a) — true irradiance scale, per the NOAA/NCEI recommendation.**
Reasons (user):
- NOAA states the pre-GOES-16 0.7 scaling was incorrect (NCEI GOES 1–15 XRS readme §3.1).
- Recent practice divides old values by 0.7 (Hudson et al. 2023, arXiv:2310.11457;
  SWSC 2025, doi:10.1051/swsc/2025007).
- It increases positive regions in both periods.
**Trade-off (recorded): labels are no longer on the same scale as Bobra & Couvidat (2015) or SWAN-SF;
comparisons with them are approximate.** (This reverses K's stated reason — comparability with B&C,
SWAN-SF and SWPC verification — in favour of physical correctness.)

Implementation (as specified):
1. SWPC events from **GOES-13/14/15** (per each event's `Obs` column): **flux / 0.7** before assigning
   class. **GOES-16/18 events: as reported.** SDO-observed events: kept as reported, flagged
   `scale_unverified` (unchanged rule).
2. Applies to **labels AND n_C/n_M/n_X history features**.
3. GOES empty-day rule thresholds (true flux): **M1 = 1.0e-5, C1 = 1.0e-6**. Empty-day flags re-derived
   from the cached GOES files; changes vs K reported.
4. Relabel all 176 chunks from cache. Verify rows unchanged (255,292) and all non-label columns
   identical; only label/history columns may differ. New SHA-256 recorded.
5. Checks 1–5 rerun. 6. Per-year report incl. events whose class changed K → K2.
7. Per set × subset table under the unchanged `frozen/split.csv`. 8. Fallback rule re-applied.
9. Thinned training set (TAI {4,10,16,22}) re-reported.
**Train nothing until the user confirms.**

## 2026-09-21 — RESULTS: decision K2 (true irradiance scale)

**Conversion** (`data/scale_conversion_report_K2.csv`): GOES-13/14/15 events ÷ 0.7 (exact decimal
arithmetic — binary floating point gives e.g. X1.4 / 0.7 = 1.9999…e-4, not 2.0e-4); GOES-16/18 as
reported; 5 SDO events as reported, `scale_unverified`. 4,170 of 27,219 events changed class K → K2
(both periods: 2010–2019 through ÷0.7; 2020–2024 because K had applied ×0.7).

**Empty-day flags at M1 = 1.0e-5, C1 = 1.0e-6:** 2 changes vs K — 2012-01-29 and 2020-09-26
genuine zero → incomplete_C1 (peaks between 1.0e-6 and 1.43e-6). Now: 824 genuine zero, 3 C1,
5 no data, 3 low coverage → **8 label-missing days (unchanged), 11 history-incomplete (K: 9).**

**Relabel verification:** 176/176 chunks, no failures. **Rows 255,292 → 255,292; row keys identical and
in the same order; every non-label column identical.** Rows changed: `flared_M1_next_24h` 4,003,
`n_C_prev_48h` 35,828, `n_M_prev_48h` 13,338, `n_X_prev_48h` 975, `history_incomplete` 250;
`n_flares_prev_48h` 0 (all-class total is scale-independent — as expected).
**New SHA-256 labelled file:** `d25304cf4b1fc7ee22808da3c6bc015f45f2114510d55f384003c010b35811d9`.
Raw file unchanged: `2a65e05ba070dec1aca9bad546ba4825503eff04deb56774b964b1e542a8b28f`.

**Per year** (K2 [K]):

| year | M1+ flares | positive rows | % positive | events changed class K→K2 |
|------|-----:|------:|------:|-----:|
| 2010 |  11 [8]   |    86 [81]    |  1.10% [1.04%]  |  53 |
| 2011 | 189 [119] |   917 [747]   |  3.83% [3.12%]  | 345 |
| 2012 | 201 [136] | 1,012 [781]   |  4.38% [3.38%]  | 396 |
| 2013 | 169 [111] | 1,143 [790]   |  4.08% [2.82%]  | 315 |
| 2014 | 346 [223] | 1,731 [1,273] |  6.79% [5.00%]  | 264 |
| 2015 | 194 [127] | 1,031 [715]   |  4.22% [2.93%]  | 333 |
| 2016 |  28 [16]  |    98 [67]    |  1.84% [1.26%]  | 188 |
| 2017 |  56 [43]  |   146 [124]   |  2.79% [2.37%]  | 109 |
| 2018 |   1 [0]   |     0 [0]     |  0.00% [0.00%]  |  27 |
| 2019 |   2 [0]   |     0 [0]     |  0.00% [0.00%]  |  35 |
| 2020 |   2 [1]   |     0 [0]     |  0.00% [0.00%]  | 119 |
| 2021 |  29 [16]  |   259 [178]   |  2.09% [1.44%]  | 469 |
| 2022 | 195 [117] | 1,019 [695]   |  4.13% [2.82%]  | 587 |
| 2023 | 365 [202] | 2,108 [1,337] |  6.51% [4.13%]  | 432 |
| 2024 | 935 [545] | 4,599 [3,358] | 14.16% [10.34%] | 493 |

**Checks on K2 labels:** CHECK 1 PASS (X1.2 = true 1.71e-4; all 21 rows in [t0−24h, t0) = 1).
CHECK 2 PASS (median ratio USFLUX 13.90×, TOTUSJH 17.09×). CHECK 3 descriptive (23 HARPs, 5 positive).
CHECK 4 PASS (unchanged). **CHECK 5 FAIL — 2020 and 2022.**
- 2020: 2 M1+, both no region → 0% (was 0 of 1 under K; decision L already excludes 2020).
- **2022: 195 M1+, 20 no region → 89.7% usable, below the pre-registered 90%** (K: 117 M1+, 11 no region,
  90.6% — passed). The additional true-scale M1+ flares include proportionally more without a region.
  **2022 is a test year. It is NOT excluded and the rule is NOT changed — user decision pending.**
  By the precedent of decision L, the fixed rule would exclude it.
- All other years pass (93.0–100%); 2018 and 2019 now have 1 and 2 M1+ flares (all joined), but 0
  positive rows — the HARPs holding them have no rows passing the filters in those windows.

**Split** (`frozen/split.csv` unchanged, SHA-256 `f3ab4056…`; per-set rows identical to before, only
positives moved; 2020 rows excluded per L). Note: the val stratification was drawn under K labels;
under K2 it still contains 21 single-region-positive HARPs.

| set | subset | rows | positive rows | HARPs | positive HARPs |
|-----|--------|-----:|------:|----:|---:|
| train | single |  87,115 | 2,460 | 742 |  65 |
| train | <= 2   | 103,553 | 3,384 | 860 |  91 |
| train | all    | 111,991 | 4,697 | 913 | 118 |
| val   | single |  28,053 |   712 | 244 |  21 |
| val   | <= 2   |  34,487 | 1,032 | 290 |  30 |
| val   | all    |  36,911 | 1,467 | 305 |  40 |
| test  | single |  71,998 | 2,384 | 605 |  71 |
| test  | <= 2   |  86,981 | 4,039 | 709 | 110 |
| test  | all    | 101,909 | 7,985 | 801 | 172 |

**Fallback rule (M re-applied):** single-region positive test HARPs = **71 >= 40 → single-region.**
Without 2022 (if the user excludes it): **55 >= 40 → still single-region.** (Without 2022: single 53,462 rows /
1,978 pos / 55 pos HARPs; <= 2 64,763 / 3,404 / 87; all 77,224 / 6,966 / 142.)

**Thinned dev (TAI {4,10,16,22}):** 148,902 → 27,482 rows (18.5%, unchanged).

| subset | rows | positive rows | natural N/P | positive HARPs |
|--------|-----:|------:|------:|---:|
| single | 21,237 | 587 | **35.2** (K: 45.7) | 83 |
| <= 2   | 25,469 | 818 | **30.1** (K: 39.2) | 118 |
| all    | 27,482 | 1,142 | **23.1** (K: 31.2) | 154 |

Not re-run under K2 (report-only, not requested): the March 2011–2019 completeness check; its thresholds
now match K2's M1 = 1.0e-5.
**No model trained.**

## 2026-09-21 — Decision L2  (decided by: user; fixed rule applied)

**2022 fails CHECK 5 under K2 (89.7% < 90%) → 2022 is excluded from the PRIMARY test. Rule unchanged.**
- **Primary test = 2021, 2023, 2024.**
- **2022-included results are reported only as a labelled sensitivity analysis.**
- `frozen/split.csv` **unchanged** — 2022 HARPs keep their `test` assignment; the primary test excludes
  2022 **rows** at evaluation time (as 2020 rows are excluded under L).
- **When training starts, CV fold strata are computed from the K2 labels** (the val stratification in
  `split.csv` was drawn under K; `split.csv` itself is not changed).
- Also requested: rerun the GOES completeness check at K2 thresholds; report primary-test positive HARPs.
**Train nothing until the user confirms.**

### RESULTS for L2 (me)

**Completeness check at K2 thresholds (M1 = 1.0e-5 true flux; rules otherwise unchanged; report only):**

| month | GOES M1+ peaks | matched | unmatched | SWPC M1+ | GOES coverage |
|-------|---:|---:|---:|---:|---:|
| 2011-03 | 35 | 32 | 3 | 32 | 94.6% |
| 2012-03 | 29 | 28 | 1 | 29 | 86.3% |
| 2013-03 |  3 |  3 | 0 |  3 | 87.5% |
| 2014-03 | 34 | 33 | 1 | 34 | 94.4% |
| 2015-03 | 39 | 38 | 1 | 39 | 97.9% |
| 2016–2019-03 | 0 | 0 | 0 | 0 | 95.8–100% |
| **total** | **140** | **134** | **6** | | (K: 99 / 97 / 2) |

The 6 unmatched, each checked against the flux and the SWPC list within ±3 h:
- **Artefacts of the peak rule (3):** 2012-03-07 04:43 (M1.2; long decay of the X5.4 of 00:02);
  2015-03-03 02:27 (M1.0; decay of the M8.2 peaking 01:35); 2011-03-09 13:29 (M1.1; bump inside SWPC's
  M1.7 event 13:17–14:02, 33 min before its listed peak — just outside ±30 min).
- **Apparently genuine flares absent from SWPC (3):** 2011-03-09 05:18 (isolated peak ~5e-6 → 1.07e-5,
  true M1.1 ≈ operational C7.6; nearest SWPC events 3 h earlier); 2011-03-09 06:56 (1.12e-5 as data
  resume after a 05:30–06:52 gap, eclipse season — true peak may lie in the gap; SWPC lists nothing
  02:33–08:23); 2014-03-11 19:46 (clean rise 4e-6 → 1.15e-5, true M1.1 ≈ operational C8.2, shortly after
  an 18:00–18:37 gap; SWPC lists nothing 18:00–21:40).
- **Interpretation (me):** SWPC appears to miss ~3 of 137 distinct GOES M1+ flares (~2%) in this sample,
  all just above threshold, two beside eclipse-season data gaps. Each is a small set of false-negative
  labels. The K-scale check did not see them because at 1.43e-5 they were below threshold.
  **Report only — no labels changed.** Same coverage caveat as before for 2012-03 / 2013-03.

**Primary test (2022 excluded; `frozen/split.csv` unchanged, SHA-256 `f3ab4056…`):**

| set | subset | rows | positive rows | HARPs | positive HARPs |
|-----|--------|-----:|------:|----:|---:|
| train | single |  87,115 | 2,460 | 742 |  65 |
| train | <= 2   | 103,553 | 3,384 | 860 |  91 |
| train | all    | 111,991 | 4,697 | 913 | 118 |
| val   | single |  28,053 |   712 | 244 |  21 |
| val   | <= 2   |  34,487 | 1,032 | 290 |  30 |
| val   | all    |  36,911 | 1,467 | 305 |  40 |
| **test (primary)** | **single** | **53,462** | **1,978** | **450** | **55** |
| test (primary) | <= 2   |  64,763 | 3,404 | 528 |  87 |
| test (primary) | all    |  77,224 | 6,966 | 605 | 142 |

Fallback rule on the primary test: **55 >= 40 → single-region** (unchanged).
2022-included test (sensitivity only): single 71, <= 2 110, all 172 positive HARPs.
`split_report.py` prints both the 2022-included (sensitivity) and 2022-excluded (primary) tables.
**No model trained.**

## 2026-09-21 — SWPC M1+ completeness at K2 (summary, per user)
**SWPC M1+ completeness at K2 = 134/137 in the sampled months** (March 2011–2019): of 137 distinct GOES
M1+ flares, SWPC lists 134. **The misses are near-threshold** (true M1.1–M1.3), two beside eclipse-season
data gaps. **Reported as label noise; labels unchanged.**

## 2026-09-21 — AUDIT 2018-01-01 → 2020-12-31 (report only; `audit_2018_2020.py`)

**BUG count: 0.** Every SWPC M1+ event (K2) is accounted for:

| start | K2 class (reported, obs) | region | trace | reason |
|---|---|---|---|---|
| 2018-02-07 13:31 | M1.2 (C8.1, G15) | 12699 → HARP 7237 | 24 raw → 21 QUALITY==0 → 0 within ±45° | HARP outside ±45° |
| 2019-05-06 05:04 | M1.4 (C9.9, G15) | 12740 → HARP 7357 | 24 → 22 → 0 | HARP outside ±45° |
| 2019-05-06 13:35 | M1.0 (C7.3, G15) | 12740 → HARP 7357 | 24 → 22 → 0 | HARP outside ±45° |
| 2020-05-29 07:13 | M1.1 (G16) | none | — | no region; 2020 excluded (L) |
| 2020-11-29 12:34 | M4.4 (G16) | none | — | no region; 2020 excluded (L) |

The zero-positive years 2018–2020 are real consequences of the filters, not a pipeline fault.

**GOES M1+ peaks over the 3 years** (1,096 days, 99.5% coverage): 6 peaks, 5 matched to SWPC within ±30 min.
Unmatched: **2019-05-09 05:51**, GOES true 1.03e-5 (M1.0). SWPC lists the **same flare, same minute** as
C6.7 from **GOES-15** = 9.57e-6 true — just below M1. Explanation (me): **inter-satellite calibration**, not
a missed flare. The GOES check uses GOES-16 (science primary from 2017-02-07); SWPC reported from GOES-15.
NCEI readme Table 2 gives the XRS-B ratio GOES-15/GOES-16 = **0.923**; 9.57e-6 / 0.923 ≈ 1.04e-5.

**Caveat raised for the user (no change made):** K2's ÷0.7 removes SWPC's scaling factor but not the
~8% GOES-15/GOES-16 calibration difference. For 2017-02 → 2019-11, SWPC's GOES-15-based classes read ~8%
low relative to GOES-16. Effect limited to near-threshold flares; in this window it touches only the one
event above.
Refactor: the GOES peak detector moved into `goes_xrs.peaks()` (shared by `completeness_check.py` and
the audit); the completeness check reproduces 140 / 134 / 6 after the move.

## 2026-09-21 — TRAINING AUTHORISED  (decided by: user)

**"Training authorised by me on 2026-09-21; research plan not yet signed at this point."**

**Residual calibration difference (recorded, user):** a GOES-15 vs GOES-16 calibration difference
(~8%; NCEI XRS-B ratio GOES-15/GOES-16 = 0.923) **remains after K2**. It affects **near-threshold events
only** and is **not corrected**.

**Staged plan (user).** Stop and report at each CHECKPOINT; continue only on approval; commit after each
stage. Labels = K2. Primary test years = 2021, 2023, 2024 (2022 sensitivity only; 2020 excluded).
- STAGE 2 gate (dev 2010–2019, single-region primary subset) → CHECKPOINT 2 (test years not touched)
- STAGE 3 dev cohort → CHECKPOINT 3
- STAGE 4 primary models on dev; write `frozen/frozen_spec.json`, hash here → CHECKPOINT 4
- STAGE 5 test, run once, only after approval of CHECKPOINT 4 → CHECKPOINT 5 (results table only)

**Scaling (user; supersedes the StandardScaler in amended decision S):** follow B&C (2015) §5 —
"we subtract from every feature its median value and divide by its standard deviation."
Median and standard deviation are **fitted inside each training fold only**.

## 2026-09-21 — STAGE 2 RESULTS: gate (dev only) — CHECKPOINT 2

`stage2_gate.py`. Dev = train+val HARPs of `frozen/split.csv`, rows 2010–2019 (2020 excluded). **Test HARPs
never loaded** (asserted in code: no test HARP, no row after 2019).
- **Unscorable rows (implementation choice, me):** 21 dev hourly rows (1 positive) lack MEANPOT and SHRGT45
  together; an SVM cannot score a missing input and imputation is ruled out, so these rows get **no gate
  score** — excluded from training and metrics, and cannot alarm. (Test has 34 such rows, 0 positive;
  the same rule will apply there.)
- Features: the 10 of decision Q. Training rows: single-region, thinned to TAI {4,10,16,22}.
  Scaling: B&C §5 median / standard deviation, per training fold. SVM: RBF, C=4, γ=0.075, tol=1e-8,
  class weight positive:negative = 2.0:1.0. No tuning.
- Folds: 5, grouped by HARPNUM, stratified by 3 HARP strata **from K2 labels**, seed 20260921; built by
  shuffling each stratum and dealing HARPs round-robin. HARPs per fold 245/244/243/243/243; single-region
  positive HARPs per fold 18/17/17/17/17. Grouping asserted (no HARP in two folds).
- Fits: 16,705–17,127 training rows per fold (443–499 positive), 909–1,023 support vectors, ~1 s each;
  **total 2.8 s** (limit 3 h). **Rerun reproduces the out-of-fold scores byte-for-byte.**
- Score = SVM decision function, every hourly dev row out-of-fold (115,147 primary-subset rows).
- **Threshold = −0.992496** (max TSS on pooled out-of-fold hourly scores, primary subset).

Primary subset, hourly, at the pooled threshold:

| fold | rows | pos rows | HARPs | pos HARPs | TSS | HSS | TPR | FPR | FAR | own optimal threshold | TSS at own optimum |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 24,586 | 754 | 209 | 18 | 0.788 | 0.473 | 0.837 | 0.049 | 0.648 | −0.9920 | 0.788 |
| 1 | 22,197 | 739 | 193 | 17 | 0.785 | 0.531 | 0.825 | 0.040 | 0.586 | −0.9800 | 0.787 |
| 2 | 22,343 | 479 | 191 | 17 | 0.662 | 0.381 | 0.702 | 0.040 | 0.720 | −0.9940 | 0.665 |
| 3 | 22,421 | 505 | 195 | 17 | 0.392 | 0.329 | 0.414 | 0.022 | 0.701 | −1.0057 | 0.416 |
| 4 | 23,600 | 694 | 198 | 17 | 0.663 | 0.392 | 0.715 | 0.052 | 0.705 | −0.9962 | 0.665 |
| **pooled** | **115,147** | **3,171** | **986** | **86** | **0.679** | **0.434** | **0.720** | **0.041** | **0.667** | −0.9925 | 0.679 |

Artefacts (in `data/`, not tracked): `data/stage2/oof_scores_dev.csv`, `stage2_metrics.csv`,
`stage2_result.json`; fold models `data/stage2/models/fold{0..4}.joblib`, SHA-256:
fold0 `d283c18bfe242518d0389c33c2e94bfe25405b0bc9ebd3f42030592ec09ee00a`,
fold1 `1dbc5a7908903d4cb9d9c03d14e3c51945b2712333a1b2dbcd556779b7769c20`,
fold2 `9e6f233705d9490f830b439a5debd215dc856f3879fd51e142b7f7a8df164d7c`,
fold3 `7aeae7f67c858889c249089e7f0af54832490e190e158e4b731cfb36ac87970c`,
fold4 `49e7c9597746e1398990b13c65a311aa8f16de12780900878cc0b7cd91ac8f48`.
**Test years not touched.** Awaiting approval of CHECKPOINT 2.

### CHECKPOINT 2 approved (user, 2026-09-21)
- **Missing-feature rule adopted as the user's decision:** rows with any gate feature missing are
  **unscorable** — excluded from alarms and metrics, counted and reported (dev 21, test 34).
- **Dev TSS is mildly optimistic:** the threshold was chosen on the same pooled out-of-fold scores it is
  evaluated on. **The test TSS is the unbiased estimate.**

## 2026-09-21 — BUG FOUND AND FIXED (me): month-boundary duplicate rows

Found while building the Stage 3 cohort (a one-to-one merge assert failed).
**Cause:** JSOC record-set ranges `A-B` include both ends, so each monthly query
`[1st 00:00 TAI – next 1st 00:00 TAI]` also returned the next month's 00:00 TAI record, which the next
chunk fetched again. **Extent:** 1,488 duplicate raw rows of 1,074,130 (0.14%); **393 duplicate labelled rows**
of 255,292 (0.15%), 21 positive. Every duplicate is the 00:00 TAI record on the 1st of a month; **all 393 pairs
were identical in every column** (labels agreed because each chunk's flare window was padded), so no value
was wrong — rows were counted twice.
**Fix:** `run_all.py` drops the second copy when concatenating, after **asserting the copies are identical**.
Raw chunk files are untouched. Result verified equal to the old file with duplicates removed.
- Labelled: **255,292 → 254,899 rows**, 0 duplicates. **New SHA-256:**
  `62a0e4ccffe8b1fc4dacd2a0ba80570bf56018540d57367c16eb37337380ffeb`
- Raw combined: 1,074,130 → 1,072,642. **New SHA-256:**
  `be7c7d44b33b13a4620e4b98d23a217fac8e87597360b6ed548cf53f4faf8fa3`
- **`frozen/split.csv` unaffected** (the HARP set is unchanged; split is per HARP).
- Earlier row-count tables in this log (from the first full summary through K2 and L2) include these
  duplicates; they are overstated by ≤ 0.15% of rows. Positive-HARP counts are unaffected (a duplicate
  never introduces a new HARP).

**Stage 2 rerun on the corrected file** (deterministic, 2.8 s): **threshold unchanged (−0.992496); fold
models bit-for-bit identical to the approved ones** (training uses TAI {4,10,16,22}, never hour 00);
fold assignment unchanged. Metrics change only through the removed duplicate rows: 195 fewer primary-
subset rows (3 positive); per-fold TSS change ≤ 0.0016; **pooled TSS 0.6789 → 0.6793**, HSS +0.0003,
FAR −0.0003; positive HARPs unchanged. Approved CHECKPOINT 2 results otherwise stand.

### Fold 3 detail (report only, user request; K2, primary subset, OOF, threshold −0.992496)
8 of 17 positive HARPs detected. Detected (max OOF score on positive rows): 3291 (2.941), 4941 (1.331),
753 (0.848), 5956 (−0.356), 2636 (−0.863), 2635 (−0.872), 54 (−0.939), 4231 (−0.974). Not detected:
902 (−0.996; 67 positive rows), 1990 (−0.997), 4760 (−0.999), 1464 (−1.004), 1558 (−1.005), 3344 (−1.005),
6972 (−1.024), 2887 (−1.073), 3258 (−1.270; alarmed at other times, max over all rows 1.728).
Six of the nine misses lie within 0.013 of the threshold.

## 2026-09-21 — STAGE 3 RESULTS: dev alarm cohort — CHECKPOINT 3

`cohort.py` (rules; reused unchanged for test in Stage 5) + `stage3_cohort.py`. Dev 2010–2019, primary subset,
Stage 2 out-of-fold scores, threshold −0.992496. Implementation details fixed before results (me):
episode = alarm hours of one HARP exactly 1 h apart (any gap ends it); eligible = onset row labelled,
`history_incomplete` False, >= 18 of 24 points in (t−24h, t] with USFLUX and TOTUSJH present; first eligible
episode per HARP; history via existing `n_*_prev_48h` ([t−48h, t) ≡ (t−48h, t] here — t is always hh:59:2x
UTC, flare starts are whole minutes); trend = least-squares slope vs hours / window mean; delayed = false
alarm with >= 1 M1+ from the HARP's region in (t+24h, t+48h] and that window free of label-missing days.

- Alarm hours: 6,836; **episodes: 1,311 in 220 HARPs**.
- Exclusions while searching each HARP's first eligible episode: **231 episodes skipped, all for
  "trend window < 18 points"**; 0 for `history_incomplete`; 0 label-missing.
- **41 HARPs** alarmed but had **no eligible episode** (all: trend window < 18 points).

| | regions |
|---|---:|
| **cohort (one episode per region)** | **179** |
| true alarms | **25** |
| false alarms | **154** |
| delayed (exploratory; subset of false, complete follow-up) | **16** |
| false with a flare in (t+24h, t+48h] but incomplete follow-up | 0 |

Diagnostics (me, report only):
- **Episode fragmentation by the 06/18 TAI gap.** Episode length median 4 h, max **11 h**, 375 single-hour
  episodes; median 3 episodes per HARP (max 23). QUALITY == 0 removes almost all 06:00 and 18:00 TAI records, so
  the "exactly 1 h apart" rule **breaks every alarm run at least every 12 h**. For the 67 regions whose chosen
  episode is not their first, the "onset" may be a restart after a 06/18 gap rather than a true onset.
  Whether a single systematic missing hour should break an episode is a user decision — **not changed**.
- **Why true alarms are few:** 60 HARPs have >= 1 detected positive hour; 55 are in the cohort; for **30** of
  them the first eligible episode began > 24 h before the flare, so it is a false alarm by definition.
- Selection: onset is at a median 48 h after the HARP's first labelled row (the 24-h trend window and the
  18-point rule push onsets later).

Artefacts: `data/stage3/cohort_dev.csv`, `exclusions_dev.csv`, `episodes_dev.csv`.
**Test years not touched.** Awaiting approval of CHECKPOINT 3.

## 2026-09-21 — Checkpoint 3 decisions T1, T2, T3  (decided by: user)
**Made after seeing the cohort sizes, before any trend or model result.**
Note (me): the Stage 3 cohort file contains per-episode trend slopes (computed to apply the 18-point rule),
but **no trend comparison between true and false alarms was computed, printed or viewed**, and no cohort
model has been fitted.

**T1. Episode merging.** Consecutive alarm hours stay in one episode across **up to 3 consecutive
missing/unscorable hours**. An episode ends only at a **scored hour below threshold**, or at a **gap of more
than 3 missing hours**. Reason (user): missing ≠ below threshold; the 06/18 TAI QUALITY gap fragments episodes.
Implementation (me): "missing/unscorable" = any hour with no primary-subset score for that HARP (no SHARP
record, removed by a filter, unscorable, or a multi-region hour). Walking a HARP's scored hours in time order,
a new episode starts at an alarm hour if the previous scored hour was below threshold, or if the previous
scored hour is more than 4 h earlier (> 3 missing hours between).

**T2. Unit = all eligible alarm episodes** (not first-per-region). Each episode is weighted
**1 / (number of eligible episodes in its HARP)**, so each region contributes equally. Grouped CV and the
bootstrap stay grouped by HARP. **Sensitivity: first-episode-per-region.**

**T3. The 18-of-24 trend rule is unchanged.**

Also requested: the Bobra & Couvidat replication check (skipped so far) — **protocol report first, then stop**.

## 2026-09-21 — REVISED STAGE 3 RESULTS (T1, T2, T3) — revised CHECKPOINT 3

Rebuilt with T1 merging and T2 unit; T3 unchanged. Same threshold (−0.992496), same OOF scores.
- Alarm hours 6,836; **episodes (T1): 697 in 220 HARPs** (was 1,311); episode length median 2 alarm hours,
  max 151.
- Exclusions: **197 episodes** "trend window < 18 points"; 0 `history_incomplete`; 0 label-missing.
  **51 HARPs** alarmed with no eligible episode (was 41).

| cohort | episodes | true | false | delayed | regions | regions with >= 1 true episode | region-weighted true / false / delayed |
|---|---:|---:|---:|---:|---:|---:|---|
| **PRIMARY (T2: all eligible episodes, weight 1/episodes-in-HARP)** | **500** | **83** | **417** | **39** | **169** | **33** | **19.53 / 149.47 / 11.09** (sum 169) |
| SENSITIVITY: first eligible episode per region | 169 | 20 | 149 | 13 | 169 | 20 | 20 / 149 / 13 |

**The 55 flaring regions** (previous cohort, >= 1 detected positive hour): **33 now contribute >= 1
true-alarm episode**; 16 are in the cohort with only false episodes; **6 are no longer in the cohort**
(trend window < 18 points).
Mechanism (me): 10 regions of the previous cohort lost eligibility and none gained it. Under T1, a later
fragment that was eligible on its own is absorbed into an episode whose (earlier) onset fails the 18-of-24
rule, which T3 keeps. The first-per-region sensitivity cohort now has 20 true alarms (previous cohort: 25)
for the same reason — merged onsets are earlier, further from the flare.
Artefacts replaced: `data/stage3/cohort_dev.csv` (now all eligible episodes, with `weight`,
`first_eligible`), `exclusions_dev.csv`, `episodes_dev.csv`.
**No trend or model result computed or viewed. Test years not touched.**

## 2026-09-21 — PROPOSED protocol: Bobra & Couvidat replication check (me; awaiting user approval; NOT run)

**Comparator, verified in the paper:** B&C report two parameter sets. **Table 2: C1/C2 = 2.0, operational
case, 13 features → TSS 0.610 ± 0.048.** Table 3: C1/C2 = 15.0 (chosen to maximise TSS) → 0.76 operational
(their conclusion's figure). **Our gate uses C1/C2 = 2.0, so the like-for-like comparator is Table 2's
0.610 ± 0.048,** not 0.76.

**Our quantity:** gate TSS, hour-level, primary subset —
(a) dev pooled out-of-fold at the frozen threshold (0.6793; mildly optimistic, noted at checkpoint 2);
(b) test, Stage 5, 2021/2023/2024, at the frozen threshold (the unbiased figure).
Optional, if approved: TSS at SVM decision value 0 (B&C classify by the sign of the decision function;
we use a max-TSS threshold), computed on the same dev OOF scores — the closest analogue of their rule.

**Pre-stated framing:** the comparison is **descriptive, not pass/fail** — the protocols differ in ways
that move TSS in both directions. Reported alongside our number:

| | Bobra & Couvidat (2015) | this study |
|---|---|---|
| features | 13 | 10 (TOTBSQ, TOTFZ, EPSZ unavailable) |
| QUALITY | discard > 65536 | keep == 0 (stricter; drops 06/18 TAI) |
| longitude | flares within ±68° of central meridian | HARP |LON_FWT| <= 45° |
| samples | 1 per flare (24 h before GOES peak) + random quiet times | every hourly row (training thinned 6-hourly) |
| class ratio | N/P fixed 16.5 (train and test) | natural (35.2 primary, thinned) |
| split | random 70/30 of examples — same region can be in train and test | grouped by HARP; chronological test |
| threshold | sign of decision function | max TSS on pooled OOF |
| scaling | median / std | median / std (same) |
| flare scale / catalogue | operational scale; NGDC GOES catalogue | true irradiance (K2); SWPC originals |
| period | 2010-05 → 2014-05 | dev 2010–2019; test 2021, 2023, 2024 |
| C1/C2 | 2.0 (Table 2) | 2.0 |
The random 70/30 split lets one region's samples fall on both sides, which tends to inflate B&C's TSS;
our stricter QUALITY and ±45° cut change the population. Neither direction is assumed in advance.
**Stopped: awaiting approval of the protocol and of revised CHECKPOINT 3.**

## 2026-09-21 — DIAGNOSTIC ABLATION, pre-declared as diagnostic  (decided by: user)
Dev 2010–2019 only. **Does not change the primary pipeline. Test years untouched.** Same SVM settings and the
same 10 features throughout. Baseline = current Stage 2 gate (pooled OOF TSS 0.679). Change ONE factor per run;
report TSS, TPR, FPR; single table; no interpretation.
- **D1** threshold = SVM decision value 0 (B&C rule) instead of max-TSS
- **D2** K labels (old ×0.7 scale, file `85b88518…`) instead of K2
- **D3** B&C's longitude limit instead of ±45°, rebuilt from raw
- **D4** B&C's positive/negative sample definition instead of all hourly rows
- **D5** random row-level split instead of HARP-grouped
- **D6** D1–D5 together ("B&C-like pipeline")
Each change is to be traced to a quoted B&C sentence.

### DIAGNOSTIC ABLATION — RESULTS (dev 2010–2019 only; test HARPs never loaded; primary pipeline unchanged)
`diag_ablation.py`, `diag_build.py` → `data/diag/ablation.csv`. Primary subset (single-region), 10 features, same
SVM throughout. Folds held fixed from Stage 2; HARPs that exist only in the ±68° variants dealt into folds by the
same stratified seeded procedure. Unscorable rows excluded (user rule). All TSS are pooled out-of-fold.

| run | source in B&C (2015) | TSS | TPR | FPR | threshold | eval rows | eval positives | pos. HARPs |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| baseline (Stage 2) | — | 0.6793 | 0.7200 | 0.0407 | −0.9925 | 114,952 | 3,168 | 86 |
| D1 threshold = decision value 0 | no threshold selection described; scikit-learn `SVC` used (p.16) — **inferred**, not stated | 0.3354 | 0.3453 | 0.0099 | 0 | 114,952 | 3,168 | 86 |
| D2 K labels (old scale, file `85b88518…`) | flares from NGDC GOES catalogues, operational scale (p.6) | 0.6773 | 0.7189 | 0.0416 | −0.9999 | 114,952 | 2,440 | 64 |
| D3 longitude ±68° | ARs outside ±68° of central meridian rejected (p.6, p.10) | 0.6456 | 0.6907 | 0.0451 | −0.9979 | 160,223 | 4,821 | 107 |
| D4 B&C samples | positive sample 24 h before GOES peak; random quiet times; 303 pos / 5,000 neg (p.7) | 0.8119 | 0.8697 | 0.0578 | −0.9888 | 4,165 | 238 | 71 |
| D5 random row-level split | examples randomly divided 70/30 (p.21) | 0.7901 | 0.8318 | 0.0417 | −1.0010 | 114,952 | 3,168 | 86 |
| D6 all of D1–D5 | all of the above | 0.6865 | 0.6992 | 0.0128 | 0 | 4,655 | 266 | 74 |

Notes (me, factual only):
- **Baseline reproduced** through the ablation code: TSS 0.6793, identical to Stage 2.
- **Scale switch validated:** `FLARE_SCALE=K` rebuild at ±45° reproduces file `85b88518…` (dev rows, deduplicated)
  in every column except `history_incomplete` (183 rows; the GOES empty-day table is at K2 thresholds; not a gate input).
- D4: B&C's sample definition includes the class ratio (303 positives, 5,000 random negatives), so D4 changes the
  sample construction and N/P = 16.5 together — inseparable as specified. 1,138 K2 M1+ flares in the window;
  238 have a single-region row within 30 min of peak − 24 h (887 do not; 13 flares share a row with another).
  Trained on the sampled rows (no 6-hourly thinning; the sample definition replaces it).
- D6 = K labels + ±68° + D4 samples + random row split + threshold 0. K flare list: 753 M1+ in the window, 266 sampled.
- **Bug found and fixed before reporting (me):** D6's sample builder first drew positives from the K2 flare list
  while using K labels; corrected to the K list. D1–D5 were unaffected and are unchanged by the fix.
- Diagnostic code paths are off by default: `FLARE_SCALE` defaults to K2, `LON_LIMIT` to 45, and `build_dataset.py`
  refuses to write diagnostic settings into the primary `data/` files. A default rebuild of 2014-01 is
  byte-identical to the primary file.

## 2026-09-21 — DIAGNOSTIC: uncertainty for the ablation  (decided by: user; dev only; diagnostic)
1. Verify the comparator for D6: what B&C Table 2's ± represents (sd over how many runs, what varied) and which
   threshold rule produced it; say so if unclear.
2. Baseline and D1–D6 repeated with 20 fold seeds (region-grouped for all except D5, which keeps its random split);
   report mean, sd, min, max TSS.
3. Baseline and D6: region-level bootstrap 95% CI on TSS (1,000 resamples of HARPs) at fixed fold assignment.
4. D2 vs baseline: besides TSS, how many rows, positive HARPs and alarm episodes differ.
Table only, no interpretation. Test years untouched.

### RESULTS — ablation uncertainty (dev only; diagnostic; test years untouched)

**1. Comparator (B&C 2015, verified in the paper).**
- **What the ± is:** the mean and standard deviation over **1,000 repetitions** of training and testing (p.28:
  they "repeat the training and testing phases 1000 times"). **What varied:** the random 70/30 split of
  *examples* (ratio held fixed) and the SVM's random initialisation (p.28). Examples, not regions, were split.
- **Table 2 = C1/C2 = 2.0** (p.21), parameters "selected to achieve the highest HSS2" (Table 2 caption, p.34);
  operational TSS 0.610 ± 0.048. Table 3 (C1/C2 = 15.0, selected for highest TSS) gives 0.76 operational.
- **Threshold rule: not stated.** No threshold selection is described; classification by the default decision
  boundary of scikit-learn's `SVC` is an inference, not a statement in the paper. **Unclear.**
- **Also unclear:** whether the "selected to achieve the highest HSS2" parameter choice was made on data separate
  from the reported test splits. Not stated.
- Consequence for D6 (fact, not interpretation): B&C's ± is a spread over random example-level splits, so the
  closest analogue here is the seed spread of D5/D6, which also use random row-level splits (5-fold, 20 seeds,
  versus 70/30, 1,000 repetitions).

**2. TSS over 20 fold seeds** (seeds 20260921 + 0…19; seed 0 = the Stage 2 folds and reproduces the ablation
table exactly). Region-grouped folds except D5 and D6 (random row split; D6 includes D5's split by definition).
D4/D6 samples fixed; only folds vary.

| run | seed 0 | mean | sd | min | max |
|---|---:|---:|---:|---:|---:|
| baseline | 0.6793 | 0.6760 | 0.0101 | 0.6554 | 0.6923 |
| D1 threshold 0 | 0.3354 | 0.3993 | 0.0325 | 0.3354 | 0.4435 |
| D2 K labels | 0.6773 | 0.6890 | 0.0166 | 0.6542 | 0.7112 |
| D3 ±68° | 0.6456 | 0.6658 | 0.0092 | 0.6456 | 0.6797 |
| D4 B&C samples | 0.8119 | 0.8120 | 0.0075 | 0.7945 | 0.8266 |
| D5 random row split | 0.7901 | 0.7912 | 0.0023 | 0.7869 | 0.7953 |
| D6 all of D1–D5 | 0.6865 | 0.6929 | 0.0056 | 0.6839 | 0.7057 |

**3. Region-level bootstrap** (1,000 resamples of HARPs, seed-0 folds, fixed threshold; 0 resamples lacked a class):

| run | TSS | 95% CI | threshold | HARPs |
|---|---:|---|---:|---:|
| baseline | 0.6793 | [0.5863, 0.7484] | −0.9925 | 986 |
| D6 | 0.6865 | [0.5624, 0.7827] | 0 | 942 |

**4. D2 (K labels) vs baseline (K2 labels), seed-0 folds**

| quantity | baseline (K2) | D2 (K) | difference |
|---|---:|---:|---|
| evaluation rows | 114,952 | 114,952 | identical row keys |
| rows with a different label | | | **728** (all positive under K2 only; 0 positive under K only) |
| positive HARPs | 86 | 64 | 64 in both; **22 baseline only**; 0 D2 only |
| alarm episodes (T1 rule, each run's own threshold) | 697 | 918 | **146 identical**; 551 baseline only; 772 D2 only |
| threshold | −0.9925 | −0.9999 | |
| TSS | 0.6793 | 0.6773 | |

## 2026-09-21 — Decisions on the ablation, the replication protocol, and T4  (decided by: user)

**1. Ablation uncertainty — accepted.** Recorded wording (user):
"B&C Table 2 TSS (0.610) lies within the region-bootstrap 95% CI of our B&C-style reproduction D6 (0.687,
[0.562, 0.783]). Compatible; not a formal test of agreement. B&C's threshold rule and whether their parameter
selection used held-out data are not stated. Their ± (sd over 1,000 random example-level splits) is not directly
comparable to our seed sd. Random example-level splitting (D5) scored higher than region-grouped (baseline) in
all 20 seeds (0.787–0.795 vs 0.655–0.692); cause not decomposed. K vs K2: similar TSS but different positive
HARPs (64 vs 86) and alarm episodes."
**D6 keeps D5's random split — correct; it is the B&C-like combination.**
(Checked by me: D5 > baseline in every one of the 20 seeds.)

**2. Replication protocol — approved as proposed.** Addition: **in Stage 5, the gate test TSS is reported with a
region-level bootstrap 95% CI (1,000 resamples), not a seed sd.**

**3. Revised Checkpoint 3 approved, with one change — T4.**
**T4 — made after seeing cohort sizes, before any trend comparison or model result.**
The episode alarm time **t = the first hour within the episode whose (t−24h, t] trend window has >= 18 of 24
points** (first evaluable hour). **Labels, history and trends are all measured relative to this t. Episodes with
no evaluable hour are excluded.** Reason (user): T1 merging moved onsets before trends are measurable, excluding
whole episodes whose later hours were evaluable. **T1, T2, T3 unchanged.**
Implementation (me): candidate hours for t are the episode's alarm hours in time order (missing hours inside an
episode have no row and cannot be t). The `history_incomplete` rule (D) is then applied at that t: if it is
True the episode is excluded (reason "history_incomplete at t"); t is not moved further.

## 2026-09-21 — STAGE 3b RESULTS: dev cohort under T1–T4 — CHECKPOINT 3b
Same OOF scores and threshold (−0.992496). 697 episodes (T1) in 220 HARPs; 6,836 alarm hours.
- **Exclusions:** **150 episodes** "no evaluable hour" (trend window < 18 points at every alarm hour of the episode);
  0 `history_incomplete at t`; 0 label-missing. **40 HARPs** alarmed with no eligible episode.
- **T4 shift:** t equals the episode onset for 500 of 547 eligible episodes (median shift 0 h) — these are the 500
  episodes of the T1–T3 cohort; the other **47 are recovered** by T4.

| cohort | episodes | true | false | delayed | regions | regions with >= 1 true | region-weighted true / false / delayed |
|---|---:|---:|---:|---:|---:|---:|---|
| **PRIMARY (T1–T4, all eligible episodes, weight 1/episodes-in-HARP)** | **547** | **98** | **449** | **47** | **180** | **41** | **24.13 / 155.87 / 13.04** (sum 180) |
| SENSITIVITY: first eligible episode per region | 180 | 25 | 155 | 16 | 180 | 25 | 25 / 155 / 16 |

- **The 55 previously listed flaring regions:** **41 contribute >= 1 true-alarm episode**; 14 only false; 0 missing
  from the cohort.
- **All 86 dev positive HARPs (primary subset):** **41 contribute >= 1 true-alarm episode**; 21 are in the cohort
  with only false episodes; 24 are not in the cohort — **16 never alarmed**, 8 alarmed but had no eligible episode.
Artefacts replaced: `data/stage3/cohort_dev.csv` (adds `episode_onset`, `hours_onset_to_t`), `exclusions_dev.csv`,
`episodes_dev.csv`. **No trend comparison computed or viewed; no model fitted. Test years untouched.**

## 2026-09-21 — STAGE 4 ON HOLD; full-fidelity B&C reproduction D7  (decided by: user; diagnostic, dev data only)
- **Stage 4 is on hold until the user approves.**
- **Step 1:** protocol audit table from the paper (location for each item), each item marked MATCHABLE /
  NOT MATCHABLE (why) / NOT STATED IN PAPER.
- **Step 2 — D7 "closest possible reproduction":** match every MATCHABLE item (their period, QUALITY rule rebuilt
  from raw, longitude limit, old K scale, sample definitions and N/P, random 70/30 split by example, 1,000 repeats),
  with the 10 available features; NOT STATED items take the most literal reading, listed as assumptions. Report mean
  ± sd TSS over 1,000 repeats (comparable to their 0.610 ± 0.048), min/max, TPR, FPR, positive/negative counts.
- **Step 3 — D7b:** our own pipeline (baseline) restricted to the same period, with a region-bootstrap 95% CI.
Table only, no interpretation.

### D7 Step 1 — B&C (2015) protocol audit (me; paraphrased with page references, not quoted in full)

| item | what the paper says (page) | status for D7 |
|---|---|---|
| data period | SHARP data and flares May 2010 – May 2014 (pp.6, 7) | MATCHABLE — end day not stated; **assumed 2010-05-01 → 2014-05-31** |
| patch type / AR definition | SHARP patches from the automatic detection algorithm; may merge several NOAA ARs into one (pp.7, 9) | MATCHABLE (HARPs) |
| multi-region handling | not described (only that patches can merge NOAA ARs, p.9) | NOT STATED — **assumed ANY rule**: a flare in any NOAA AR of the patch counts for the patch |
| flare–patch association | flares located via NGDC catalogue (p.6); mapping of flare to patch not described | NOT STATED — **assumed via NOAA AR number in `NOAA_ARS`** |
| longitude limit | flares within ±68° of central meridian (p.6); ARs outside ±68° rejected (p.10) | PARTLY MATCHABLE — AR limit applied as \|LON_FWT\| ≤ 68 at the sample time; the flare-location limit is **approximated** by the patch's LON_FWT at the record nearest the flare peak (SWPC XRA lines carry no flare location) |
| QUALITY rule | SHARP entries with QUALITY > 65536 (0x10000) discarded (p.23) | MATCHABLE — rebuilt from raw: keep QUALITY ≤ 65536 |
| flare catalogue | NGDC GOES X-ray flare catalogues (p.6) | NOT MATCHABLE — we use SWPC original event reports (the NGDC lists derive from the same SWPC reports); regions required (NGDC entries with locations, p.6) |
| class scale | GOES operational scale of the time (catalogue, p.6) | MATCHABLE — K (old ×0.7) scale |
| positive sample | sample time exactly 24 h before the GOES peak; every flare counted separately, repeated flares of one AR included (pp.6–7) | MATCHABLE with one approximation — nearest **hourly** record within ±30 min of peak − 24 h (our cache is hourly; B&C used 12-min records, p.7) |
| negative sample | flare-quiet sample times chosen randomly; operational case: AR does not flare within 24 h after the sample time (pp.6–7) | MATCHABLE — random records whose patch has no M1+ in (t, t+24h]; **assumed uniform over eligible records, without replacement, drawn once** |
| number / N/P | 303 positives, 5,000 random negatives (p.7); N/P = 16.5 in training and testing (p.21) | MATCHABLE — N = round(16.5 × P) |
| features | 13 highest-F-score of Table 1 (p.24) | NOT MATCHABLE — 10 of 13 (TOTBSQ, TOTFZ, EPSZ not keywords) |
| scaling | subtract median, divide by standard deviation (p.23) | MATCHABLE — **which data the median/sd come from is not stated; assumed the whole catalogue, before splitting** (literal reading of a pre-processing step) |
| SVM kernel, parameters | RBF; C = 4, γ = 0.075, tol 1e-8 (pp.15, 21) | MATCHABLE |
| C1/C2 | 2.0 for Table 2 (p.21) | MATCHABLE — **which class carries C is not stated; assumed C2 = C = 4 (negatives), C1 = 8** (same convention as our gate) |
| threshold rule | not described | NOT STATED — **assumed the SVC default (decision value 0)** |
| train/test split | examples randomly divided 30% test / 70% train, ratio always kept (pp.21, 28); N/P 16.5 in both | MATCHABLE — random, by example, **stratified by class** so both keep N/P |
| repeats | 1,000 repetitions; means and sds in Tables 2–3 (p.28) | MATCHABLE — 1,000 |
| metric | TSS = TP/(TP+FN) − FP/(FP+TN) (eq. 17, p.19) | MATCHABLE |
| missing data | not described | NOT STATED — **assumed: examples with any missing feature dropped before sampling** |
| NOAA mapping for negatives | not described | NOT STATED — **assumed: patches with a NOAA number only** (otherwise "does not flare" cannot be determined) |

### D7 Step 2 and D7b Step 3 — RESULTS (diagnostic; dev period only; test years untouched)
`diag_d7.py` → `data/diag/d7_repeats.csv`. Built from raw chunk files with the audit-table choices and assumptions.

**D7 construction counts**
- Raw rows 2010-05 … 2014-06: 379,600 → QUALITY ≤ 65536: 343,198 → |LON_FWT| ≤ 68: 252,052 → features present and
  NOAA-mapped: 140,847 (eligible rows restricted to 2010-05-01 … 2014-05-31 for sampling).
- SWPC M1+ flares, K scale, with a region: 455. Used as positives: **272** (269 distinct records; 3 records serve two
  flares each, one example per flare as in B&C). Not used: 121 flare-location proxy (patch |LON| > 68 or no record at
  the peak); 61 no patch record within 30 min of peak − 24 h passing the filters; 1 sample time outside the period;
  0 without a peak time; 0 region in no patch.
- Negative pool (eligible records, no M1+ from the patch's regions in (t, t+24h]): 132,939; drawn once:
  **N = 4,488** (N/P = 16.50).
- Distinct patches: 90 among positives, 761 among negatives.

| run | TSS | sd | min | max | TPR | FPR | P | N | uncertainty |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| **B&C (2015) Table 2, operational** | **0.610** | 0.048 | — | — | — | — | 303 | 5,000 | sd over 1,000 random 70/30 splits |
| **D7 closest reproduction** | **0.5267** | **0.0500** | 0.3562 | 0.6969 | 0.5399 ± 0.0505 | 0.0132 ± 0.0032 | 272 | 4,488 | sd over 1,000 random 70/30 splits (stratified; ~82 pos / 1,346 neg per test set) |
| **D7b our baseline, same period** (2010-05-01 … 2014-05-31) | **0.5861** | — | — | — | 0.6318 | 0.0457 | 57 pos HARPs, 1,863 pos rows | 71,023 rows, 613 HARPs | region bootstrap 95% CI **[0.4665, 0.6800]**, 1,000 resamples |

D7b: Stage 2 baseline machinery (Stage 2 fold map, 6-hourly thinned single-region training, hourly OOF evaluation) on
rows in the period only; the max-TSS threshold (−0.9918) is re-chosen on this period's OOF scores.
D7 assumptions in force (from the audit table): end date 2014-05-31; ANY rule; flare→patch via NOAA number; flare-
location proxy; nearest hourly record (±30 min) instead of 12-min; negatives uniform, without replacement, drawn once;
scaling on the whole catalogue; C2 = C = 4, C1 = 8; threshold = decision value 0; stratified split; examples with
missing features dropped; NOAA-mapped patches only; no missing-SWPC-day rule (B&C have none).
**Stage 4 remains on hold.**

## 2026-09-21 — DIAGNOSTIC D7t, pre-declared  (decided by: user; dev only)
Identical to D7, except **the threshold is chosen within each 70/30 split by max TSS on the TRAINING 70% only**,
then applied to the 30% test. Report mean ± sd, min, max TSS over 1,000 repeats. Table only. **Stage 4 stays on hold.**
Note (me, factual): the training-set decision values used to choose the threshold are in-sample (the SVM is fitted
on those same examples) — as specified.

### D7t — RESULTS (diagnostic; dev period only; test years untouched)
Same catalogue (P 272, N 4,488) and the same 1,000 splits as D7 — the rerun reproduces `d7_repeats.csv` byte-for-byte.
Output: `data/diag/d7t_repeats.csv`.

| run | threshold rule | TSS mean | sd | min | max | TPR | FPR | threshold |
|---|---|---:|---:|---:|---:|---:|---:|---|
| B&C (2015) Table 2 | not stated | 0.610 | 0.048 | — | — | — | — | — |
| D7 | decision value 0 (assumed) | 0.5267 | 0.0500 | 0.3562 | 0.6969 | 0.5399 ± 0.0505 | 0.0132 ± 0.0032 | 0 |
| **D7t** | **max TSS on the training 70% (in-sample), applied to the 30%** | **0.7065** | **0.0401** | **0.5680** | **0.8189** | 0.7843 ± 0.0427 | 0.0778 ± 0.0094 | mean −0.9926 (−1.0241 … −0.8920) |
**Stage 4 remains on hold.**

## 2026-09-21 — Replication conclusion  (decided by: user)
"Closest reproduction of B&C 2015 (D7): TSS 0.527 ± 0.050 with decision value 0; D7t: 0.707 ± 0.040 with threshold
learned on the training 70%. B&C's reported 0.610 ± 0.048 lies between these; their threshold rule is not stated.
Replication diagnostics complete; no changes to the primary pipeline."

## 2026-09-21 — STAGE 4 hold released  (decided by: user)
Specification (user): Logistic **A** = gate score + n_C + n_M + n_X; **B** = A + USFLUX and TOTUSJH relative 24h slopes.
`LogisticRegression`, L2, **C = 1.0, no tuning**; inputs standardised inside each training fold; episode weights
1/(eligible episodes in HARP). Grouped 5-fold CV by HARP on the dev cohort, seed 20260921. Report weighted log-loss and
AUC for A and B (per fold and pooled) and a region-bootstrap 95% CI on log-loss(A) − log-loss(B), 1,000 HARP resamples.
Supporting: score-matched pairs (caliper fixed before looking at trends). Exploratory: delayed vs true, descriptive
only. Also the first-episode sensitivity cohort. Write `frozen/frozen_spec.json`, hash it here. Stop at CHECKPOINT 4.

### Stage 4 implementation details — PRE-REGISTERED by me, BEFORE any trend or model result
1. **Folds:** the cohort's HARPs are split into 2 strata (>= 1 true-alarm episode / none), each shuffled with seed
   20260921 and dealt round-robin into 5 folds. Every episode of a HARP is in its HARP's fold.
2. **Standardisation:** mean / sd of each input, fitted on the training folds only (`StandardScaler`).
3. **Fit:** `LogisticRegression(penalty="l2", C=1.0, solver="lbfgs", max_iter=10000)`, `sample_weight` = episode weight.
4. **Metrics:** out-of-fold predicted probabilities. **Weighted log-loss** = Σ wᵢ·ℓᵢ / Σ wᵢ; **weighted AUC** =
   ROC AUC with `sample_weight`. Per fold (on that fold's held-out episodes) and pooled (all OOF predictions).
5. **Primary contrast:** Δ = log-loss(A) − log-loss(B) on the pooled OOF predictions (positive Δ = B better).
   **Bootstrap:** 1,000 resamples of HARPs with replacement (seed 20260921); predictions held fixed (no refit);
   weighted Δ recomputed per resample; percentile 95% CI.
6. **Score-matched pairs (supporting):** each true-alarm episode is matched 1:1, greedy nearest neighbour on the **gate
   score**, without replacement, to a false-alarm episode **from a different HARP**; true episodes processed in a seeded
   random order. **Caliper = 0.2 × SD of the gate score over the dev cohort's episodes** (computed from gate scores
   only). Reported: number of pairs, unmatched true episodes, max |score difference|; for each slope, mean and median
   of the paired difference (true − false) with a 95% bootstrap CI resampling pairs **clustered by the true episode's
   HARP** (1,000 resamples).
7. **Delayed vs true (exploratory, descriptive only):** weighted mean and median of gate score, n_C, n_M, n_X and the two
   slopes for true, delayed and other-false episodes; counts; no test statistic.
8. **First-episode sensitivity:** items 1–5 repeated on the first-eligible-episode cohort (weights 1).
9. **Stage 5 prediction rule for A and B (proposed; flagged for approval at CHECKPOINT 4):** by analogy with N2, test
   probabilities = mean of the 5 fold models' predicted probabilities; no refit on the full dev cohort.

## 2026-09-21 — STAGE 4 RESULTS (dev only) — CHECKPOINT 4
`stage4_models.py` (pre-registered details above). Rerun reproduces the out-of-fold cohort predictions byte-for-byte.
Test HARPs and years never loaded (asserted).

**PRIMARY cohort** (T1–T4; 547 episodes, 98 true; 180 HARPs, 41 with a true episode; weighted true 24.13 of 180):

| fold | episodes | true | HARPs | true HARPs | log-loss A | log-loss B | AUC A | AUC B | Δ = A − B |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 97 | 14 | 37 | 9 | 0.3377 | 0.3056 | 0.8209 | 0.8693 | 0.0320 |
| 1 | 93 | 17 | 36 | 8 | 0.2906 | 0.3228 | 0.8813 | 0.7956 | −0.0322 |
| 2 | 110 | 21 | 36 | 8 | 0.3924 | 0.3933 | 0.5884 | 0.6094 | −0.0009 |
| 3 | 132 | 30 | 36 | 8 | 0.3897 | 0.3573 | 0.6683 | 0.8178 | 0.0324 |
| 4 | 115 | 16 | 35 | 8 | 0.2551 | 0.2661 | 0.8841 | 0.7708 | −0.0110 |
| **pooled** | **547** | **98** | **180** | **41** | **0.3336** | **0.3293** | **0.7432** | **0.7695** | **0.0043** |

**Δ log-loss (A − B), pooled: 0.0043; HARP-bootstrap 95% CI [−0.0114, 0.0253]** (1,000 resamples).

**SENSITIVITY — first eligible episode per region** (180 episodes, 25 true, 180 HARPs):

| fold | episodes | true | log-loss A | log-loss B | AUC A | AUC B | Δ |
|---|---:|---:|---:|---:|---:|---:|---:|
| 0 | 36 | 5 | 0.3352 | 0.3674 | 0.7548 | 0.6903 | −0.0322 |
| 1 | 36 | 5 | 0.3844 | 0.3440 | 0.6581 | 0.8129 | 0.0404 |
| 2 | 36 | 5 | 0.3626 | 0.3273 | 0.7032 | 0.8258 | 0.0352 |
| 3 | 36 | 5 | 0.6270 | 0.6553 | 0.4839 | 0.4903 | −0.0283 |
| 4 | 36 | 5 | 0.3008 | 0.2690 | 0.8000 | 0.8516 | 0.0317 |
| **pooled** | **180** | **25** | **0.4020** | **0.3926** | **0.6521** | **0.7272** | **0.0094** |

**Δ pooled 0.0094; HARP-bootstrap 95% CI [−0.0162, 0.0435].**

**Score-matched pairs (supporting):** caliper **0.0747** (0.2 × SD of gate score over 547 episodes, fixed from scores
only before trends were examined); **83 pairs** from 98 true episodes (15 unmatched); max |score difference| 0.0733;
35 true HARPs. Paired difference (true − false), 95% CI clustered by true HARP (1,000 resamples):
- rel. slope USFLUX: mean 2.832e-3, median 1.858e-3, CI [−4.238e-3, 1.037e-2]
- rel. slope TOTUSJH: mean 3.294e-3, median 2.777e-3, CI [−3.848e-3, 1.188e-2]

**Exploratory, descriptive only** — weighted mean [median]:

| group | episodes | HARPs | weight | gate score | n_C | n_M | n_X | rel. slope USFLUX | rel. slope TOTUSJH |
|---|---:|---:|---:|---|---|---|---|---|---|
| true | 98 | 41 | 24.13 | −0.331 [−0.81] | 5.23 [4] | 1.46 [0] | 0.134 [0] | 0.0131 [0.00245] | 0.0164 [0.00218] |
| delayed | 47 | 26 | 13.04 | −0.724 [−0.936] | 4.37 [2] | 1.13 [0] | 0.115 [0] | 0.0129 [0.00497] | 0.0158 [0.00655] |
| other false | 402 | 160 | 142.83 | −0.916 [−0.973] | 2.10 [1] | 0.157 [0] | 0.00933 [0] | 0.00948 [0.000401] | 0.0109 [0.000123] |

**Frozen specification:** `frozen/frozen_spec.json` (tracked),
**SHA-256 `598be4fa9dc21eb309f9a3e89162f4d62e3c7d2e3c631ff1e119b79a7f964632`**. It fixes the labelled-file and split
hashes, gate features / scaling / SVM / threshold (−0.992496) / fold-model hashes, cohort rules T1–T4 (with the
`cohort.py` hash), models A and B, the caliper, the seeds, and the Stage 5 metrics.
**Awaiting approval.** Open item for approval: pre-registered item 9 — Stage 5 predictions for A and B = mean of the
5 fold models' probabilities, no refit.
**Test years untouched.**

## 2026-09-21 — CHECKPOINT 4 approved; Stage 5 prediction rule approved  (decided by: user)
**Approved: models A and B score the test set with the mean of the 5 fold models' predicted probabilities; no refit.**
Marked in `frozen/frozen_spec.json` (only the `models.test_prediction` field changed; `git diff` shows one line).
**New SHA-256 of `frozen/frozen_spec.json`: `1d20506849930dd52f7f77333f44e4f458a65d9946cb0007a1c603816785368d`**
(supersedes `598be4fa…`). No other changes to the frozen spec.

### Stage 5 execution details fixed BEFORE the test run (me; where the spec is silent)
- **Integrity check first:** the script recomputes every hash in `frozen_spec.json` (labelled file, split, gate fold
  models, `cohort.py`, A/B fold models) and stops if any differs.
- **Gate evaluation population:** scorable rows of test HARPs in the stated years; hour level = every row; **region level
  = one contingency entry per HARP: positive if >= 1 positive row, alarmed if >= 1 alarm hour** in that period/subset.
  TSS, HSS, FAR at both levels; hour- and region-level TSS with a HARP-bootstrap 95% CI, 1,000 resamples; TSS at
  decision value 0 at both levels.
- **Matched pairs:** the **frozen dev caliper 0.0747** (the Stage 4 spec said "caliper fixed on dev"; `frozen_spec.json`
  records the value), same matching procedure.
- **Primary Δ bootstrap: 10,000 HARP resamples** (as in `frozen_spec.json`); seed 20260921 throughout.
- **Robustness subsets (≤ 2 regions, all HARPs):** the gate's fold models score those rows (no refit); the cohort is
  built with T1–T4 from alarms in that subset's rows; models A and B (fold models, no refit) score it.
- **Run once:** the code is first exercised end-to-end on a DEV-period stand-in (2014, dev HARPs; outputs discarded, not
  test data) to remove coding errors; then the test run is executed exactly once.
- **Recorded before the test run (me):** cohort alarms/episodes are restricted to rows in the evaluation years; the
  24-h trend window at t uses every labelled row of the HARP, so an alarm early in an evaluation year can use SHARP
  features from the end of an excluded year (e.g. 2022-12-31 for a 2023-01-01 alarm). Features only — never labels —
  come from outside the evaluation years.
- **Dry run completed** (`stage5_test.py dryrun`: dev HARPs, 2013–2014, outputs in /tmp, discarded): every code path
  ran without error. Its numbers are a code check, not results.

## 2026-09-21 — STAGE 5 RESULTS: held-out test, run ONCE — CHECKPOINT 5 (results tables only, no interpretation)

`stage5_test.py test`: single execution, exit 0. **Every hash in `frozen/frozen_spec.json` verified before scoring.** Test HARPs 801; rows 2021–2024: 101,766; **unscorable 34 (0 positive), excluded**. Gate threshold −0.992496 (frozen); gate score = mean of the 5 fold models' decision values; A/B probabilities = mean of the 5 fold models; no refit.

### Gate (hour level = rows; region level = one entry per HARP; TSS CI = HARP bootstrap, 1,000 resamples)

| period | subset | level | threshold | N | positives | TSS | TSS 95% CI | HSS | FAR | TPR | FPR |
|---|---|---|---|---:|---:|---:|---|---:|---:|---:|---:|
| primary 2021/2023/2024 | single | hour | frozen −0.9925 | 53,356 | 1,976 | **0.5467** | [0.4120, 0.6598] | 0.3670 | 0.7021 | 0.6012 | 0.0545 |
| primary 2021/2023/2024 | single | hour | 0 | 53,356 | 1,976 | **0.3227** | [0.1994, 0.4338] | 0.3536 | 0.5832 | 0.3411 | 0.0184 |
| primary 2021/2023/2024 | single | region | frozen −0.9925 | 450 | 55 | **0.7284** | [0.6301, 0.8198] | 0.5236 | 0.5429 | 0.8727 | 0.1443 |
| primary 2021/2023/2024 | single | region | 0 | 450 | 55 | **0.4757** | [0.3390, 0.6101] | 0.5746 | 0.1818 | 0.4909 | 0.0152 |
| primary 2021/2023/2024 | <=2 | hour | frozen −0.9925 | 64,642 | 3,401 | **0.6089** | [0.5150, 0.6945] | 0.4233 | 0.6483 | 0.6783 | 0.0694 |
| primary 2021/2023/2024 | <=2 | hour | 0 | 64,642 | 3,401 | **0.3966** | [0.2806, 0.4968] | 0.4267 | 0.5057 | 0.4205 | 0.0239 |
| primary 2021/2023/2024 | <=2 | region | frozen −0.9925 | 528 | 87 | **0.7288** | [0.6591, 0.7950] | 0.5606 | 0.4868 | 0.8966 | 0.1678 |
| primary 2021/2023/2024 | <=2 | region | 0 | 528 | 87 | **0.4876** | [0.3818, 0.5932] | 0.5815 | 0.1538 | 0.5057 | 0.0181 |
| primary 2021/2023/2024 | all | hour | frozen −0.9925 | 77,085 | 6,955 | **0.6452** | [0.5829, 0.6986] | 0.4519 | 0.6087 | 0.7629 | 0.1177 |
| primary 2021/2023/2024 | all | hour | 0 | 77,085 | 6,955 | **0.4936** | [0.4066, 0.5660] | 0.4912 | 0.4657 | 0.5403 | 0.0467 |
| primary 2021/2023/2024 | all | region | frozen −0.9925 | 605 | 142 | **0.7266** | [0.6743, 0.7800] | 0.6029 | 0.4159 | 0.9296 | 0.2030 |
| primary 2021/2023/2024 | all | region | 0 | 605 | 142 | **0.6063** | [0.5285, 0.6873] | 0.6629 | 0.1495 | 0.6408 | 0.0346 |
| sensitivity incl. 2022 | single | hour | frozen −0.9925 | 71,862 | 2,381 | **0.5224** | [0.4115, 0.6256] | 0.3347 | 0.7331 | 0.5766 | 0.0543 |
| sensitivity incl. 2022 | single | hour | 0 | 71,862 | 2,381 | **0.2753** | [0.1582, 0.3900] | 0.3089 | 0.6233 | 0.2919 | 0.0166 |
| sensitivity incl. 2022 | single | region | frozen −0.9925 | 605 | 71 | **0.6812** | [0.5841, 0.7621] | 0.4813 | 0.5755 | 0.8310 | 0.1498 |
| sensitivity incl. 2022 | single | region | 0 | 605 | 71 | **0.4179** | [0.3015, 0.5368] | 0.5116 | 0.2439 | 0.4366 | 0.0187 |
| sensitivity incl. 2022 | <=2 | hour | frozen −0.9925 | 86,824 | 4,034 | **0.5942** | [0.5091, 0.6642] | 0.3916 | 0.6821 | 0.6636 | 0.0694 |
| sensitivity incl. 2022 | <=2 | hour | 0 | 86,824 | 4,034 | **0.3667** | [0.2669, 0.4579] | 0.3979 | 0.5347 | 0.3884 | 0.0218 |
| sensitivity incl. 2022 | <=2 | region | frozen −0.9925 | 709 | 110 | **0.7008** | [0.6330, 0.7669] | 0.5268 | 0.5176 | 0.8727 | 0.1720 |
| sensitivity incl. 2022 | <=2 | region | 0 | 709 | 110 | **0.4783** | [0.3880, 0.5717] | 0.5666 | 0.1912 | 0.5000 | 0.0217 |
| sensitivity incl. 2022 | all | hour | frozen −0.9925 | 101,732 | 7,972 | **0.6446** | [0.5875, 0.6994] | 0.4335 | 0.6338 | 0.7559 | 0.1113 |
| sensitivity incl. 2022 | all | hour | 0 | 101,732 | 7,972 | **0.4828** | [0.4009, 0.5543] | 0.4776 | 0.4871 | 0.5252 | 0.0424 |
| sensitivity incl. 2022 | all | region | frozen −0.9925 | 801 | 172 | **0.7077** | [0.6555, 0.7581] | 0.5704 | 0.4510 | 0.9128 | 0.2051 |
| sensitivity incl. 2022 | all | region | 0 | 801 | 172 | **0.5913** | [0.5212, 0.6615] | 0.6474 | 0.1756 | 0.6279 | 0.0366 |

### Test cohort sizes (rules T1–T4)

| period | subset | episodes (T1) | alarm HARPs | excluded (no evaluable hour) | eligible episodes | true | false | delayed | regions | regions with true | region-weighted true |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| primary 2021/2023/2024 | single | 367 | 105 | 54 | 313 | 45 | 268 | 26 | 98 | 28 | 14.46 |
| primary 2021/2023/2024 | <=2 | 563 | 152 | 87 | 476 | 81 | 395 | 53 | 139 | 43 | 22.46 |
| primary 2021/2023/2024 | all | 971 | 226 | 126 | 845 | 180 | 665 | 92 | 212 | 86 | 45.89 |
| sensitivity incl. 2022 | single | 486 | 139 | 72 | 414 | 62 | 352 | 36 | 128 | 37 | 18.51 |
| sensitivity incl. 2022 | <=2 | 745 | 199 | 117 | 628 | 109 | 519 | 68 | 182 | 56 | 28.86 |
| sensitivity incl. 2022 | all | 1197 | 286 | 162 | 1035 | 215 | 820 | 113 | 267 | 102 | 54.28 |

All exclusions were "no evaluable hour"; none for `history_incomplete at t` or label-missing.

### Models A vs B (weighted; Δ = log-loss(A) − log-loss(B); CI = HARP bootstrap, 10,000 resamples)

| period | subset | cohort | episodes | true | HARPs | true HARPs | log-loss A | log-loss B | **Δ** | **Δ 95% CI** | AUC A | AUC B |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|
| primary 2021/2023/2024 | single | all eligible (T2) | 313 | 45 | 98 | 28 | 0.3686 | 0.3737 | **-0.0051** | **[-0.0201, 0.0094]** | 0.8111 | 0.7974 |
| primary 2021/2023/2024 | single | first episode per region | 98 | 13 | 98 | 13 | 0.4066 | 0.4091 | -0.0025 | [-0.0265, 0.0210] | 0.7593 | 0.7330 |
| primary 2021/2023/2024 | <=2 | all eligible (T2) | 476 | 81 | 139 | 43 | 0.3747 | 0.3814 | -0.0067 | [-0.0182, 0.0049] | 0.8089 | 0.7829 |
| primary 2021/2023/2024 | <=2 | first episode per region | 139 | 19 | 139 | 19 | 0.4022 | 0.4044 | -0.0022 | [-0.0200, 0.0152] | 0.7618 | 0.7276 |
| primary 2021/2023/2024 | all | all eligible (T2) | 845 | 180 | 212 | 86 | 0.4250 | 0.4260 | -0.0010 | [-0.0101, 0.0078] | 0.8083 | 0.8103 |
| primary 2021/2023/2024 | all | first episode per region | 212 | 45 | 212 | 45 | 0.4841 | 0.4819 | 0.0022 | [-0.0118, 0.0157] | 0.7599 | 0.7561 |
| sensitivity incl. 2022 | single | all eligible (T2) | 414 | 62 | 128 | 37 | 0.3726 | 0.3741 | -0.0015 | [-0.0159, 0.0133] | 0.7994 | 0.7686 |
| sensitivity incl. 2022 | single | first episode per region | 128 | 18 | 128 | 18 | 0.4270 | 0.4216 | 0.0054 | [-0.0199, 0.0336] | 0.7247 | 0.6879 |
| sensitivity incl. 2022 | <=2 | all eligible (T2) | 628 | 109 | 182 | 56 | 0.3864 | 0.3899 | -0.0035 | [-0.0149, 0.0079] | 0.7986 | 0.7664 |
| sensitivity incl. 2022 | <=2 | first episode per region | 182 | 27 | 182 | 27 | 0.4487 | 0.4462 | 0.0026 | [-0.0174, 0.0244] | 0.7075 | 0.6724 |
| sensitivity incl. 2022 | all | all eligible (T2) | 1035 | 215 | 267 | 102 | 0.4278 | 0.4277 | 0.0001 | [-0.0085, 0.0088] | 0.7981 | 0.7955 |
| sensitivity incl. 2022 | all | first episode per region | 267 | 54 | 267 | 54 | 0.4992 | 0.4942 | 0.0050 | [-0.0102, 0.0210] | 0.7267 | 0.7239 |

Primary analysis = first row (primary years, single-region, all eligible episodes).

### Score-matched pairs (primary, single-region; frozen dev caliper 0.0747)

41 pairs from 45 true episodes (4 unmatched); max |score difference| 0.0469; 26 true HARPs.

| slope | mean paired difference (true − false) | median | 95% CI (mean; clustered by true HARP, 1,000) |
|---|---:|---:|---|
| rel_slope_usflux | 0.002191 | 0.002213 | [-0.003941, 0.007951] |
| rel_slope_totusjh | 0.002309 | -0.0006981 | [-0.003397, 0.00864] |

### Delayed vs true (primary, single-region; descriptive only; weighted mean, [median] for slopes)

| group | episodes | HARPs | weight | gate score | n_C | n_M | n_X | rel. slope USFLUX | rel. slope TOTUSJH |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| true | 45 | 28 | 14.46 | -0.342 | 5.22 | 0.613 | 0.207 | 0.0077 [0.00259] | 0.0114 [0.00205] |
| delayed | 26 | 20 | 8.11 | -0.661 | 2.47 | 0.452 | 0.0411 | 0.0243 [0.00867] | 0.0283 [0.00666] |
| other false | 242 | 87 | 75.42 | -0.875 | 1.97 | 0.243 | 0.0155 | 0.0119 [0.00311] | 0.013 [0.00199] |

### Output files (data/stage5/, SHA-256)

- `data/stage5/cohort_sizes.csv` `8ef8337d837f71ac4acfa356beff11ebbcc06b834150438f143fbbd8dde480c5`
- `data/stage5/cohort_test_primary.csv` `49fe435c24264c291b010a223519ebad4b1237a08d85976b68b3ef945a86c083`
- `data/stage5/delayed_descriptive.csv` `78bd507ac06a07d86c00a34387cf8f14c75edf4192b725e475aa7665ea60ccfa`
- `data/stage5/gate_gate.csv` `5e88db8d7075302ebdd55ccb8088485fcd00a1e4893bc92fbaa028cf214c2054`
- `data/stage5/matched_pairs_test.csv` `15acc54d50bd58cd3eef08091f72ef3c1ffc397a36d96563325487ef364e8aa4`
- `data/stage5/models_b.csv` `77cd1e0db0f2e7eacf04f785c7c6761e212efd63f055582931a7b72363b52e6b`
- `data/stage5/pairs_summary.csv` `d0dd9b6c9d1daeadee50866b1c53ea56749ca796ea251653a456962832d00cbf`
- `stage5_test.log` (console output) is tracked in git.
