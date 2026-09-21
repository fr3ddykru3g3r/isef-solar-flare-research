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
