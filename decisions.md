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
| TOTBSQ   | **not a JSOC keyword** [corrected 2026-09-22: not a SHARP keyword; available in JSOC `cgem.lorentz`] | | MEANGAM | fetched |
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
computed from the vector-field image data. Three are in the 13-feature SVM set (TOTBSQ, TOTFZ, EPSZ). [**Corrected 2026-09-22:** not SHARP keywords, but available as keywords in JSOC `cgem.lorentz`; see the 2026-09-22 correction entry.]
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
unavailable as keywords.** ("Reproduction" is withdrawn as a description.) [**Corrected 2026-09-22:** not SHARP keywords, but available as keywords in JSOC `cgem.lorentz`; see the 2026-09-22 correction entry.]
**The gate uses exactly these 10 features and no others** — B&C Table 1 "Included" features that exist
as SHARP keywords, in Table 1 rank order:

  1. TOTUSJH   2. TOTPOT   3. TOTUSJZ   4. ABSNJZH   5. SAVNCPP
  6. USFLUX    7. AREA_ACR 8. MEANPOT   9. R_VALUE  10. SHRGT45

(B&C ranks 1, 3, 4, 5, 6, 7, 8, 10, 11, 13; ranks 2 TOTBSQ, 9 TOTFZ, 12 EPSZ unavailable.) [**Corrected 2026-09-22:** not SHARP keywords, but available as keywords in JSOC `cgem.lorentz`; see the 2026-09-22 correction entry.]
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
| features | 13 | 10 (TOTBSQ, TOTFZ, EPSZ unavailable [corrected 2026-09-22: not SHARP keywords; available in `cgem.lorentz`]) |
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
| features | 13 highest-F-score of Table 1 (p.24) | NOT MATCHABLE — 10 of 13 (TOTBSQ, TOTFZ, EPSZ not keywords [corrected 2026-09-22: not SHARP keywords; available in `cgem.lorentz`]) |
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

## 2026-09-21 — PRIMARY RESULT FINAL; next phase  (decided by: user)
**The primary result (Stage 5, CHECKPOINT 5) stays unchanged and is recorded as FINAL.**
**No new analysis is to be run on 2021–2024.**

**Step A (dev only, exploratory):** within the dev cohort, logistic models with (i) gate score only, (ii) C/M/X history
only, (iii) score + history; same CV, weights and regularisation as Stage 4; weighted log-loss and AUC; table only.
(Note (me): (iii) has the same inputs as model A, so it reproduces Stage 4's A.)

### Step B — PRE-REGISTERED 2026-09-21, before R has been computed anywhere  (decided by: user; details marked)
- **Feature R** = hours since the region's most recent **C1+ flare (K2 scale)** before t, **capped at 48 h** (R = 48 if
  none in the window); used as **log(1 + R)**.
  Details (me, fixing the literal reading): "region" = the NOAA regions in the HARP's `NOAA_ARS` at t (ANY rule, as for
  labels and history); flare time = **start time** (as for labels and history); "before t" = start in **(t − 48 h, t)**;
  R = (t − start of the most recent such flare) in hours, else 48; C1+ = harmonised K2 flux >= 1e-6; SWPC originals.
- **Hypothesis: model C = A + log(1 + R) beats A.** Model C: same estimator, standardisation, weights, CV and seeds as A.
  "Beats" = weighted log-loss(A) − log-loss(C) > 0, with a HARP-bootstrap 95% CI (same procedure as the primary).
- **Operating point, fixed on dev:** report the false-alarm count for A vs C at the dev threshold that gives C the same
  true-alarm rate as A.
  **For confirmation (me): A's own operating threshold τ_A is not specified.** Proposed: τ_A = the threshold maximising
  weighted TSS on A's dev out-of-fold probabilities (the same rule used for the gate); τ_C = the threshold on C's dev
  out-of-fold probabilities giving the same weighted true-alarm rate (TPR) as A at τ_A; report false alarms (episodes
  and region-weighted) at τ_A and τ_C. Both thresholds fixed on dev.
- **Evaluation set:** not yet specified — 2021–2024 is closed (above); the candidate is the fresh confirmation set of
  Step C. **Nothing in Step B is computed until the user confirms τ_A and the evaluation set.**

**Step C (report only; fetch nothing):** feasibility of a fresh confirmation set 2025-01-01 → latest available: SHARP
keyword availability, SWPC report coverage, and whether SWPC 4-digit Reg# → +10000 still holds past region 14000
(verify against SHARP NOAA_ARS).

### STEP A — RESULTS (dev only, exploratory; table only)
`stepA_dev.py` (reuses `stage4_models.cv`; `stage4_models.py` given a main guard and verified to reproduce its outputs
byte-for-byte; all 10 frozen A/B fold models still match their frozen hashes; Step A saves no models).

| cohort | model | episodes | true | weighted log-loss | weighted AUC |
|---|---|---:|---:|---:|---:|
| primary (all eligible, region-weighted) | (i) gate score only | 547 | 98 | 0.3260 | 0.7403 |
| primary (all eligible, region-weighted) | (ii) history only (n_C, n_M, n_X) | 547 | 98 | 0.3764 | 0.7260 |
| primary (all eligible, region-weighted) | (iii) score + history (= A) | 547 | 98 | 0.3336 | 0.7432 |
| first eligible episode per region | (i) gate score only | 180 | 25 | 0.3182 | 0.7551 |
| first eligible episode per region | (ii) history only | 180 | 25 | 0.4552 | 0.6658 |
| first eligible episode per region | (iii) score + history (= A) | 180 | 25 | 0.4020 | 0.6521 |
Per-fold log-losses in `data/stage4/stepA_dev.csv`. (iii) reproduces Stage 4's model A exactly.

### STEP C — feasibility of a confirmation set 2025-01-01 → latest (report only; nothing fetched)
Checked with metadata only: JSOC series description, NCEI directory listings (names/dates), and the local cache.

| item | finding | status |
|---|---|---|
| SHARP keywords, `hmi.sharp_cea_720s` | series live on JSOC (prime keys HARPNUM, T_REC); latest T_REC **not checked** — requires a record query | **unverified** without a (one-record, keyword-only) query |
| SWPC daily event reports (NCEI) | 2025: all 12 month directories; 2026: through **2026-09-20**; spot-checked months complete (2025-01, -02, -03, -06; 2026-01, -08) **except 2025-12: files for the 1st–29th only (12-30 and 12-31 absent)** | available; 2 missing days → the label-missing rule (C) would apply |
| GOES XRS 1-min science (empty-day rule) | GOES-18: 2022–2026; GOES-19: 2024–2026; GOES-16: to 2025 | available; Table 11 lists **GOES-18 primary / GOES-19 secondary from 2025-04-07** (already transcribed) |
| SWPC Reg# → +10000 past region 14000 | local cache ends 2025-01-02; highest region seen: SWPC 13947 (Reg# 3947), SHARP `NOAA_ARS` 13960 — **region 14000 is not in the cache** | **unverified** — needs SWPC reports and SHARP `NOAA_ARS` from after ~14000 was assigned |
| flare scale 2025+ | XRA from GOES-18/19 = true scale; `swpc.py` already treats G16–G19 as true scale (K2: used as reported) | consistent, no change needed |
Proposed minimal checks, **not run** (each a fetch, awaiting approval): (1) one keyword-only JSOC query for the latest
`hmi.sharp_cea_720s` T_REC; (2) SWPC reports for a few days around the first region ≥ 14000 plus a keyword-only SHARP
`NOAA_ARS` query for the same days, to confirm the Reg# rule. **No analysis run on 2021–2024.**

## 2026-09-21 — Confirmation-set decisions  (decided by: user; before any 2025+ data is fetched or R is computed)
1. **τ_A approved:** the threshold maximising TSS on A's dev out-of-fold predictions.
2. **Confirmation set = 2025-01-01 → the latest date with SHARP + SWPC + GOES coverage.** The end date is determined
   from check 1 below and **frozen in this log BEFORE fetching**. Identical rules: K2 scale; CHECK 5 per calendar year
   (>= 90% rule; failing years excluded); missing-day and empty-day rules; frozen gate and threshold; cohort rules
   T1–T4; single-region primary.
3. **Pre-registered confirmatory tests on the 2025+ set:**
   (a) **Replication of the primary:** log-loss(A) − log-loss(B), region-bootstrap 95% CI, 10,000 HARP resamples.
   (b) **Step B:** log-loss(A) − log-loss(C), same CI; plus the false-alarm count for A vs C at τ_A's dev true-alarm rate.
   **Models A, B, C are trained on dev only (2010–2019) and frozen before 2025+ is scored.**
4. **Step A recorded as exploratory:** on dev, the gate score alone had the lowest log-loss; adding the C/M/X counts
   did not improve it.
5. **Approved: the two keyword-only checks** (latest SHARP T_REC; SWPC Reg# convention around the first region >= 14000
   vs SHARP NOAA_ARS). Report, then stop.
**No 2025+ data is fetched until the user approves the frozen end date and the check results.**

### CHECK RESULTS — confirmation-set feasibility (keyword-only; approved checks)
**Check 1 — coverage end dates**
- **SHARP (`hmi.sharp_cea_720s`):** latest T_REC = **2026-08-17 00:00:00 TAI**. Found by keyword-only queries (T_REC,
  HARPNUM): daily sampling finds no records 2026-08-25 → 09-22 and the latest at 08-17 00:00; an hourly query of
  08-17 → 08-25 returns only the 08-17 00:00 slot (20 records).
- **SWPC daily reports (NCEI):** through **2026-09-20**; archive lacks **2025-12-30 and 2025-12-31** (the missing-day rule applies).
- **GOES XRS 1-min science:** GOES-18 and GOES-19 through **2026-09-20** (latest daily files d20260920).
- **Limiting source: SHARP.**

**Check 2 — SWPC Reg# convention past region 14000** (SWPC reports 2025-02-18 → 02-24 downloaded into the cache; SHARP
`NOAA_ARS` keyword query, same days, hourly)
- SHARP: region 14000 first appears 2025-02-20 (daily sampling); neighbours 13995–14005 first appear 02-12 → 02-22.
  Region 14001 already appears on 2025-02-08, merged with 13989 in HARP 12732 — consistent with `NOAA_ARS` being
  filled retroactively once NOAA assigns a number (noted, no action).
- SWPC prints the crossing as **4-digit "4000", "4001"**; +10000 → 14000, 14001, both present in SHARP.
- XRA events parsed in these 7 days: 66, 63 with a region; **their converted regions (13990, 13991, 13992, 13996, 13997,
  13998, 14000, 14001) all appear in SHARP `NOAA_ARS`.**
- **Region column of every XRA and FLA line: 95 of 95 are 4-digit.** The 5-digit values and six unmatched 4-digit
  values found by a broad last-token scan (1100, 1700, 2000, 2500, 3200, 3600, 14000, 23000) are all **RBR radio-burst
  fluxes**, not regions; the parser reads XRA lines only, so they cannot reach labels.
- **Result: the rule Reg# < 10000 → +10000 holds past region 14000.** (It would fail at region 20000; not reached.)

**PROPOSED frozen end date (me; awaiting user approval — NOT yet frozen, nothing fetched beyond the checks):**
confirmation set = **T_REC from 2025-01-01 00:00 TAI up to but not including 2026-08-17 00:00 TAI** (last full SHARP day
2026-08-16). SWPC and GOES cover every 24-h label window and 48-h history window in that span (SWPC to 2026-09-20; the
history window at the start uses 2024-12-30/31 reports, already cached). The JSOC query will use an end of
2026-08-16_23:00_TAI, because JSOC ranges include both ends (see the month-boundary duplicate fix). Calendar years for
CHECK 5: 2025 (full) and 2026 (2026-01-01 → 2026-08-16, partial).

## 2026-09-21 — CONFIRMATION SET FROZEN  (decided by: user; recorded before any 2025+ fetch beyond the checks)
**Confirmation set = T_REC 2025-01-01 00:00 TAI → 2026-08-16 23:00 TAI.** The JSOC query end is inclusive at 23:00, to
avoid boundary duplicates. Approved by the user; frozen from this entry.

**`NOAA_ARS` (user):** SHARP `NOAA_ARS` appears to be filled retroactively. It is used **only for flare–region
linking** (labels, history, the single-region/mapping status that defines subsets), **never as a model input**.
(The gate uses the 10 SHARP features; models A/B/C use the gate score, n_C/n_M/n_X, and trends/R.)

**STEP 1 (data only; no gate scoring, no cohort, no R):** fetch SHARP keywords (original set + the 10 extras) in
resumable monthly chunks with the same record-set pattern and a boundary-duplicate check; fetch SWPC reports and GOES
XRS for the period (+48 h before, +24 h after where available); build labels with identical rules (K2, missing-day,
empty-day, history_incomplete, region_group); run CHECKS 1–5, CHECK 5 per calendar year (2025; 2026 partial) with the
90% rule, excluding failing years per L; report per year and hash the new raw and labelled files. STOP after Step 1.

## 2026-09-21 — CONFIRMATION SET, STEP 1 RESULTS (data only; no gate scoring, no cohort, no R)

**Fetched / built**
- SWPC daily reports 2024-12-29 → 2026-08-18 (593 files for 2025–2026). **404 days: 2025-12-30, 2025-12-31** (added to
  `_missing_days.txt`; rule C → label-missing and history-incomplete). **Empty-report days in 2025–2026: 0.**
- **GOES XRS: not fetched.** GOES is read only to classify empty-report days (rules E, H, I); a 404 day is missing
  without a GOES check (rule C). With zero empty-report days no rule reads GOES in this period. The empty-day table is
  unchanged. (Deviation from the instruction's "fetch GOES XRS", stated here; available on request.)
- SHARP extras (`fetch_extra.py 2025-01-01 2026-08-17`): 20/20 chunks. SHARP keywords + labels (`run_all.py`), 20 monthly
  chunks, same record-set pattern; **final chunk queried to 2026.08.16_23:00_TAI** via `JSOC_END_OVERRIDE` (applied only to
  the chunk whose end is 2026-08-17). **Boundary-duplicate check:** 282 raw / 76 labelled duplicate rows, all identical
  copies, dropped.
- Code changes (defaults unchanged; a default 2014-01 rebuild is byte-identical): `JSOC_END_OVERRIDE` in
  `build_dataset.py` / `fetch_extra.py`; `CHUNK_RANGE` in `chunks.py`; GOES-19 added to `goes_xrs.BASE`; `join_report.py`
  derives years and output file from the chunk range (the 2010–2024 table is never overwritten); CHECK 1 now uses the
  first X flare with >= 1 labelled row in its 24-h window (see below).

**CHECKS on the confirmation set: 1 PASS, 2 PASS, 3 descriptive, 4 PASS, 5 PASS.**
- CHECK 1 first **failed on event selection, not labels**: it took the first X flare of the padded flare list
  (X1.5, 2024-12-30), whose 24-h window precedes every confirmation row, so "all 0 rows labelled 1" was false. Fixed to
  the first X flare with a labelled row in [t0−24h, t0): X2.0, 2025-02-23 19:22, NOAA 14001 → HARP 12755; **12 of 12 rows
  in [t0−24h, t0) labelled 1**. The same fix on 2014-01 selects the original event (X1.2, HARP 3563; 21/21) — unchanged.
- CHECK 2: median USFLUX positive/negative 6.42×, TOTUSJH 7.15×.
- CHECK 3: 49,935 rows, 402 HARPs, 68 with a positive row.
- CHECK 4: missing-mapping rows median USFLUX 0.026× mapped; 1.0% above the mapped median.
- **CHECK 5 per calendar year (>= 90%): 2025 — 356 M1+, 21 unknown region, 94.1% usable → USABLE; 2026 (to 08-16) —
  205 M1+, 7 unknown, 96.6% → USABLE. No year excluded.** %in_SHARP 100% / 99.5%; dups 1 / 0.

**Exclusions by reason** (UTC year; sequential as in the pipeline)

| year | raw rows | QUALITY != 0 | \|LON\| > 45 | mapping missing | label-missing day | → labelled | history_incomplete (kept) |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2024* | 15 | 0 | 4 | 1 | 0 | 6 | 0 |
| 2025 | 140,567 | 15,653 | 29,094 | 38,541 | 320 | 32,830 | 0 |
| 2026 | 70,474 | 8,091 | 14,482 | 18,536 | 0 | 17,099 | 237 |

**Per year by region subset** — rows / positive rows / HARPs / positive HARPs

| year | single (primary) | <= 2 | all |
|---|---|---|---|
| 2024* | 2 / 0 / 2 / 0 | 4 / 0 / 4 / 0 | 6 / 1 / 6 / 1 |
| 2025 | 21,303 / 390 / 185 / 12 | 27,770 / 1,073 / 232 / 28 | 32,830 / 1,843 / 267 / 46 |
| 2026 | 12,398 / 468 / 104 / 11 | 14,930 / 636 / 122 / 17 | 17,099 / 847 / 137 / 22 |

Distinct positive HARPs over 2025 + 2026 (single / <= 2 / all): **23 45 68**.

**\* Overlap with the 2021–2024 test data (flagged for the user; nothing excluded yet).** The frozen start, 2025-01-01
00:00 TAI, is **2024-12-31 23:59:23 UTC**, and the 2024-12 chunk of the 2010–2024 dataset already contains that slot
(JSOC ranges include both ends). **15 raw / 6 labelled rows are in both files** — identical in every column. They are the
"2024" rows above. **6 HARPs** appear in both 2021–2024 and the confirmation set: all 6 have the overlapping slot, and the same 6 also have
2025 rows (6 of the 267 HARPs with 2025 rows); none of the 137 HARPs with 2026 rows is in 2021–2024.

**Hashes (SHA-256)**
- `data/raw_sharp_20250101_20260817.csv` `d6dc70b837fe0716e3ef0d31b735e70bb2a5c2e5a6ec7633c3412c0e05c779c2`
- `data/labelled_20250101_20260817.csv` `1f6673956db3599616fe4d04fbd14b285a383737156a49d393f6c5d617c49263`
**Stopped after Step 1.** No gate scoring, no cohort, no R.

## 2026-09-21 — DIAGNOSTIC D8, pre-declared  (decided by: user; dev period only; primary result untouched)
Identical to D7 (B&C period May 2010 – May 2014, their sample definition, N/P 16.5, random 70/30, 1,000 repeats,
QUALITY <= 65536, ±68°, 10 features, median/std scaling, C = 4, γ = 0.075, tol = 1e-8), **but C1/C2 = 15.0 and decision
value 0 (B&C Table 3 setting).** Then ONE comparison table, operational case, mean ± sd over 1,000 repeats: rows TSS,
recall, precision, FPR, accuracy; columns B&C Table 2 | D7 | B&C Table 3 | D8. Table only.

### D8 — RESULTS and the D7/D8 vs B&C comparison (diagnostic; dev period only; primary result untouched)
B&C values were checked against the paper before use: **all ten user-supplied operational values match** Table 2
(p.34) and Table 3 (p.35). FPR is not reported by B&C; it is taken as 1 − recall(negative), with the same sd.
D7 was rerun with full confusion counts (`diag_d7.py --d8`) and **reproduces its saved TSS exactly**. D8 = D7 with
class weight positive:negative = 15.0 (decision value 0). Same catalogue (P 272, N 4,488) and the same 1,000 splits.
No split had zero positive predictions. Per-split counts in `data/diag/d7_counts.csv`, `d8_counts.csv`.

**Operational case, mean ± sd over 1,000 repeats**

| metric | B&C Table 2 (C1/C2 = 2) | our D7 (C1/C2 = 2) | B&C Table 3 (C1/C2 = 15) | our D8 (C1/C2 = 15) |
|---|---|---|---|---|
| TSS | 0.610 ± 0.048 | 0.527 ± 0.050 | 0.761 ± 0.039 | 0.716 ± 0.040 |
| recall | 0.627 ± 0.049 | 0.540 ± 0.051 | 0.832 ± 0.042 | 0.805 ± 0.042 |
| precision | 0.690 ± 0.049 | 0.717 ± 0.050 | 0.417 ± 0.037 | 0.356 ± 0.022 |
| FPR | 0.017 ± 0.004 | 0.013 ± 0.003 | 0.071 ± 0.008 | 0.089 ± 0.009 |
| accuracy | 0.962 ± 0.004 | 0.961 ± 0.004 | 0.924 ± 0.007 | 0.905 ± 0.008 |

## 2026-09-21 — Confirmation set PAUSED; decisions on overlap and subset  (decided by: user)
- **The 2025+ confirmation work is PAUSED.**
- **The 6 HARPs that also appear in 2021–2024 are excluded** from the confirmation set (this removes the 6 overlapping
  labelled rows of the 2025-01-01 00:00 TAI slot along with those HARPs' 2025 rows).
- **The <= 2-region fallback applies** to the confirmation set (single-region has 23 positive HARPs over 2025–2026,
  below the fallback's 40).
- Note (me): not yet applied to any file — the confirmation labelled file (`1f667395…`) is unchanged; the exclusion and
  subset choice will be applied when the work resumes.

## 2026-09-21 — D8 replication conclusion (me, record-keeping)
The user's message refers to a "D8 replication conclusion". The D8 results table is recorded above; **no conclusion
wording for D8 has been provided by the user**, so none is recorded here. To be added verbatim when supplied.

## 2026-09-21 — EUV/UV PILOT — exploratory, dev data only (2010–2019)  (decided by: user)
**Exploratory.** Dev data only; **2021–2024 and 2025+ data are not touched.**
- **STEP 1 — BADPIT specification from the paper (arXiv:2604.26036) only; code unavailable.** Extract the algorithm
  with page references (instrument/channel, cadence, baseline, thresholds (3σ and power-law), spatial rule (> 3 connected
  pixels), temporal rule (> 5 consecutive frames), saturation flag (> 12,000 DN), PIL mask (±150 G, 16 px dilation), AR
  mask (30 G), alignment/registration); list every unstated detail with one proposed choice each, marked for user
  approval; check for an archived official copy of the code (Zenodo, Software Heritage, arXiv ancillary files) and use
  no unofficial copies; identify BADPIT's 2 active regions and time windows. **CHECKPOINT 1; no downloads.**
- **STEP 2** (after CHECKPOINT 1 approval): 3 dev alarm episodes from the frozen dev cohort (1 true, 1 false, 1 delayed;
  gate scores within the caliper; |LON| <= 30° if possible); SHARP CEA Br at t and AIA cutouts over the HARP box for
  (t−24h, t] in BADPIT's channel at 12-min cadence via JSOC export (cutout mode); report size and wall time; save to
  `data/euv_pilot/` (untracked) with hashes.
- **STEP 3:** PIL mask from Br by BADPIT's rule, mapped onto the AIA frame (level 1.5 if needed; time offset/rotation);
  one overlay PNG per episode.
- **STEP 4:** per AIA frame, fraction of PIL-mask pixels above a TRAILING 3σ baseline (earlier frames only), and the same
  for the HARP box; plots vs time; frames during a GOES flare in progress flagged and excluded.
- **CHECKPOINT 2 (final): GO/NO-GO facts only**; no interpretation of true vs false (n = 3).
- JSOC export email: the message gives "YOUR_EMAIL" — a placeholder. **A registered JSOC address is needed before
  Step 2**; none is assumed.

## 2026-09-21 — EUV PILOT STEP 1: BADPIT specification (paper only) — CHECKPOINT 1
Source: André-Hoffmann, Korsós, Nindos, Patsourakos, Georgoulis & Erdélyi, "Brightenings AnD Polarity Inversion
Tracking (BADPIT) method…", arXiv:2604.26036 (22 pp., SOLA manuscript dated 26 June 2026). Page numbers are the
manuscript's. Content paraphrased with page references (not quoted at length).

### Official code
The paper links a GitHub repository for BADPIT and its desaturation tool (p.7, footnote 2:
`github.com/aandre-hoffmann/BADPIT`). **Checked 2026-09-21: the URL returns HTTP 404; Software Heritage has no archived
origin for it; Zenodo has no record matching "BADPIT"; the arXiv abstract page lists no ancillary files.**
**No official copy is available; no code of any kind was downloaded or used.**

### Specification table

| item | what the paper states (page) |
|---|---|
| magnetic data | **HMI line-of-sight magnetogram cutouts**, 0.5″/px, 12-min cadence (pp.4–5, Table 1); LoS is used because ARs are restricted to ±45° central-meridian distance (pp.4, 11) |
| EUV/UV data | AIA **Level 1.5**, co-aligned, cutouts via the JSOC export service following P. Young's procedure (p.4); 94, 131, 171, 193, 1600 Å (p.4) |
| channel used for the analysis | **94 Å** (p.13), chosen because TBs concentrate at the PIL there and the power-law TBs appear most consistently |
| AIA cadence | **12 s** (24 s for 1600 Å) (Table 1, p.5) |
| pre-processing | exposure-time normalisation → DN/s (p.4) |
| saturation | saturation = ≥ 16,000 DN; **pixels > 12,000 DN are flagged** (conservative, following Schwartz et al. 2015), together with saturation trails (detector y-axis streaks) and diffraction arms (along the PSF axes at ±40°, ±50°); flagged pixels are **replaced by linear interpolation in time, with a sinusoidal component added** so the corrected points do not trigger detection (pp.6–7) |
| candidate pixels | intensity peaks in each pixel's light curve over the field of view (p.8) |
| spatial rule | patch larger than **3 contiguous pixels** (> 5.67×10⁵ km²) (p.8) |
| temporal rule | persists for **more than five consecutive frames** (at least one minute at 12 s) (p.8) |
| 3σ threshold | per pixel, from the Gaussian distribution of that pixel's intensities **over the full observation period** (pp.8–9); the paper notes this makes it not directly usable for near-real-time monitoring (p.9) |
| power-law threshold | one global threshold per AR and channel, from the AR's intensity histogram over the whole period: the intensity where the histogram departs from a fitted power law y = a x^(−α) at high intensity, identified **qualitatively** from the residuals (increased spread or a high-intensity rollover) (pp.9–10); values in Table 2 (p.11) |
| PIL area (PIA) | two masks where \|B_LoS\| > **150 G** (one per polarity), each **dilated by 16 HMI pixels (8″)**; their overlap = PIA (p.12); following Schrijver (2007) |
| AR mask | \|B\| > **30 G**, chosen empirically to separate AR from quiet-Sun fields; applied to the AIA data (p.12) |
| magnetogram timing | Fig. 6 shows masks on an HMI magnetogram **averaged over 3 hours** (p.12) |
| counting | TBs counted per **1-hour** interval over the 24-hour window (pp.14–16) |
| alignment | data described as co-aligned Level 1.5 (p.4); **no registration or HMI→AIA mapping procedure described** |

### Unstated details — one proposed choice each, **for the user's approval** (none acted on)

| # | unstated detail | proposed choice |
|---|---|---|
| U1 | 3σ threshold form (μ + 3σ? Gaussian fit or sample moments?) | per-pixel **mean + 3 × sample SD** |
| U2 | contiguity of "> 3 contiguous pixels" | **8-connectivity; >= 4 pixels** |
| U3 | what must persist "> 5 consecutive frames" (a pixel, or a patch that moves) | a patch whose pixels **overlap by >= 1 pixel between consecutive frames**, for **>= 6 frames** |
| U4 | desaturation sinusoid (amplitude, period) and the geometry used to flag trails and diffraction arms | **do not interpolate**: exclude pixels > 12,000 DN, and flag the frame if any pixel in the HARP box exceeds 12,000 DN |
| U5 | power-law fit range and the deviation point (qualitative in the paper) | **not used in the pilot** (Step 4 uses a trailing 3σ only); if needed later: fit between the median and 99th percentile, deviation = first bin above the range with residual > 3 × residual RMS |
| U6 | dilation structuring element for 16 px | **disk of radius 16 px** |
| U7 | single magnetogram vs a 3-hour average for the masks | **the single magnetic record at t** (as in the pilot brief) |
| U8 | HMI→AIA mapping | reproject the mask with the WCS headers (`reproject`), after **differential rotation** from the magnetogram time to each AIA frame time; AIA registered to level 1.5 with `aiapy` |
| U9 | how the 30 G AR mask is applied ("through visual inspection") | not used in the pilot: the **HARP box** is used as the region (as in the brief) |
| U10 | cutout tracking (fixed box vs following rotation) | JSOC cutouts **tracked** with solar rotation, centred on the HARP at t |

### Differences between the pilot brief and BADPIT (flagged, not resolved — the user's call)
1. **Magnetic data:** the brief uses **SHARP CEA Br**; BADPIT uses **HMI LoS** magnetogram cutouts at 0.5″/px. The 150 G / 30 G
   thresholds and the 16-px dilation were set on LoS data.
2. **Cadence:** the brief uses AIA at **12 min**; BADPIT uses **12 s**. "> 5 consecutive frames" means ~1 minute at 12 s but
   ~1 hour at 12 min, and the per-pixel intensity distributions differ. At 12 s, a 24-hour window is ~7,200 frames per
   channel per episode (60× the 12-min volume).
3. **Baseline:** the brief's trailing 3σ baseline is causal; BADPIT's 3σ uses the full period, including frames after t.
4. **Channel:** BADPIT's analysis channel is 94 Å (the brief says "BADPIT's channel").

### BADPIT's 2 active regions (for later validation)

| NOAA AR | role | window (UT) | position | period in this project |
|---|---|---|---|---|
| 11429 | flaring (C, M; two X flares starting just after the window) | 2012-03-06T00:00 → 2012-03-07T00:00 | N17E27 at 03-06 00:00 | **dev (2010–2019)** |
| 13186 | non-flaring (no ≥ C1 in the window or ±48 h) | 2023-01-16T00:00 → 2023-01-17T00:00 | N25W15 at 01-16 18:58 | **2023 — inside the 2021–2024 test years** |
**Conflict:** validating against AR 13186 would read 2023 data, which the pilot instruction forbids. AR 11429 is usable.
Also: AR 11429 lies at ~E27 at the start of its window, i.e. inside ±30°.
**No downloads made. Stopped at CHECKPOINT 1.**

## 2026-09-21 — EUV PILOT decisions, part 1  (decided by: user; recorded BEFORE any EUV download)
**Exploratory; dev data (2010–2019) only for all EUV development.**
- **D8 conclusion (user, verbatim):** "Same-period reproduction with C1/C2 = 15: D8 TSS 0.716 ± 0.040 vs B&C Table 3
  0.761 ± 0.039, with the same recall/precision trade-off; together with D7 (0.527 vs 0.610), our reproduction is
  consistently 0.05–0.08 lower, plausibly from 3 unavailable features [corrected 2026-09-22: available in `cgem.lorentz`], catalogue, and flare-location differences."
- **JSOC export email:** provided by the user for JSOC export requests.
- **U1–U10 approved as proposed.**
- **BADPIT power-law threshold dropped** (not algorithmic); **3σ only.**
- **Magnetic data for PIL masks: line-of-sight, as BADPIT.** The user asked to confirm that `hmi.sharp_720s` has a LoS
  magnetogram segment — answered below.
- **The user's message was cut off** after that sentence; the remaining decisions are not yet received. No EUV download
  until they are.
- **Answer (me): `hmi.sharp_720s` has a line-of-sight `magnetogram` segment — provisional.** The JSOC metadata call
  (`drms` `info`) failed server-side on 2026-09-21 ("No space left on device" in JSOC's database). The failed query
  itself, returned in the error, lists the series' segment columns: `magnetogram` is segment 0 (`magnetogram_bzero`,
  `magnetogram_bscale`), followed by `bitmap`, `dopplergram`, `continuum` and the inversion segments (`field`,
  `inclination`, `azimuth`, …). To be confirmed with a clean metadata call once JSOC recovers.
  **JSOC was returning database disk-full errors at this time** — relevant to export feasibility.

## 2026-09-21 — EUV PILOT decisions, part 2  (decided by: user; recorded BEFORE any EUV download)
1. **Primary EUV measure = "PIL-localised EUV variability" at 12-min cadence** (not BADPIT's 12-s transient detection).
   For (t−24h, t]: AIA **94 Å** cutouts (**1600 Å secondary**) covering the HARP; PIL-area mask from the
   **`hmi.sharp_720s` LoS magnetogram at t** (±150 G, 16 px dilation; 30 G AR mask), mapped to the AIA frames with
   differential rotation. Per episode: mean intensity and the SD of the **detrended** intensity, inside the PIL mask and
   in the whole HARP box; frames during a GOES flare already in progress excluded; **>= 80% of frames required**.
   **Primary feature = PIL variability / whole-HARP variability.** Described as **"motivated by BADPIT and Leka et al."**,
   not as BADPIT.
2. **Cadence cost test:** in the pilot, **also run 12 s over (t−6h, t]** on the same 3 episodes, **process-and-delete**
   (keep only per-frame results and overlays). Record download time, size and processing time per episode for both
   cadences, and projected totals for **547 dev + ~400 2025+ episodes**. **The full-study cadence will be chosen on cost
   only, before any true-vs-false comparison.**
3. **Baseline: trailing (past frames only) for everything used in forecasting.** BADPIT's whole-window baseline only
   for the validation reproduction.
4. **AR 13186 (2023-01-16): exception allowed for method validation only** (reproducing BADPIT's flaring vs quiescent TB
   counts at 12 s). Reason (user): 2021–2024 was reserved for the magnetic test, which is complete; the EUV
   confirmatory test will use 2025+. **No alarms, labels or hypotheses from 2021–2024 are used.** The validation
   reproduction can wait until after the pilot.
5. **AARP (NWRA AIA Active Region Patches): metadata check only** — date coverage, times, channels, file sizes.
6. **JSOC outage:** confirm the LoS segment with a clean metadata call when JSOC recovers. **If exports fail, wait and
   retry; do not switch data sources without asking.**
**Pilot:** 3 dev episodes (1 true, 1 false, 1 delayed; gate scores within the caliper; |LON| <= 30° if possible).
Deliver overlays (for the user's visual alignment check), time series and the cost table. **No true-vs-false
conclusions. Stop at CHECKPOINT 2.**

### Pilot implementation details fixed by me before any download — **for the user's approval**
- **P1 detrending:** for each mask (PIL, whole HARP box), the per-frame **mean** intensity series over (t−24h, t] minus
  its least-squares **linear** fit; variability = SD of the residuals. Primary feature = SD(PIL) / SD(HARP box).
- **P2 "flare already in progress":** a frame is excluded if its time lies inside the begin–end interval of **any SWPC
  XRA event of class >= C1.0 (K2 true scale), from any region** (GOES is disk-integrated).
- **P3 12-s cost test:** **94 Å only** (the primary channel); 1600 Å only at 12 min.
- **P4 AIA processing:** `aia.lev1_euv_12s` / `aia.lev1_uv_24s` exported as cutouts, registered to level 1.5 with
  `aiapy`, exposure-normalised (DN/s); pixels > 12,000 DN excluded and the frame flagged (U4).
- **P5 pilot metric (Step 4 of the pilot brief):** per frame, the fraction of mask pixels above a **trailing** per-pixel
  mean + 3 SD computed from **earlier frames only** (U1); needs >= 12 earlier frames before it is reported.
- **P6 episode choice:** from the frozen dev cohort, candidate triples (one true, one false, one delayed) whose gate
  scores lie within the caliper (0.0747) of each other and whose |LON_FWT| <= 30° at t; among them, the triple with the
  smallest gate-score spread, ties broken by earliest t. Chosen **before** any EUV data is seen.

### EUV pilot — pre-download results (me)
**Pilot episodes chosen by rule P6 (before any EUV data):** |LON_FWT| <= 30° at t: 62 true, 29 delayed, 296 other-false
episodes eligible. Smallest gate-score spread, three different HARPs (`data/euv_pilot_episodes.csv`):

| role | HARP | NOAA AR | t (UTC) | gate score | LON_FWT | LAT_FWT |
|---|---:|---:|---|---:|---:|---:|
| true | 4231 | 12089 | 2014-06-12 12:59:25 | −0.9917 | −9.3° | 17.5° |
| delayed | 6975 | 12645 | 2017-03-31 06:59:23 | −0.9917 | −11.4° | −9.9° |
| false | 3248 | 11856 | 2013-10-08 11:59:25 | −0.9917 | 2.2° | 8.3° |
Score spread 0.0001 (caliper 0.0747). Why these: the rule's minimum spread; all three are within 12° of disk centre.

**AARP metadata check (decision 5; no data downloaded).** Sources: data.gov record "NWRA AIA Active Region Patches
(AARP) Database"; SDAC directory listing `umbra.nascom.nasa.gov/contributed/AIA_AARPS/`; Dissauer et al. 2023, ApJ
(arXiv:2212.11251).
- **Coverage: 2010-06 → 2018-12** (103 month directories). **No 2019; no 2025+.**
- **Sampling:** daily, **11 images at 72-s cadence (13 min) per channel, centred at 15:48, 16:48, … 21:48 UT** (7 samples a
  day, one hour apart). Only that 6-hour daytime window is covered each day.
- **Channels:** 94, 131, 171, 193, 211, 304, 335, 1600 Å (1700 Å omitted).
- **Boxes:** HARP-based, with extended bounding boxes for coronal loops; full spatial sampling kept.
- **Files:** one FITS per AARP per day per channel (e.g. `2014.03.01_15:48:00_7h@1h_AARP3766_94.fits`), **58–90 MB each**
  in 2014-03; total ~9 TB; last updated 2026-09-08.
- Facts relevant to the brief: AARP cannot supply (t−24h, t] at 12-min cadence (daily 6-h window only), does not cover
  2019 or 2025+, and its cadence within a sample is 72 s.

**JSOC outage (decision 6):** the metadata call failed again with the same database disk-full error; per the decision,
waiting and retrying (no source switch).

### EUV pilot — approvals and amendments  (decided by: user)
- **P1, P3, P5, P6 approved.**
- **P2 amended:** a frame is excluded if it falls within the begin–end interval of **(a) any C1+ SWPC event attributed to the
  same NOAA region(s) as the HARP**, or **(b) any M1+ event from any region** (K2 true scale). **Report per episode how many
  frames each rule removes.**
- **P4 approved with clarification:** the **12,000 DN saturation cut applies to raw DN, before exposure normalisation.**
- **AARP: not used** (no 2019 or 2025+ coverage; 6 h/day only).
- Continue waiting on JSOC per decision 6; when it recovers: confirm the LoS segment, run the pilot, stop at CHECKPOINT 2.

### EUV pilot — preparation while JSOC is down (me)
- `swpc.py` now also parses each event's **end** time (needed for P2); labels verified **byte-identical** for 2014-01 and
  2024-05 chunks after the change.
- JSOC `im_patch` documentation (read from jsoc.stanford.edu): patches are **tracked by default** (`-t` disables tracking),
  no reprojection is done (plain cutout in original pixels) → U10 = tracked cutouts; level 1.5 via `aiapy` (P4).
- `euv_pilot.py` written; its pure-logic parts pass a self-test on synthetic data (PIL mask incl. a no-overlap case,
  P2 counts per rule, P5 trailing 3σ, P1 detrended SD, P4 saturation before normalisation).
- **JSOC export address:** JSOC's registration check returned "invalid or not registered" for the address the user
  supplied. This may be genuine or an effect of the outage (the check uses the same failing JSOC services). Registering
  the address is the user's action (JSOC sends a confirmation email); not done by me.

## 2026-09-21 — EUV PILOT DOWNLOAD decisions  (decided by: user; recorded BEFORE downloading)
**Scope: the 3 pilot episodes only** (HARP 4231, 6975, 3248; t as recorded).
**Items per episode:**
1. `hmi.sharp_720s` LoS **magnetogram** at the record nearest <= t (TAI), plus **bitmap**.
2. AIA **94 Å**, 12-min cadence, (t−24h, t], cutout around the HARP, tracked.
3. AIA **1600 Å**, 12-min cadence, (t−24h, t], cutout, tracked.
4. AIA **94 Å, 12-s cadence, (t−6h, t]**, cutout, tracked — cost test; process-and-delete allowed (per-frame results and
   overlays kept).
**Source rules:**
- Primary: **JSOC export** (drms, the email on record), method url, protocol FITS; AIA via **im_patch** cutouts, box = HARP
  bounding box + **50″ margin**, tracking on, reference time t. Keep the retry loop; start as soon as JSOC responds.
- **Fallback, AIA items 2–3 ONLY:** if JSOC is still failing **12 hours from this entry** (entry time 2026-09-21 22:43:34 IST; deadline
  **2026-09-22 10:43:34 IST**), fetch level-1 full-disk AIA via SunPy Fido from a VSO provider (e.g. SDAC), crop locally to the same box,
  delete the full-disk files; record the provider per file. **Not for item 4, not for HMI item 1 (JSOC only).**
- Never mix sources within one episode's item without recording it.
**Download discipline:** resumable (skip present and verified files); `data/euv_pilot/<HARP>/<item>/` (untracked);
manifest CSV (file, T_OBS, wavelength, exposure, source, size, SHA-256); checker (count vs expected — 12 min ~120, 12 s
~1,800 —, wavelength, time coverage, cutout contains the HARP box, gaps listed); wall time and bytes per item and episode.
**After download:** run the pilot (P1–P6 as approved; P2 amended; P4 raw-DN cut): overlays, time series, cost table with
projected totals for 547 dev + ~400 2025+ episodes. **No true-vs-false conclusions. Stop at CHECKPOINT 2.**

Notes (me):
- "Record nearest <= t (TAI)": each episode's t is the UTC form (hh:59:2x) of an hourly T_REC at hh+1:00:00 TAI, so the
  record at t is the episode row's own T_REC.
- **Gap in the fallback rule:** it triggers on "JSOC still failing". JSOC's registration check currently rejects the export
  address. If JSOC recovers but exports fail because the address is unregistered, that is not "JSOC failing"; **I will
  stop and ask** rather than use the fallback.
- `euv_download.py` written (JSOC path only; the approved AIA fallback is not implemented yet): resumable (skips items whose
  manifest files verify by SHA-256), manifest (`data/euv_pilot/manifest.csv`: file, T_OBS, wavelength, exposure, source,
  size, SHA-256), per-item download log (files, bytes, wall time, JSOC request id). HMI record = the episode row's own
  T_REC (4231: 2014.06.12_13:00:00_TAI; 6975: 2017.03.31_07:00:00_TAI; 3248: 2013.10.08_12:00:00_TAI).
  The AIA box is computed from item 1's WCS, so AIA items run only after item 1.
- The JSOC retry loop now runs until JSOC answers or the fallback deadline (2026-09-22 10:43:34 IST).
- **Open question raised with the user (fallback geometry):** the approved fallback crops to "the same box" (HARP bounding
  box + 50″). That box comes from JSOC (the item-1 WCS or the patch-extent keywords, never fetched). If JSOC stays down,
  the box cannot be computed; the cache holds only the HARP's flux-weighted centre. Not resolved by me.

### 2026-09-22 08:05 IST — JSOC recovered; export address unregistered (decided by: me)
- JSOC `info('hmi.sharp_720s')` succeeded at 2026-09-22 08:05:21 IST. The segment `magnetogram` (int, Gauss, "magnetogram") is confirmed as the LoS field; the provisional confirmation is now final. `bitmap` is confirmed too.
- With JSOC up, `drms.Client(email='lc09.11146@gmail.com')` still returns "Email address is invalid or not registered". Exports cannot run.
- The fallback (items 2–3 only) covers "JSOC failing". It does not cover an unregistered address, and JSOC is no longer failing. So no fallback is used and no download has started. Waiting for the user to register the address (http://jsoc.stanford.edu/ajax/register_email.html) or supply a registered one.

### 2026-09-22 — JSOC parallel-export limit (fact, measured; recorded by: me)
- Three small exports (item-1 bitmaps, data already held) were submitted back to back. The first was accepted (JSOC_20260922_000476). The others got status 7: "User lc09.11146@gmail.com has 1 pending export requests (JSOC_20260922_000476); please wait until at least one request has completed before submitting a new one."
- So JSOC allows N = 1 pending export per registered address. The cost projections use N = 1 as the allowed value.

### 2026-09-22 — AIA pilot processing: implementation notes (decided by: me; **for the user's approval at Checkpoint 2**)
- **Level 1.5 on cutouts:** `aiapy.calibrate.register` refuses non-full-disk input ("Input must be a full disk image"). Its pixel operation is `Map.rotate(scale = cdelt/0.6", order=3)`, i.e. rotate to solar north and rescale to 0.6"/px. The surrounding recentre/crop is specific to full-disk images. I apply that same rotate/rescale to each cutout (euv_run.register_cutout), with missing = NaN.
- **Frame quality:** some frames are not covered by P1–P6. There is one zero-exposure frame per episode per channel at ~20:59 UTC (QUALITY 0x10000), and HARP 6975 has frames with QUALITY 0x40000/0x60000 on 2017-03-30 14:59–16:35 UTC (SDO eclipse season). Default: **frames with QUALITY != 0 are excluded**, counted separately (`excl_quality`). Zero-exposure frames cannot be normalised in any case.
- **P5 with moving masks:** the masks are reprojected per frame (differential rotation), so the trailing 3σ fraction for frame i uses frame i's mask. The baseline uses earlier valid frames only; P2- and quality-excluded frames give no metric and do not enter the baseline.
- **Flare events for P2:** SWPC events with begin in [t−2 d, t], so events that start before the window and end inside it are included.

### 2026-09-22 — Checkpoint 2 approvals and design fix (decided by: user)
- **Approved:** registration on cutouts (aiapy's register pixel operation applied to cutouts), exclusion of frames with QUALITY != 0, and the baseline rule (per-frame mask; excluded frames not in the baseline).
- **Optional:** apply `aiapy.update_pointing` before registration if it runs without JSOC DB issues; otherwise note it.
- **Design fix before any scaling.** The user decided this **from method reasoning, not from pilot values**.
  - The ratio SD(PIL)/SD(box) is replaced as the primary feature by **CV_PIL − CV_ctrl**.
  - CV = SD of the detrended mean-intensity series / mean intensity, over (t−24h, t].
  - ctrl = a same-area control mask inside the AR mask (30 G) and outside the dilated PIL, chosen by a fixed rule.
  - CV_PIL, CV_ctrl and CV_box are also reported. The 3 pilot episodes are recomputed with the new definition (facts only).
- **Full-study download plan: proposal only, not started.** Group dev episodes by HARP, with one export per HARP covering the union of its (t−24h, t] windows. Report the number of requests and the projected time at N = 1, for 94 Å only and for 94 + 1600 Å.
- Finish item 4, deliver the cost table, then stop.

### 2026-09-22 — Control-mask rule and CV details (decided by: me, before computing any CV)
- **Control mask (HMI grid at t):**
  - Candidates are the pixels with |B| > 30 G that are NOT in the dilated PIL mask.
  - Distance = Euclidean distance (px) to the nearest PIL-mask pixel (`scipy.ndimage.distance_transform_edt`).
  - ctrl = the n_PIL candidates with the largest distance, where n_PIL is the number of PIL-mask pixels.
  - Ties are broken by a fixed random permutation (numpy RandomState seed 0) applied before a stable sort.
  - If there are fewer than n_PIL candidates, all are used and the episode is flagged (`ctrl_short`).
  - ctrl is reprojected onto each AIA frame exactly as the PIL mask is.
- **CV:** for each mask, CV = detrended_sd(mean series over valid frames) / mean(mean series over the same frames). Valid frames are the same as for the other features (not P2-excluded, QUALITY == 0).

### 2026-09-22 — update_pointing applied; ctrl mask observations (recorded by: me)
- `aiapy.calibrate.update_pointing` runs on the cutouts. It shifts CRPIX by X0_MP_new − X0_MP_old and uses the pointing table `aia.master_pointing3h` from a JSOC keyword query. It is applied to every frame before registration (`pointing_updated` counts frames), and all frames in items 2–3 were updated. `ratio_old` changed by < 1% as a result.
- Ctrl mask facts: under the fixed rule it is spatially scattered (small >30 G plage/network patches far from the PIL, often near the patch edges). For HARP 6975 there are fewer candidates than PIL pixels (26,688 < 33,031), so `ctrl_short` = True and all candidates are used. The rule is not changed.

### 2026-09-22 — Item 4 paused (decided by: user)
- The user paused item 4 to find a faster download method. Files average 0.14 MB and arrive at ~7–8 s each (per-file HTTP overhead, not bandwidth).
- State at pause: HARP 4231 has 191 of 1,800 files from finished request JSOC_20260922_000545; partial `.part` files were removed. Nothing is processed yet and no raw files are deleted. HARPs 6975 and 3248 have not been requested.
- Resume with `JSOC_REQUEST_ID=JSOC_20260922_000545 python euv_run.py item4 4231`, which skips files already present. Items 1–3 and the pilot results are complete.

## 2026-09-22 — Reproduction improvement for D7 (decided by: user; DIAGNOSTIC ONLY)
- **The main gate stays at 10 features.** This work is diagnostic only. It does not change the frozen spec, the gate or the Stage 5 FINAL result.
- Scope, report only, no downloads:
  1. Exact formulas, units, pixel masks and constants for TOTBSQ, TOTFZ and EPSZ, from Bobra et al. 2014 (Sol. Phys. 289, 3549) and B&C 2015, quoted with pages.
  2. A cost estimate for the hmi.sharp_cea_720s vector segments (Br, Bp, Bt, plus bitmap/conf_disambig as needed) for exactly the D7 sample records (272 pos + 4,488 neg): records, size, requests, projected time at N = 1.
  3. A validation plan: compare our computed values with SWAN-SF's TOTBSQ, TOTFZ and EPSZ for matching HARP/time, with an agreement metric, before using them.
  4. A catalogue check (metadata only): does the NGDC/NCEI GOES XRS flare report for May 2010 – May 2014 carry flare location and NOAA region, and how many of the 121 location-proxy losses would it recover?
- Report 1–4, then stop.

### D7 reproduction improvement — results 1 and 4 (recorded by: me; diagnostic; dev period only)
**1. Definitions of TOTBSQ, TOTFZ, EPSZ.** Page numbers are arXiv pages; journal pages differ.
- **Bobra et al. 2014** (arXiv:1404.1879, Table 3, p. 8) lists 16 parameters. **TOTBSQ, TOTFZ and EPSZ are not among them**, and no Lorentz-force formula appears in the paper. It does define the pixel mask for all SHARP parameters (p. 7): pixels "within the HARP (bitmap ≥ 33)" and above the high-confidence disambiguation threshold (≈ 150 G, conf_disambig = 90). The count of contributing pixels is keyword CMASK.
- **B&C 2015** (arXiv:1411.1405, Table 1, p. 12) gives proportionalities only, with no constants or units:
  - TOTBSQ: F ∝ ΣB²
  - TOTFZ: F_z ∝ Σ(B_x² + B_y² − B_z²) dA
  - EPSZ: δF_z ∝ Σ(B_x² + B_y² − B_z²) / ΣB²

  B&C p. 8 says seven Lorentz parameters are "adapted from Fisher et al. (2012)". B&C p. 8 (Fig. 1 panels 7–8) says each parameter uses one of two masks; the non-R masks are HARP ∩ high-confidence.
- **Official JSOC series `cgem.lorentz`** ("Lorentz force computed from hmi.sharp_cea_720s", prime keys HARPNUM, T_REC, 12-min cadence, 2010-05-01 → 2026-08-18). Its keyword definitions (jsoc_info) give the constants and units:
  - TOTBSQ [G²] = Σ B², all pixels; TOTBSQ1 = strong pixels only.
  - TOTFZ [10²⁰ dyne] = Σ (B_h² − B_r²)·AREA/(8π), all pixels; TOTFZ1 = within the bitmap mask.
  - EPSZ [none] = Σ(B_h² − B_r²)/ΣB², all pixels; EPSZ1 = within the bitmap mask.
  - MASKNAME = conf_disambig, MASKTHRS = 61 (e.g. HARP 4231, 2014-06-12).
  - **hmi.sharp_cea_720s has no TOTBSQ/TOTFZ/EPSZ keywords.**
- **Not stated in either paper:** which variant B&C used (all pixels or masked), and the exact per-pixel AREA. The official SHARP/CGEM pipeline source would settle both; it has not been read (only official copies may be used).

**4. NCEI GOES XRS report (goes-xrs-report_2010…2014.txt; fixed-width catalogue text, ~1 MB).**
- Location (e.g. S12W47, cols 29–34) and NOAA region (cols 81–85) fields exist, but location is often blank.
  - Rows with a location: 2010 204/1,256; **2011 0/2,171**; 2012 840/2,037; 2013 849/2,051; 2014 1,213/2,258.
  - M/X rows with a location: 15/23, **0/119**, 93/130, 72/111, 151/221.
- The 121 D7 location-proxy losses (`data/diag/d7_location_proxy_losses.csv`):
  - 119 match a report row (same date, start hhmm), and 52 of those have a location: 19 with |lon| ≤ 68 and 33 with |lon| > 68.
  - Of the 19, **8 have a qualifying patch record within 30 min of peak − 24 h**, so **8 of 121 would be recovered as positives.**
  - By year (with location / |lon| ≤ 68): 2010 2/0, 2011 0/0, 2012 22/7, 2013 10/5, 2014 18/7.
- Not computed: flares the proxy wrongly *included* (true location > 68°) would need the same report. Out of scope.
- Files: `diag_d7_catalogue.py`, `data/diag/d7_location_proxy_catalogue.csv`, `data/diag/d7_sample_records.csv` (the D7 sample rebuilt from diag_d7.py's seeded code: 272 pos + 4,488 neg, 4,757 distinct records, 763 HARPs).

## 2026-09-22 — CORRECTION and reproduction decisions (decided by: user)
**Correction:** TOTBSQ, TOTFZ and EPSZ are **not SHARP keywords** (hmi.sharp_cea_720s / hmi.sharp_720s), but they **are available as keywords in the JSOC series `cgem.lorentz`**. Earlier wording ("unavailable", "not a JSOC keyword", "not keywords") is annotated in place with this date. **The main gate stays at 10 features.**
- **Step 2 (vector-segment size estimate) is cancelled.** It is not needed. The partial script `diag_d7_vector_cost.py` is kept for the record; it produced no result.
- **Reproduction fix 1 uses `cgem.lorentz` keyword queries** for the 4,757 D7 records, with no image downloads. Pre-registered:
  - **R4a (primary) = masked variant** (TOTBSQ1, TOTFZ1, EPSZ1).
  - **R4b (sensitivity) = all-pixel variant** (TOTBSQ, TOTFZ, EPSZ).
  - **Unstated in B&C:** their exact variant, and their mask threshold (SHARP convention conf_disambig = 90, Bobra et al. 2014 p. 7, vs cgem MASKTHRS = 61).
- **SWAN-SF:** the full SWAN.tar.gz (735 MB, Harvard Dataverse file 3642432) is approved **for validation only**. It goes to data/swansf/ (untracked).
  - **Pre-registered pass rule:** Spearman ρ ≥ 0.95 **and** median |relative difference| ≤ 10% between `cgem.lorentz` (each variant) and SWAN-SF, for matching HARP/T_REC.
  - Report which variant matches SWAN-SF better.
- **R2 includes the NGDC catalogue fix** (8 recovered flares), as planned.
- **Step 0:** Ahmed et al. 2013 sample definitions; our HARP/AR count for May 2010 – May 2014 vs B&C's 2,071.
- Then report, and **wait for the user's OK before R1–R4.** Note: R1 and R3 are not defined in this repository or this session's messages; only R2 (catalogue fix included) and R4a/R4b (above) are specified.

### Step 0 — results (recorded by: me)
- **Ahmed et al. 2013** (Sol. Phys. 283, 157): full text not read. It is paywalled (Springer), and the only other copy found is on ResearchGate (unofficial). The definitions below are **as B&C 2015 report them (arXiv pp. 6–7)**:
  - **Operational:** positive = the AR flares within 24 h after the sample time; negative = it does not flare within 24 h after.
  - **Segmented:** same positive; negative = no flare within ±48 h of the sample time.
  - Positive sample time = exactly 24 h before the GOES peak; negative sample times random.
  - B&C also note that Ahmed et al. include C-class flares (p. 21).
- **HARP/AR count, 2010-05-01 … 2014-05-31** (our hourly hmi.sharp_cea_720s keyword cache):
  - 2,322 distinct HARPs, 801 of them with ≥ 1 NOAA number; 1,006 distinct NOAA ARs.
  - B&C: "the SHARP database contains 2,071 ARs and 1.5 million active region patches" (arXiv p. 8).
  - Their end date and their definition of "AR" (HARP or NOAA region) are not stated.

### SWAN-SF validation — RESULTS (pre-registered rule; recorded by: me; diagnostic)
- **Inputs:**
  - SWAN.tar.gz (Harvard Dataverse file 3642432), 735,206,766 B, **MD5 379da8ba2920a82c81d1c4d3293fc709 = published**. It was re-downloaded from scratch in 8 byte ranges; the earlier partial copy was discarded.
  - `cgem.lorentz` keyword query for the 4,757 distinct D7 records (`diag_d7_cgem.py` → `data/diag/d7_cgem_lorentz.csv`): 4,757 found, 4,579 with all six values; MASKNAME = conf_disambig and MASKTHRS = 61 on every record.
- **Matching:** SWAN-SF Timestamp = T_REC without "_TAI". All 763 D7 HARPs are in SWAN-SF, and 4,757 records matched. cgem TOTFZ was converted from 10²⁰ dyne to dyne.
- **Rule:** PASS iff Spearman ρ ≥ 0.95 AND median |rel diff| ≤ 10%, with rel diff = (cgem − SWAN)/|SWAN|.

| variant | param | n | Spearman ρ | median \|rel diff\| | median ratio cgem/SWAN | PASS |
|---|---|---:|---:|---:|---:|---|
| R4a masked | TOTBSQ | 4,639 | 0.9889 | 0.1310 | 1.1182 | no |
| R4a masked | TOTFZ | 4,639 | 0.9775 | 0.9537 | 0.0463 | no |
| R4a masked | EPSZ | 4,639 | 0.9852 | 0.0300 | 1.0148 | **yes** |
| R4b all-pixel | TOTBSQ | 4,579 | 0.9625 | 0.7569 | 1.7569 | no |
| R4b all-pixel | TOTFZ | 4,579 | 0.8652 | 0.9719 | 0.0281 | no |
| R4b all-pixel | EPSZ | 4,579 | 0.3391 | 0.5909 | 0.4099 | no |

- **Which variant matches SWAN-SF better:** the **masked variant (R4a)**, which has the higher ρ and the lower median |rel diff| for all three parameters.
- **Under the rule:** 1 of 6 passes (R4a EPSZ).
- **Disclosure:** before the validation ran, but after the rule was fixed, I inspected one record (HARP 4201, 2014-06-02 19:24 TAI, not a D7 HARP) to check timestamp format and units.
- Files: `diag_swansf_validate.py`, `data/diag/swansf_validation.csv`. SWAN.tar.gz is kept in data/swansf/ (untracked).

## 2026-09-22 — Reproduction runs R1–R4 defined (decided by: user; DIAGNOSTIC; main pipeline and gate unchanged)
- Cumulative runs. Each uses all 1,000 random stratified 70/30 splits, with both C1/C2 = 2 (Table 2 setting) and C1/C2 = 15 (Table 3 setting). Report TSS, recall, precision and FPR as mean ± sd, and whether mean TSS lands in the **pre-registered target: Table 2 0.562–0.658; Table 3 0.722–0.800.**
  - **R1** = D7/D8 with the exact 12-min SHARP record at each sample time (keywords only).
  - **R2** = R1 + NGDC catalogue (flare locations; 8 recovered flares under D7 logic).
  - **R3 = skipped.** Step 0 found that B&C's operational definition (as they report Ahmed et al. 2013) matches D7's.
  - **R4 (primary)** = R2 + TOTBSQ, TOTFZ, EPSZ from SWAN-SF (13 features).
  - **R4-cgem (sensitivity)** = R2 + the 3 features from cgem.lorentz, masked variant. Label: "failed pre-registered magnitude validation (TOTBSQ, TOTFZ); ρ ≥ 0.978".
- **Validation outcome recorded as-is:** the pre-registered rule passed only for masked EPSZ, and the rule is not changed. Likely causes, **hypotheses, not verified**: mask threshold (cgem MASKTHRS 61 vs SHARP convention 90), and a unit or constant difference for TOTFZ (median ratio cgem/SWAN ≈ 0.046).
- **Region count recorded:** 2,322 HARPs (ours, 2010-05-01 … 2014-05-31) vs B&C's 2,071. B&C's counting unit and end date are unstated.
- Table only.

### R1–R4 implementation details (decided by: me, before running)
- **R1 positive sample record:** for each SWPC M1+ flare (K scale, with a region), the T_REC on the 12-min grid nearest to (GOES peak − 24 h, converted to TAI), so |Δ| ≤ 6 min.
  - It is fetched by keyword query from hmi.sharp_cea_720s, for the patches containing the flare's region, tried in HARPNUM order (as in D7).
  - If that exact record is missing or fails a filter (QUALITY ≤ 65536, |LON_FWT| ≤ 68, 10 features present, region in NOAA_ARS), that patch gives no positive. There is no fallback to neighbouring records.
  - The location proxy uses the patch's 12-min record nearest the peak (|LON_FWT| ≤ 68).
- **R1 negatives:** the D7 construction is unchanged. The hourly eligible records are themselves exact 12-min SHARP records at their own sample times. The pool excludes the positive records (HARP, T_REC) and records with M1+ in (t, t+24h]. N = round(16.5·P), drawn once with the D7 seed.
- **R2:** a flare that fails the location proxy is admitted if the NCEI GOES XRS report (matched on date and start hhmm) gives a location with |lon| ≤ 68. It still needs a qualifying R1 sample record. No flare is removed by R2. The number recovered under R1 logic is reported (it may differ from 8).
- **R4 / R4-cgem:** an example needs all 13 features at its (HARP, T_REC); examples without them are dropped **before sampling**, for positives and the negative pool alike (the D7 missing-data assumption). This changes P and N relative to R2, and both are reported. SWAN-SF is matched on HARP + T_REC. cgem.lorentz values come from keyword queries (TOTBSQ1, TOTFZ1, EPSZ1).
- Everything else is D7/D8: median/SD scaling on the whole catalogue, RBF C = 4, γ = 0.075, tol = 1e-8, class weight positive:negative = 2 or 15, decision value 0, split seeds SEED + i.

### R1–R4 — RESULTS (diagnostic; dev period only; main pipeline and gate unchanged; table only)
`diag_r.py` → `data/diag/r_runs.csv`. 1,000 random stratified 70/30 splits per row; mean ± sd. The pre-registered TSS targets are Table 2 0.562–0.658 and Table 3 0.722–0.800. Flares in the period with a peak: 454. NCEI-location admissions in R2: 8. No split had undefined precision.
Implementation note (me): the cgem.lorentz query for the negative pool used one hourly range query per HARP. The first attempt, which listed hourly T_RECs, failed with HTTP 414 before any result was computed.

| run | C1/C2 | P | N | neg pool | TSS | recall | precision | FPR | TSS in target |
|---|---:|---:|---:|---:|---|---|---|---|---|
| R1 | 2 | 283 | 4,670 | 132,978 | 0.515 ± 0.049 | 0.531 ± 0.050 | 0.677 ± 0.048 | 0.016 ± 0.003 | no |
| R1 | 15 | 283 | 4,670 | 132,978 | 0.706 ± 0.040 | 0.797 ± 0.042 | 0.347 ± 0.023 | 0.092 ± 0.010 | no |
| R2 | 2 | 291 | 4,802 | 132,978 | 0.520 ± 0.049 | 0.536 ± 0.049 | 0.679 ± 0.052 | 0.016 ± 0.004 | no |
| R2 | 15 | 291 | 4,802 | 132,978 | 0.708 ± 0.038 | 0.801 ± 0.041 | 0.344 ± 0.023 | 0.093 ± 0.010 | no |
| R4 (SWAN-SF, primary) | 2 | 291 | 4,802 | 132,965 | 0.530 ± 0.051 | 0.541 ± 0.051 | 0.756 ± 0.049 | 0.011 ± 0.003 | no |
| R4 (SWAN-SF, primary) | 15 | 291 | 4,802 | 132,965 | 0.695 ± 0.039 | 0.779 ± 0.042 | 0.360 ± 0.025 | 0.084 ± 0.010 | no |
| R4-cgem (masked; failed pre-registered magnitude validation TOTBSQ, TOTFZ; ρ ≥ 0.978) | 2 | 276 | 4,554 | 129,826 | 0.507 ± 0.050 | 0.519 ± 0.051 | 0.730 ± 0.054 | 0.012 ± 0.003 | no |
| R4-cgem (same label) | 15 | 276 | 4,554 | 129,826 | 0.695 ± 0.042 | 0.777 ± 0.044 | 0.366 ± 0.025 | 0.082 ± 0.009 | no |

## 2026-09-22 — Item 4 resumed; 12-s cadence check pre-declared (decided by: user; pilot only; facts only)
- Finish item 4 (94 Å, 12 s, (t−6h, t]) for HARPs 4231, 6975 and 3248, resuming from files on disk, one file at a time with retries. Keep per-frame derived results; process-and-delete is OK.
- **Cadence check (pre-declared):** for each episode over (t−6h, t], compute CV_PIL, CV_ctrl (pixel-count-matched control, 20 draws) and CV_PIL − CV_ctrl:
  - (a) from all 12-s frames;
  - (b) from only the frames at the 12-min slots.
  Report both side by side, with frame counts, gaps, download time and size. No true-vs-false conclusions (n = 3).
- Also requested: "the AIA synoptic check and Path A as specified earlier".
- **Open (me):** "AIA synoptic check", "Path A" and the "pixel-count-matched control, 20 draws" are **not defined** in decisions.md or in this session's messages. The recorded ctrl rule (2026-09-22) is deterministic (the farthest AR-mask pixels, seed-0 tie-break), not 20 random draws.
  - None of the three is run until the user supplies the definitions.
  - Raw item-4 files are **kept, not processed or deleted**, until the metric is defined.

## 2026-09-22 — Definitions D-CTRL, SYNOPTIC CHECK, PATH A, item-4 cadence check (decided by: user; recorded VERBATIM before running anything)

> D-CTRL — pixel-count-matched random control (replaces the "farthest pixels" rule
> as primary; keep the deterministic rule as a reported secondary):
> - Candidate set: HARP bitmap region ∩ AR mask (|B_LoS| ≥ 30 G) ∩ OUTSIDE the dilated
>   PIL mask, defined on the LoS magnetogram at t.
> - Draws: 20 draws, seeds 0–19, uniform random WITHOUT replacement.
>   n = min(n_PIL, n_candidates). If n_candidates < n_PIL, also subsample the PIL mask
>   to n pixels (same seed), so both sides always have equal pixel counts.
>   Flag ctrl_short when this happens.
> - Pixels are drawn once in the magnetogram frame at t, then mapped to every AIA frame
>   with the same reprojection/differential rotation as the full masks.
> - Per draw: build the mean-intensity time series over (t−24h, t] for the PIL sample
>   and the control sample (valid frames only; exclusion rules P2/P4/QUALITY as
>   approved); remove a least-squares linear trend; CV = SD(residuals) / mean(series).
> - Combine: mean of the per-draw CVs (report the SD across draws too).
> - Primary feature: ΔCV = CV_PIL − CV_ctrl. Also report CV_PIL, CV_ctrl, CV_box.
>
> SYNOPTIC CHECK — report only, no bulk download:
> - AIA synoptic data (level 1.5, ~1024², ~2-min cadence): URL, format, coverage
>   2010→2026, 94 Å and 1600 Å availability, file size, any usage/rate policy.
> - Test: download 20 files with 4–8 parallel connections; report throughput.
> - If available: rerun the 3 pilot episodes with synoptic frames at the 12-min slots,
>   same masks mapped to the synoptic frame, D-CTRL metric; side by side with the
>   cutout results; overlays; time and size.
> - Also: SDAC/VSO full-res full-disk AIA via SunPy Fido — same 20-file parallel
>   throughput test. And count UNIQUE 12-min timestamps in the union of all 547 dev
>   alarm windows. Project total time/GB for (a) JSOC cutouts grouped by HARP, N = 1,
>   (b) synoptic, (c) SDAC full-res crop-and-delete; 94 Å only and 94 + 1600 Å.
> - Never use more than one JSOC account.
>
> PATH A — "phantom false alarms" (no downloads; descriptive, not a test of the
> primary result):
> - Using archived HEK-based labels (data/labels_hek/) and final SWPC K2 labels, with
>   the same frozen 10-feature gate scores and threshold:
>   1. Gate TSS, FAR, precision under HEK vs SWPC labels, hour and region level,
>      region-bootstrap 95% CI — for 2021–2024 and 2010–2019 separately.
>   2. Count alarm episodes (T1–T4 rules) labelled FALSE under HEK but TRUE under
>      SWPC ("phantom false alarms"), per year and as % of HEK false alarms.
>   3. Separate the two causes: also compare HEK vs SWPC on the SAME scale (K),
>      so region-number loss is separated from the ×0.7 scale change.
> - Literature check: any published report of HEK SWPC events with
>   ar_noaanum = 0 after ~2020, and any paper quantifying its effect on flare-forecast
>   verification. Links only.
>
> Item 4 cadence check (after the download finishes): for each pilot episode over
> (t−6h, t], compute ΔCV (D-CTRL, 6 h window) from (a) all 12 s frames and (b) only
> the 12-min-slot frames. Side by side, facts only. Raw 12 s files may be deleted
> after this.
>
> Run order: synoptic check and Path A now (they don't need JSOC); cadence check
> when item 4 finishes. Report each when done.

Notes (me, recorded before running):
- **Path A uses 2021–2024.** The standing rule (2026-09-21, "PRIMARY RESULT FINAL") is "No new analysis is to be run on 2021–2024". Path A is the user's explicit, descriptive exception. It does not alter or retest the FINAL primary result.
- The **"AR mask (|B_LoS| ≥ 30 G)"** here uses ≥; the earlier pilot code used > 30 G. D-CTRL follows the ≥ given here.

### D-CTRL / synoptic / cadence — implementation details (decided by: me, BEFORE any D-CTRL value is computed)
- **HARP bitmap region** = `hmi.sharp_720s` bitmap ≥ 33. Observed values are 1, 2, 33 and 34; ≥ 33 = inside the HARP, as in Bobra et al. 2014 p. 7. AR mask = |B_LoS| ≥ 30 G.
- **Draws:** for seed s, the control sample is `RandomState(s).choice(candidates, n, replace=False)`. When ctrl_short, the PIL sample is a separate `RandomState(s).choice(PIL, n, replace=False)`; otherwise the PIL sample is the full PIL mask (n = n_PIL).
- **Mapping to AIA (all masks in the D-CTRL runs, including the full PIL, box and deterministic ctrl):** each HMI pixel centre is mapped forward to the AIA frame (WCS, with `propagate_with_solar_surface` from the magnetogram time to the frame time) and assigned to the AIA pixel it falls in (nearest). A mask's frame mean is the mean over its HMI pixels of the AIA value at their mapped pixels. Pixels mapping outside the frame or onto NaN are ignored.
  - Reason: bilinear reprojection thresholded at 0.5 (used for the earlier pilot numbers) drops most isolated single-pixel samples, so the sample sizes would no longer be equal. Forward mapping keeps every sampled HMI pixel.
  - The earlier pilot results stay as recorded; the D-CTRL numbers use this mapping.
- **Box** = all pixels of the SHARP patch (U9, unchanged).
- **Valid frames:** P2 (amended), QUALITY == 0 and the P4 saturation rule, as approved. For **synoptic** frames (4×4-averaged level 1.5, values = DN per original pixel), the 12,000 DN cut is applied to the averaged pixel values. It cannot be applied per raw pixel, so this is a stated deviation. Synoptic frames are already level 1.5, so no update_pointing or registration is applied to them.
- **Cadence check (b):** the 12-s frames whose T_OBS lies within ±6 s of the 12-min slots t − 6 h + 12 min … t. **Synoptic:** the file at each 12-min slot, `AIAYYYYMMDD_HHMM_{0094,1600}.fits`, with HHMM = the slot rounded to the 2-min grid.

### SDAC/VSO full-res throughput test — not completed (recorded by: me)
- **SDAC is not an AIA full-resolution provider.** `Fido.search` for AIA 94 Å (2014-06-12 00:00–00:05) with Provider = SDAC returned 0 rows. Without a provider filter, VSO lists **only JSOC** (64.6 MiB per level-1 full-disk file). SDAC's `umbra.nascom.nasa.gov/sdo/aia/` holds only a few 2010–2012 event bundles.
- The 20-file test via VSO→JSOC (6 connections) was started, delivered 0 files in ~25 min, and was **stopped**. VSO stages JSOC data under VSO's own JSOC access, which conflicts with "Never use more than one JSOC account". No file was received.
- Path (c) "SDAC full-res crop-and-delete" therefore has no measured throughput.

### PATH A — RESULTS (descriptive; not a test of the FINAL primary result; recorded by: me)
`diag_patha.py` → `data/diag/patha_gate.csv`, `patha_episodes.csv`, `patha_phantom_*.csv`.
- **Setup:** primary subset (single-region), frozen gate and threshold −0.992496.
  - All 254,899 K2 rows have HEK and SWPC-K labels (month-boundary duplicates removed from both).
  - Dev uses the frozen OOF scores; 2021–2024 uses the mean of the frozen fold models, including 2022 as in the sensitivity analysis.
  - Reproduction checks: dev K2 hour TSS 0.6793 = Stage 2; 2021–2024 K2 hour TSS 0.5224 and 414 episodes = Stage 5's sensitivity row.
- **Label sets:**
  - HEK = archived HEK/SWPC labels, classes as reported.
  - K = SWPC originals, old scale (file 85b88518…).
  - K2 = final.
- **Same-scale pairs:** 2010–2019 HEK vs K; 2021–2024 HEK vs K2 (HEK carries GOES-16 fluxes as reported).

**1. Gate under each label set** (TSS 95% CI = HARP bootstrap, 1,000; precision = 1 − FAR)

| period | labels | level | positives | N | TSS [95% CI] | FAR | precision |
|---|---|---|---:|---:|---|---:|---:|
| 2010–2019 | HEK | hour | 2,444 | 114,952 | 0.725 [0.642, 0.796] | 0.725 | 0.275 |
| 2010–2019 | K | hour | 2,440 | 114,952 | 0.722 [0.636, 0.792] | 0.727 | 0.273 |
| 2010–2019 | K2 | hour | 3,168 | 114,952 | 0.679 [0.586, 0.748] | 0.666 | 0.334 |
| 2010–2019 | HEK | region | 64 | 986 | 0.680 [0.591, 0.766] | 0.750 | 0.250 |
| 2010–2019 | K | region | 64 | 986 | 0.664 [0.570, 0.750] | 0.755 | 0.245 |
| 2010–2019 | K2 | region | 86 | 986 | 0.647 [0.557, 0.726] | 0.682 | 0.318 |
| 2021–2024 | HEK | hour | 1,299 | 71,862 | 0.579 [0.401, 0.720] | 0.838 | 0.162 |
| 2021–2024 | K | hour | 1,465 | 71,862 | 0.553 [0.417, 0.679] | 0.825 | 0.175 |
| 2021–2024 | K2 | hour | 2,381 | 71,862 | 0.522 [0.412, 0.626] | 0.733 | 0.267 |
| 2021–2024 | HEK | region | 38 | 605 | 0.682 [0.552, 0.785] | 0.763 | 0.237 |
| 2021–2024 | K | region | 45 | 605 | 0.736 [0.641, 0.815] | 0.705 | 0.295 |
| 2021–2024 | K2 | region | 71 | 605 | 0.681 [0.584, 0.762] | 0.576 | 0.425 |

**2–3. Episodes (T1–T4 under K2; 961 = 547 dev + 414 test, relabelled at t).** "Phantom" = false under the first set, true under the second; "reverse" = the opposite.

| comparison | 2010–2019 phantom / HEK-or-K false | 2021–2024 phantom / false | all | reverse (all) |
|---|---|---|---|---|
| HEK → K2 (both causes) | 18 / 466 | 34 / 386 (8.8%) | 52 / 852 (6.1%) | 1 |
| HEK → K (dev: same scale) | **0** / 466 | 20 / 386 | 20 / 852 (2.3%) | 14 |
| K → K2 (scale change only) | 19 / 468 | 26 / 378 | 45 / 846 (5.3%) | 0 |

- **Per year, HEK → K2 phantom:** 2011 3, 2014 4, 2015 8, 2017 3, 2021 2, **2022 15**, **2023 17**, 2024 0, other years 0.
- **Same-scale view:** 2010–2019 HEK vs K = 0 phantom, so there is no region-loss effect in the dev years. 2021–2024 HEK vs K2 (same scale) = 34 phantom (2021 2, 2022 15, 2023 17, 2024 0).
- **Literature (links only; not read in full):** arXiv:2512.13417 "Defects and Inconsistencies in Solar Flare Data Sources: Implications for Machine Learning Forecasting"; Angryk et al. 2020, Sci. Data (SWAN-SF); NCEI "GOES Flare Report ReadMe" (Lucas & Machol, 2025); arXiv:2608.04537. **No source found that specifically reports HEK ar_noaanum = 0 after ~2020 [unverified whether 2512.13417 does].**

### 2026-09-22 — Download-speed tests (decided by: user; method only, same data)
- **HARP 6975 item 4** is requested with JSOC `method="url-tar"`: one archive per request, unpacked into the item folder, tar deleted. The data, box, tracking and t_ref are unchanged; only the delivery method differs.
- **HARP 4231** continues per file from finished request JSOC_20260922_000545 (886 of 1,800 at the switch). The log now records `prep_s` (submit → ready) and `download_s` separately.
- **Synoptic** downloads use 6 parallel connections, written to .tmp and renamed. One truncated synoptic file left by the stopped sequential run was found (FITS size check) and removed.
- **HARP 3248 item 4:** requested after 6975's export has finished (one pending export per address), with whichever method measured faster (operational choice, stated when made).

## 2026-09-22 — Path A follow-up (decided by: user; frozen files and the main result unchanged)
**Prior work (user, recorded verbatim):** "Prior work = Hu, Jin, Verma, Liu, Manchester, Zhao, Gombosi & Chen, arXiv:2512.13417v3 (2026). They report >3,000 post-2022 SunPy-HEK GOES flares with AR=0 (p.9) and the SWPC x0.7 scaling (Fig.4). They do not quantify the HEK AR=0 effect on alarm FAR. Path A = independent confirmation + FAR quantification, not a discovery."
Requested:
- (2) 95% CIs for FAR and precision, HEK vs K2, 2021–24, hourly and region level: 2,000 bootstrap resamples by HARP, seed 0, plus the CI of the difference (HEK − K2) from the same resamples.
- (3) The 34 phantom alarms → `data/pathA/phantoms_2021_24.csv`.
- (4) An evidence pack for 3 phantoms from 2023 → `data/pathA/evidence/`.
- (5) Numbers only.

## 2026-09-22 — Prior-work check completed: Hu et al. 2026 read in full (recorded by: Claude chat, on user request; no analysis changed)
Source: Hu, Jin, Verma, Liu, Manchester, Zhao, Gombosi & Chen, "Defects and Inconsistencies in Solar Flare Data Sources: Implications for Machine Learning Forecasting", arXiv:2512.13417v3 (June 2026). Main text pp. 1–33 read; appendix tables only skimmed.
- **Already published (not ours):** SunPy-HEK GOES list has >3,000 post-2022 flares with AR = 0; authors say not to use it for research, especially GOES-R era (p. 9). SWPC ×0.7 scaling, ratio 0.7 before Dec 2019 then 1 (pp. 10–11, Fig. 4).
- **Their Section 4 (ML effect)** compares SWPC-FTP vs NCEI Science-Quality labels, and NRT vs definitive SHARPs (LSTM + logistic regression/PCA; train 2010-05-01 → 2019-12-31; test 2020–2024; M/X vs A/B, C excluded; 30 bootstrap models). It does **not** test HEK labels. No HEK effect on skill or FAR is reported in the main text.
- **Their recommendations (Section 5, Table 11):** for AR-based ML, SWPC-FTP labels are the most direct source; the pre-GOES-R scaling must be documented/corrected; definitive SHARPs preferred for retrospective benchmarks; SunPy-HEK must be independently validated before training/evaluation. Our existing design (SWPC originals, K2 = ÷0.7 correction, definitive SHARPs) already follows these. No design change.
- **Consequence for Path A framing:** independent confirmation of a published defect + first alarm-level quantification of its effect on FAR (as far as checked). Hu et al. must be cited. Open caveat: appendix tables not read line by line.

### Path A follow-up — RESULTS (numbers only; recorded by: me)
`diag_patha2.py`. 2021–2024 test HARPs, single-region, frozen gate and threshold. 5,145 alarm hours; 139 alarmed regions of 605. 2,000 HARP resamples, seed 0; all 2,000 were usable.

| level | quantity | HEK | K2 | HEK − K2 |
|---|---|---|---|---|
| hour | FAR | 0.8383 [0.7599, 0.9112] | 0.7331 [0.6609, 0.8040] | 0.1052 [0.0662, 0.1466] |
| hour | precision | 0.1617 [0.0888, 0.2401] | 0.2669 [0.1960, 0.3391] | −0.1052 [−0.1466, −0.0662] |
| region | FAR | 0.7626 [0.6905, 0.8288] | 0.5755 [0.4937, 0.6593] | 0.1871 [0.1224, 0.2517] |
| region | precision | 0.2374 [0.1712, 0.3095] | 0.4245 [0.3407, 0.5063] | −0.1871 [−0.2517, −0.1224] |

- **Phantom list:** `data/pathA/phantoms_2021_24.csv`, 34 alarms (2021: 2, 2022: 15, 2023: 17) in 20 HARPs.
- **HEK match** (SWPC-reported events within ±10 min of the first SWPC K2 M1+ start in (t, t+24h]): ar_noaanum = 0 for 27 phantoms, "0;0" (two HEK events) for 3, and no HEK event for 4 (HARP 9699 2023-06-22; HARP 10430 ×3, 2023-11-28 and 2023-12-01).
- **Evidence pack** (`data/pathA/evidence/`, the first 3 phantoms of 2023):
  - HARP 8942 2023-01-08 09:59 (SWPC M2.1, reg 3181; HEK ar_noaanum 0, hpc_x 0, hgs_x/y 0).
  - HARP 9121 2023-02-25 16:59 (SWPC M6.3, reg 3229; HEK ar 0).
  - HARP 9182 2023-03-05 11:59 (SWPC M1.0, reg 3242; 2 HEK M1.0 events, both ar 0).
  - Each folder has `hek_record.csv` (165 fields incl. hpc/hgs/hgc/hrc/event_coord), `swpc_report_line.txt` (the NCEI original XRA line) and `sharp_record_at_alarm.csv` (raw SHARP row at the alarm T_REC).

### Path A consistency checks — RESULTS (numbers only; recorded by: me)
`diag_patha3.py`. Descriptive; frozen files and the main result unchanged.

**1. Region flips.** 139 alarmed regions of 605; **26 flip** (HEK false → K2 true); the 34 phantom episodes span 20 HARPs. No flipping region has a single HEK-positive row. `data/pathA/region_flips_2021_24.csv`.

| reason | regions |
|---|---:|
| phantom episode (first evaluable hour) | 15 |
| later alarm hour, K2-positive, not an episode t | 7 |
| K2-positive rows only outside alarm hours | 4 |

The 4 with no K2-positive alarm hour: HARPs 9590, 9643, 9822, 10527. The 7 "later alarm hour": 8878, 8968, 9133, 9137, 9632, 9762, 10312. (The region level counts a region positive if **any** row is positive and alarmed if **any** hour alarms, so it does not require the positive row to be an alarm hour.)

**2. FAR / precision by test-year set** (2,000 HARP resamples, seed 0; the 2021–2024 table above is unchanged)

| years | level | FAR HEK | FAR K2 | FAR HEK − K2 | precision HEK | precision K2 |
|---|---|---|---|---|---|---|
| primary 2021/2023/2024 (3,988 alarm hours, 105 alarmed regions) | hour | 0.8007 [0.7110, 0.8878] | 0.7021 [0.6186, 0.7833] | 0.0985 [0.0573, 0.1499] | 0.1993 [0.1122, 0.2890] | 0.2979 [0.2167, 0.3814] |
| primary 2021/2023/2024 | region | 0.7238 [0.6344, 0.8058] | 0.5429 [0.4414, 0.6337] | 0.1810 [0.1122, 0.2589] | 0.2762 [0.1942, 0.3656] | 0.4571 [0.3663, 0.5586] |
| 2022 only (1,157 alarm hours, 34 alarmed regions) | hour | 0.9680 [0.9230, 1.0000] | 0.8401 [0.7331, 0.9223] | 0.1279 [0.0519, 0.2241] | 0.0320 [0.0000, 0.0770] | 0.1599 [0.0777, 0.2669] |
| 2022 only | region | 0.8824 [0.7692, 0.9744] | 0.6765 [0.5161, 0.8333] | 0.2059 [0.0811, 0.3448] | 0.1176 [0.0256, 0.2308] | 0.3235 [0.1667, 0.4839] |

**3. HEK M1+ events with ar_noaanum ≤ 0 or missing, per year** (all HEK/SWPC M1+ events, classes as reported, no scale conversion; `data/pathA/hek_ar_zero_by_year.csv`)

| year | HEK M1+ | AR = 0 or missing | fraction |
|---|---:|---:|---:|
| 2019 | 0 | 0 | — |
| 2020 | 2 | 2 | 1.000 |
| 2021 | 31 | 14 | 0.452 |
| 2022 | 195 | 173 | 0.887 |
| 2023 | 334 | 284 | 0.850 |
| 2024 | 949 | 72 | 0.076 |

**4. The 4 "no HEK event" phantoms** (HARP 9699 2023-06-22; HARP 10430 2023-11-28 and ×2 2023-12-01). Re-searched HEK (FRM = SWPC) within ±60 min of both the SWPC start and the SWPC peak: **no HEK event found in any of the 8 searches.** `data/pathA/no_hek_phantoms_pm60min.csv`.

**5.** The staged entry "Prior-work check completed: Hu et al. 2026 read in full" was already in `decisions.md` and went into commit `2ba51d3` unchanged (verified with `git log -S`). No re-commit was needed.

## 2026-09-23 — COMBINED EUV TEST (decided by: user; replaces all earlier EUV test prompts from Claude chat)
**Rules in force:** no true-vs-false comparison of ΔCV anywhere; frozen files and the main result unchanged; one JSOC export pending at a time, the user's account only; all rules recorded here **before** running; numbers only; **STOP before the full-study download.**

### PHASE 0 — prior work (source: Claude chat, verified from PDFs; recorded as given)
- Kniezewski, Mason, Uritsky & Garland 2024, ApJL 977:L29 — 3-min, 6 h, limb loops, 131/171/193/304 Å, 53 flares ≥ C5 vs 30 flare-quiet ARs.
- Dissauer, Leka & Wagner 2023, ApJ 942:83 — AARPs; full resolution; 72-s bursts; AEC images avoided; criticises spatial binning.
- Zhong, Kolotkov & Nakariakov, arXiv:2602.18133 — 12-s full-res cutouts; 0.9–10 mHz.
- Nishizuka et al. 2018, ApJ — DeFN; 1-h cadence.
- Galvez et al. 2019, ApJS — SDOML, built from AIA synoptic 1024×1024, 2.4″/px, 2-min.

### Download set-up (rules)
- **JSOC:** `url-tar` for all exports. **Overlap test:** once an export reports complete, submit the next while the previous tar downloads; if JSOC rejects it as a second pending export, revert to sequential and log the exact response.
- **Synoptic:** 12 connections; log files/s and errors every 500 files; on any error or throttling drop to 6 and log it.
- **Disk:** free space at start **666 GB** (data/euv_pilot currently 1.7 GB). **Crop-on-download** for synoptic: after each full-disk frame, save the patch for every HARP needed at that time (HARP box + D-CTRL margin), then delete the full-disk file. First verify on the 3 pilot HARPs that cropped-patch ΔCV equals full-disk ΔCV (|diff| < 1e-6). Report MB per 1,000 frames before and after.
- **Shared cross-HARP cache:** not used now (≈7% saving); noted as optional.

### PHASE 1 (no downloads)
1. **Exposure:** confirm every frame (cutout, 12-s, synoptic) is divided by EXPTIME before ΔCV; for synoptic, check header/units and state whether already normalised. **Rule: drop frames with EXPTIME < 50% of that channel's median in the window.** Report frames checked/dropped per pilot HARP and channel, and recompute all pilot ΔCVs (24 h cutout, 24 h synoptic, 6 h 12-s, 6 h 12-min): old vs new.
2. **Offset test:** HARPs 4231, 6975, 3248, existing 12-s 94 Å frames over (t−6h, t]; 12-min subsamples at all 60 offsets (0 s to 11:48 in 12-s steps). Report mean, SD, min, max, and the percentile of the current 12-min value.
3. **Path A leftovers:** HEK ar_noaanum = 0 count and fraction per year 2019–2024 (all M1+); re-search the 4 "no HEK event" phantoms (HARP 9699; 10430 ×3) at ±60 min by start and by peak.

### PHASE 2 — cadence test (synoptic, 94 Å only)
4. **15 dev alarms, random seed 1, stratified 8/7 by label for coverage only.** D-CTRL ΔCV over (t−24h, t] at 2, 3, 6 and 12 min; same masks, same 20 draws, exposure rule; **slot = nearest frame within ± half the cadence; an alarm is valid only if ≥ 90% of slots are filled.**
   - **Decision rule:** reference = 2 min. Choose the **slowest** of {12, 6, 3} with **Spearman ρ ≥ 0.9 AND median |ΔCV − ΔCV_2min| ≤ 0.02**; if none passes, use 2 min. Report ρ with a bootstrap 95% CI (2,000 resamples, seed 0) and state that n = 15.
   - **1600 Å is not re-tested** (validated by the 3-HARP pilot only; stated as a limitation).

### PHASE 3 — synoptic vs cutout (JSOC, 94 Å only)
5. First 10 of the 15 (seed-1 order): 24 h cutouts at 2-min cadence by url-tar.
   - (a) cutout vs synoptic at the chosen cadence. **Rule: synoptic is the full-study source if median |diff| ≤ 0.01 AND Spearman ρ ≥ 0.9, otherwise JSOC cutouts.**
   - (b) cutout-based 2/3/6/12-min agreement as a second opinion on Phase 2.

### PHASE 4 — after the decisions
6. **131 Å** ΔCV at the chosen cadence for the 15 alarms (descriptive only).
7. **Summary table:** each choice (source, cadence, exposure rule, slot rule), its rule, the measured numbers, pass/fail, final decision.
8. **Full-study cost table** for 547 alarms at the chosen source/cadence: files, GB after cropping, estimated hours for 2 channels (and 3 with 131 Å). Wall-clock time per phase.
9. **Commit and STOP.** Wait for the user's go-ahead before the full download.
