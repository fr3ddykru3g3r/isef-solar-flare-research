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
