# Verified facts

Full fact check, 2026-09-23. **Read-only:** no refitting, no test-set tuning, no changes to frozen files or results.
- Every value comes from repository files, logs or CSVs, or from a read-only recomputation in `verify_facts.py` (saved output: `/tmp/verify_facts.log`, not committed).
- One re-scoring with the frozen gate models (no fitting) was used earlier to verify Stage 5 counts: `diag_flare_rate.py`, commit `0fd731c`.

**Sources checked**
- **PS** = `PROJECT_SUMMARY.md` (commit state at `57c925d`).
- **CH** = `verification/claude_chat_status_to_verify.md` (written by Claude chat; treated as unverified).
- **D** = `decisions.md`, result sections.

Line numbers are `file:line`.

**Evidence abbreviations**
- `g5` = `data/stage5/gate_gate.csv`
- `m5` = `data/stage5/models_b.csv`
- `s2` = `data/stage2/stage2_metrics.csv`
- `jr` = `data/join_report_swpc.csv`
- `pa` = `data/diag/patha_gate.csv`
- `pac` = `data/pathA/far_precision_ci_2021_24.csv`
- `pay` = `data/pathA/far_precision_ci_by_years.csv`

**Status values:** MATCH / MISMATCH (correct value given) / DEFINITION WRONG (number right, meaning wrong) / NOT FOUND (no evidence in the repository) / NOT CHECKABLE (external, e.g. a paper quote).

## Glossary

Terms:
- **Alarm hour:** an hourly SHARP row whose frozen gate score (SVM decision value; test = mean of the 5 frozen fold models) is ≥ −0.992496.
- **Alarm region:** a HARP with ≥ 1 alarm hour in the evaluated period and subset. Region-level truth = ≥ 1 of its labelled hours has `flared_M1_next_24h = 1`.
- **Alarm episode (T1–T4):**
  - T1: consecutive alarm hours of one HARP, merged across ≤ 3 missing/unscorable hours; the episode ends at a scored hour below threshold or a gap > 3 h.
  - T4: t = the first alarm hour whose (t−24h, t] window has ≥ 18 of 24 points (T3).
  - T2: every eligible episode, weighted 1 / (eligible episodes in its HARP).
- **True / false / delayed alarm:**
  - True: episode with ≥ 1 M1+ (K2, SWPC, same NOAA region[s]) in (t, t+24h].
  - False: none in (t, t+24h].
  - Delayed: false, with ≥ 1 M1+ in (t+24h, t+48h] and complete follow-up.

Metrics:
- **TPR (recall):** TP / (TP + FN).
- **FPR:** FP / (FP + TN).
- **TSS:** TPR − FPR.
- **HSS:** 2(TP·TN − FN·FP) / [(TP+FN)(FN+TN) + (TP+FP)(FP+TN)].
- **FAR:** FP / (TP + FP), the false-alarm *ratio*, 1 − precision.
- **Precision:** TP / (TP + FP).
- **AUC (weighted):** ROC AUC with episode weights 1/n per HARP.
- **Log-loss (weighted):** Σ w·ℓ / Σ w.
- **Δlog-loss:** log-loss(A) − log-loss(B), with A = gate score + n_C + n_M + n_X (48 h) and B = A + relative 24-h slopes of USFLUX and TOTUSJH. Positive means B is better.

Labels:
- **HEK:** archived HEK/SWPC labels.
- **K:** SWPC originals, old operational scale.
- **K2:** SWPC originals, true scale (final).

CI methods:
- Main result: HARP bootstrap, 10,000 resamples, seed 20260921.
- Gate: HARP bootstrap, 1,000, seed 20260921.
- Path A follow-up: 2,000, seed 0.

## A. PROJECT_SUMMARY.md

| # | claim (quoted) | source | exact definition | verified value | evidence | status |
|---|---|---|---|---|---|---|
| 1 | "hourly (`@1h`), 2010-05-01 → 2025-01-01" | PS:13 | labelled file, UTC; end exclusive | first 2010-05-01 00:59:26, last 2024-12-31 23:59:23 | labelled file (recomputed) | MATCH |
| 2 | "QUALITY == 0 … removes 99.5% of 06:00/18:00 TAI records" | PS:14 | raw hourly records, 2010-05→2024-12 | pass: 06 TAI 216/45,181 (0.48%), 18 TAI 220/44,312 (0.50%) → 99.5% removed | `data/raw_sharp_20100501_20250101.csv` (recomputed) | MATCH |
| 3 | "\|LON_FWT\| ≤ 45°" | PS:15 | labelled rows | max \|LON_FWT\| 44.9999 | labelled file | MATCH |
| 4 | "Reg# < 10000 → +10000" | PS:18 | SWPC XRA region rule | rule in `swpc.py`; verified past 14000 | D:169, D:1739–1750 | MATCH |
| 5 | "True irradiance scale (K2): GOES-13/14/15 fluxes ÷ 0.7; GOES-16+ as reported" | PS:19 | per-event `Obs` satellite | as stated; 4,170 of 27,219 events changed K→K2 | D:826–845; `data/scale_conversion_report_K2.csv` | MATCH |
| 6 | "2020 excluded (L)" | PS:23 | CHECK 5, ≥ 90% usable region | 2020: 2 M1+, 0% usable; spec `excluded_years = [2020]` | jr; `frozen/frozen_spec.json` | MATCH |
| 7 | "2022 … fails CHECK 5 at 89.7%" | PS:23 | K2, M1+ with usable region / all M1+ | 175/195 = 0.8974 | jr | MATCH |
| 8 | "SHA-256 `62a0e4cc…`, 254,899 rows" | PS:24 | frozen labelled file | 62a0e4cc; 254,899 rows; 0 duplicates | recomputed | MATCH |
| 9 | "SWPC vs HEK, March 2011–2019: class agreement 100%, 1 region disagreement in ~1,100 pairs" | PS:27 | matched events, 9 Marches | class 1,281/1,281; region 1,094/1,095 (2011-03: 196/197) | `validate_swpc.log`:12–23 | MATCH |
| 10 | "835 empty-report days; none reaches M1" | PS:28 | GOES XRS 1–8 Å daily max | 835 days; max 1.95e-6 W/m² | `data/goes_empty_days.csv` | MATCH |
| 11 | "134 of 137 GOES M1+ peaks" | PS:29 | K2, March 2011–2019; distinct flares after removing 3 peak-rule artefacts | CSV: 140 peaks, 134 matched, 6 unmatched; 3 classified as artefacts → 134/137 | `data/completeness_check.csv`; D:947–958 | MATCH (137 = distinct flares, not raw peaks) |
| 12 | "393 duplicate labelled rows were removed" | PS:30 | 176 monthly labelled chunks, key (harpnum, t_rec_tai) | 255,292 rows, 393 duplicates → 254,899 | recomputed from `data/labelled_<month>.csv` | MATCH |
| 13 | "2018–2020 audit found 0 bugs" | PS:31 | every SWPC M1+ traced | "BUG count: 0" | `audit_2018_2020.log` | MATCH |
| 14 | "residual ~8% GOES-15/16 calibration difference" | PS:31 | NCEI XRS-B ratio 0.923 | 0.923 (quoted from NCEI readme) | D:1003 | NOT CHECKABLE (external readme) |
| 15 | "2024: 80% of positive rows are multi-region" | PS:32 | 2024 positive rows, share with noaa_ar_count > 1 | K2: 3,652/4,591 = 79.6%; originally HEK: 3,656/4,596 = 79.5% | labelled file (recomputed); D:193 | MATCH |
| 16 | "split … SHA-256 `f3ab4056…`, seed 20260921" | PS:35 | `frozen/split.csv` | f3ab4056 | recomputed | MATCH |
| 17 | "Test = 2021–2024 HARPs (801); dev = 2010–2019 (1,218 HARPs)" | PS:36 | HARP counts by set | test 801; train 913 + val 305 = 1,218 | `frozen/split.csv` | MATCH |
| 18 | "SVM, RBF, C = 4, γ = 0.075, tol = 1e-8, class weight 2:1; median/SD scaling inside each fold" | PS:40 | frozen gate | C 4.0, γ 0.075, tol 1e-8, class_weight {1: 2, 0: 1}, median/SD per fold | `frozen/frozen_spec.json` | MATCH |
| 19 | "10 of B&C's 13 (TOTUSJH … SHRGT45)" | PS:41 | gate features | the same 10 | `frozen/frozen_spec.json` | MATCH |
| 20 | "thinned to TAI hours {4, 10, 16, 22}" | PS:42 | training rows | "dev single-region rows at TAI hours {4,10,16,22}" | `frozen/frozen_spec.json` | MATCH |
| 21 | "Threshold: −0.992496, maximising TSS on the pooled out-of-fold scores" | PS:43 | dev, primary subset, hourly OOF | −0.9924958 | `data/stage2/stage2_result.json`; spec | MATCH |
| 22 | "Dev pooled OOF TSS 0.679" | PS:44 | hour level, dev 2010–2019, single-region, OOF, frozen threshold (after dedup) | 0.679264 | s2 (pooled row) | MATCH |
| 23 | "Hour-level TSS 0.547 [0.412, 0.660]" | PS:46 | test 2021/2023/2024, single-region, frozen threshold; HARP bootstrap 1,000 | 0.546719 [0.411954, 0.659838] | g5 | MATCH |
| 24 | "Region-level TSS 0.728 [0.630, 0.820]" | PS:47 | same, one entry per HARP (450) | 0.728423 [0.630135, 0.819759] | g5 | MATCH |
| 25 | "At decision value 0: 0.323 (hour) and 0.476 (region)" | PS:48 | threshold 0 | 0.322740; 0.475719 | g5 | MATCH |
| 26 | "`frozen_spec.json` SHA-256 `1d205068…`" | PS:49 | | 1d205068 | recomputed | MATCH |
| 27 | "313 \| 45 \| 98 \| 0.3686 \| 0.3737 \| −0.0051 \| [−0.0201, 0.0094]" | PS:54 | test 2021/23/24, single-region, all eligible episodes (T2 weights), mean of 5 fold models, HARP bootstrap 10,000 | 313, 45, 98, 0.368581, 0.373669, −0.005089 [−0.020108, 0.009405] | m5 row 1; `stage5_test.log` | MATCH |
| 28 | "Δ ranges from −0.0067 to +0.0054, and every CI includes 0" | PS:56 | 12 rows (2 periods × 3 subsets × 2 cohorts) | min −0.006688, max +0.005391; all 12 CIs contain 0 | m5 | MATCH |
| 29 | "Score-matched pairs (41 pairs): CIs for both slope differences include 0" | PS:57 | caliper 0.0747, pairs clustered by true HARP, 1,000 | 41 pairs; USFLUX [−0.00394, 0.00795]; TOTUSJH [−0.00340, 0.00864] | `data/stage5/pairs_summary.csv` | MATCH |
| 30 | "primary contrast … with a region-level bootstrap 95% CI" | PS:9 | HARP resampling | HARP bootstrap, 10,000 | spec; m5 | MATCH |
| 31 | "D1 0.335, D2 0.677, D3 0.646, D4 0.812, D5 0.790, D6 0.687 (baseline 0.679)" | PS:61–67 | pooled OOF TSS, dev, seed-0 folds | 0.335443, 0.677275, 0.645632, 0.811943, 0.790085, 0.686489; baseline 0.679264 | `data/diag/ablation.csv` | MATCH |
| 32 | "D6 … [0.562, 0.783]" | PS:67 | HARP bootstrap 1,000, seed-0 folds | 0.5624–0.7827 recorded only in D:1311 | no saved artefact; recomputing needs refitting (not allowed) | NOT FOUND |
| 33 | "D7: 0.527 ± 0.050 … D7t 0.707 ± 0.040 … D8 0.716 ± 0.040; 272 pos / 4,488 neg" | PS:68–71 | 1,000 random stratified 70/30 splits; mean ± SD | D7 0.5267 ± 0.0500; D7t 0.7065 ± 0.0401; D8 0.7155 ± 0.0403; P 272, N 4,488 | `data/diag/d7_repeats.csv`, `d7t_repeats.csv`, `d8_counts.csv`, `d7_sample_records.csv` | MATCH |
| 34 | "B&C 0.610 ± 0.048 … 0.761 ± 0.039" | PS:69, 71 | B&C Tables 2 and 3, operational | as stated; checked against the paper on 2026-09-21 | D:1837; `data/diag/d7_d8_comparison.csv` | NOT CHECKABLE (external paper) |
| 35 | "TOTBSQ, TOTFZ, EPSZ … are keywords in JSOC `cgem.lorentz`" | PS:72 | keyword query | values present for 4,757/4,757 D7 records (4,579 with all six) | `data/diag/d7_cgem_lorentz.csv`; D:2201–2210 | MATCH |
| 36 | "SWAN-SF validation … 4,757 records: only masked EPSZ passes; masked closer on all three" | PS:73–75 | ρ ≥ 0.95 and median \|rel diff\| ≤ 10% | 4,757 matched; n used 4,639 (masked) / 4,579 (all-pixel); only R4a EPSZ PASS; masked better on all 3 | `data/diag/swansf_validation.csv` | MATCH (n per comparison < 4,757) |
| 37 | "Suggested causes … mask threshold (61 vs 90), and a TOTFZ unit or constant difference" | PS:76 | hypothesis | not tested | D:2220 | NOT CHECKABLE (unverified hypothesis) |
| 38 | "NCEI catalogue: it would recover 8 of the 121 location-proxy flare losses" | PS:77 | matched in NCEI with \|lon\| ≤ 68 and a qualifying record at peak − 24 h | 121 → 119 matched → 52 with location → 19 \|lon\| ≤ 68 → 8 | `data/diag/d7_location_proxy_catalogue.csv`; `r_runs.log` ("NCEI-location admissions 8") | MATCH |
| 39 | "our 2,322 HARPs (2010-05 → 2014-05) vs B&C's '2,071 ARs'" | PS:78 | distinct HARPNUM in the hourly cache, 2010-05-01…2014-05-31 | 2,322 HARPs (801 with a NOAA number; 1,006 distinct NOAA ARs); 2,071 is B&C's | recomputed from `data/raw_sharp_*` | MATCH (ours); B&C unit NOT CHECKABLE |
| 40 | "Ahmed et al. 2013 definitions … original was not read" | PS:79 | | as stated | D:2190–2196 | NOT CHECKABLE |
| 41 | "R1 0.515, R2 0.520, R4 0.530, R4-cgem 0.507 / R1 0.706, R2 0.708, R4 0.695, R4-cgem 0.695; targets 0.562–0.658 and 0.722–0.800" | PS:80–83 | 1,000 splits each; targets = B&C mean ± 1 SD | exactly these; 0.610 ± 0.048 = 0.562–0.658 and 0.761 ± 0.039 = 0.722–0.800; SDs 0.038–0.051 | `data/diag/r_runs.csv` | MATCH |
| 42 | "3 dev episodes … (HARPs 4231 true, 6975 delayed, 3248 false)" | PS:86 | rule P6 | as stated | `data/euv_pilot_episodes.csv` | MATCH |
| 43 | "6 HMI files and 717 AIA 12-min frames" | PS:88 | items 1–3 | 2 × 3 HMI; 120 + 118 + 120 + 120 + 119 + 120 = 717 | `data/euv_pilot/check.csv` | MATCH |
| 44 | "HARP 6975 is missing 3 frames" | PS:89 | items 2 + 3 | 2 (94 Å) + 1 (1600 Å) | check.csv | MATCH |
| 45 | "the primary feature is now CV_PIL − CV_ctrl" | PS:91 | superseded by D-CTRL (20 random draws) as primary (D:2240ff), then by the flare-kept draft amendment (not recorded) | D-CTRL ΔCV is the current primary | D:2109, D-CTRL entry | MATCH (updated since by D-CTRL) |
| 46 | "Item 4 … paused by the user at 191 of 1,800 files for HARP 4231" | PS:92 | | **item 4 complete: 1,800 files × 3 HARPs** (4231 per file; 6975, 3248 url-tar) | `data/euv_pilot/download_log.csv` | MISMATCH (outdated) |
| 47 | "JSOC allows 1 pending export per address" | PS:93 | status-7 response | as stated; the next export is accepted once the previous is complete (0 rejections in 25) | D:2099–2101; `data/euv_cad/cutouts*.log`, `cut131.log` | MATCH |
| 48 | "Download cost is dominated by ~7–8 s per file" | PS:94 | | later per-file rate ~3.55 s/file (4231: 3,244 s, ~914 files); url-tar 1,800 frames in 844.5 s | download_log.csv | MISMATCH (outdated) |
| 49 | "Not yet delivered: the cost table and Checkpoint 2" | PS:95 | | cost table delivered | `data/euv_cad/cost_full_study.csv`; commit 9a56c68 | MISMATCH (outdated) |
| 50 | "EUV item 4, the cost table, and the full-study download plan" (open) | PS:99 | | item 4 and the cost table done; full download awaiting go-ahead | as above | MISMATCH (outdated) |
| 51 | "confirmation set … paused. Data is fetched; overlap exclusion and ≤ 2 fallback decided but not applied" | PS:100 | | as stated | D:1853–1860 | MATCH |
| 52 | "a 137 MB CSV remains in git history" | PS:102 | | raw combined CSV 136,646,561 B | file size; D:667–670 | MATCH |
| 53 | "Codex: … `verification/` … 2010-05 → 2016-04" | PS:107 | | as stated | D:678–701 | MATCH |
| 54 | commit hashes in §11 (41 cited) | PS:111–135 | `git log` | all exist; messages match the stated decisions | `git log -1 <hash>` | MATCH |

## B. verification/claude_chat_status_to_verify.md

| # | claim (quoted) | source | exact definition | verified value | evidence | status |
|---|---|---|---|---|---|---|
| 55 | "hourly: 254,899 labelled rows after dedup" | CH:8 | | 254,899 | labelled file | MATCH |
| 56 | "Region numbers: 4-digit Reg# + 10000" | CH:9 | | as stated | D:169 | MATCH |
| 57 | "K2 = true irradiance (GOES-13/14/15 fluxes ÷ 0.7), per NOAA/NCEI recommendation (Hudson et al. 2023; SWSC 2025)" | CH:10 | | rule MATCH; citations as recorded | D:814–825 | MATCH (citations NOT CHECKABLE) |
| 58 | "Filters: QUALITY == 0, \|LON\| ≤ 45°, usable NOAA mapping. Primary subset = single-region HARPs" | CH:11 | primary subset = single-region **rows** (noaa_ar_count == 1) | as stated | spec `primary_subset: noaa_ar_count == 1` | DEFINITION WRONG (rows, not HARPs; a HARP can be single-region in some hours only, D:521) |
| 59 | "Empty SWPC days checked against GOES XRS flux; missing/low-coverage days excluded" | CH:12 | | 835 empty days: 824 genuine zero, 3 C1, 5 no data, 3 low coverage → 8 label-missing days | goes_empty_days.csv | MATCH |
| 60 | "Years excluded by fixed ≥90% region-join rule: 2020; 2022 (primary test; kept as sensitivity)" | CH:13 | | 2020 0%; 2022 89.7% | jr | MATCH |
| 61 | "HEK's SWPC events lose NOAA region numbers (ar_noaanum = 0) — almost entirely after ~2020, some already in 2014" | CH:16 | HEK-era M1+ with unknown region | 2010–2019: 32 in total (2014: 15/224); 2020 2/2; 2021 14/31; 2022 173/195; 2023 284/334; **2024 72/949 (7.6%)** | `data/join_report.csv`; `data/pathA/hek_ar_zero_by_year.csv` | MATCH (concentrated in 2021–2023; 2024 low) |
| 62 | "ALREADY PUBLISHED: Hu et al. 2026 (arXiv:2512.13417, p. 9)" | CH:16 | | recorded | D:2396–2401 | NOT CHECKABLE |
| 63 | "SWPC flare classes change scale in late 2019 (GOES-15 ×0.7 operational → GOES-16 true flux)" | CH:17 | SWPC `Obs`: G13/14/15 to 2019-11, G16/18 from 2019-12 | as stated | D:351–358 | MATCH (Hu Fig. 4 NOT CHECKABLE) |
| 64 | "HMI QUALITY bit 0x10000 (QUAL_LOWINTERPNUM) removes ~all 06:00/18:00 TAI records" | CH:18 | | 99.5% fail; dominated by 0x10000 | raw file (recomputed); D:754–758 | MATCH |
| 65 | "Month-boundary duplicate records … (fixed)" | CH:19 | | 393 labelled duplicates removed | recomputed | MATCH |
| 66 | "SWPC M1+ completeness vs GOES flux (sampled Marches): 134/137 (~98%)" | CH:20 | distinct GOES M1+ flares | 134/137 = 97.8% | #11 | MATCH |
| 67 | "Residual GOES-15 vs GOES-16 calibration difference ~8% (NCEI ratio 0.923)" | CH:21 | | as recorded | D:1003 | NOT CHECKABLE |
| 68 | "NCEI/NGDC GOES XRS flare report has NO flare locations for 2011 (0 of 2,171 rows)" | CH:22 | goes-xrs-report_2011.txt | 0 of 2,171 | `data/ngdc/xrs_2011.txt` (recomputed) | MATCH |
| 69 | "Their flare list cannot be rebuilt from today's public files" | CH:22 | inference | not established: B&C may have used another version or source | — | NOT CHECKABLE (inference) |
| 70 | "Dev … grouped 5-fold CV by HARP. Test: 2021, 2023, 2024 (2022 sensitivity). split.csv hash f3ab4056" | CH:25 | | as stated | spec; split | MATCH |
| 71 | "Positive single-region HARPs: dev ~86; primary test 55" | CH:26 | HARPs with ≥ 1 positive single-region row | dev 86; test 55 | s2 (pooled pos_HARPs); g5 (region positives) | MATCH |
| 72 | "RBF, C=4, γ=0.075, C1/C2=2; median/SD scaling; training rows thinned to TAI hours {4,10,16,22}" | CH:29 | | as stated | spec | MATCH |
| 73 | "Threshold = max TSS on pooled out-of-fold scores (−0.9925)" | CH:30 | | −0.992496 | spec | MATCH |
| 74 | "Dev OOF TSS 0.679 (region bootstrap 95% CI 0.59–0.75)" | CH:31 | hour-level TSS; CI by resampling HARPs (1,000) | 0.6793 [0.5863, 0.7484] | pa (K2 dev hour); D:1310 | MATCH ("region bootstrap" = HARP resampling of hour-level TSS) |
| 75 | "Test 2021/23/24: hour-level TSS 0.547 [0.41, 0.66], FAR 0.70; region-level TSS 0.728 [0.63, 0.82]" | CH:32 | | 0.5467 [0.4120, 0.6598], FAR 0.7021; 0.7284 [0.6301, 0.8198] | g5 | MATCH |
| 76 | "13-feature gate: only used in the reproduction and, optionally, as a labelled robustness gate" | CH:33 | | the recorded optional robustness gate is **SolarMonitor**, not a 13-feature gate | D:562 | NOT FOUND |
| 77 | "do 24 h relative slopes of USFLUX and TOTUSJH add information beyond gate score + C/M/X flare history (48 h)?" | CH:36 | | as stated | D:568–578 | MATCH |
| 78 | "Test Δ log-loss(A − B) = −0.0051, 95% CI [−0.020, 0.009]; AUC A 0.811 vs B 0.797. All robustness variants near zero" | CH:37 | as #27 | −0.005089 [−0.020108, 0.009405]; AUC 0.8111 / 0.7974; \|Δ\| ≤ 0.0067 in all 12 rows | m5 | MATCH |
| 79 | "Conclusion: no detectable improvement … Does NOT show magnetic evolution is uninformative in general" | CH:38 | interpretation | no conclusion wording recorded for the primary result | D:1657–1659 (FINAL, no wording) | NOT FOUND |
| 80 | "Dev exploratory: gate score alone gave the lowest log-loss; adding C/M/X counts did not improve it" | CH:39 | dev cohort, primary (547, weighted) | (i) 0.3260 < (iii) 0.3336 < (ii) 0.3764 | `data/stage4/stepA_dev.csv`; D:1724 | MATCH |
| 81 | "Table 2 TSS 0.610 ± 0.048 (C1/C2 = 2); Table 3 0.761 ± 0.039 (C1/C2 = 15). ± = SD over 1,000 random 70/30 splits" | CH:42 | | as recorded | D:1279–1283, D:1837 | NOT CHECKABLE (external) |
| 82 | "D7/D8 0.527 / 0.716; R1 0.515 / 0.706; R2 0.520 / 0.708; R4 0.530 / 0.695; R4-cgem 0.507 / 0.695; D7t 0.707" | CH:43 | | all as stated | repeats CSVs; r_runs.csv | MATCH |
| 83 | "Pre-registered target (±1 SD) not reached" | CH:43 | targets pre-registered for R runs only | no R run in target; D7t (0.707) lies **above** the Table 2 range but had no target | r_runs.csv | MATCH (applies to R runs) |
| 84 | "Same qualitative behaviour, consistently 0.05–0.08 lower TSS" | CH:44 | our TSS − B&C TSS | D7 −0.083, D8 −0.045; R1 −0.095/−0.055; R2 −0.090/−0.053; R4 −0.080/−0.066; R4-cgem −0.103/−0.066 → **0.045–0.103 lower** | r_runs.csv, repeats CSVs | MISMATCH (0.05–0.08 holds for D7/D8 only, as in the user's D8 wording, D:1954) |
| 85 | "Likely causes (none proven): changed NGDC catalogue (no 2011 locations), unstated details …, possible SHARP reprocessing" | CH:44 | hypotheses | the fact "no 2011 locations" MATCHes #68; the causes are untested | — | NOT CHECKABLE |
| 86 | "Wording: 'not fully reproducible from the published description'" | CH:45 | | not in decisions.md; the recorded conclusions are D:1450–1453 and D:1954 | grep decisions.md | NOT FOUND |
| 87 | "Paper inconsistency: top-4 feature list differs between p. 25 and p. 32" | CH:46 | arXiv:1411.1405v1 pages | p. 25: 4th = "total unsigned flux"; p. 32: 4th = "total unsigned vertical current" | arXiv PDF text (session copy) | MATCH |
| 88 | "Ablation (dev): same gate scores 0.34–0.81 depending only on evaluation choices" | CH:47 | | range 0.335–0.812 is correct, but only D1 reuses the same scores; D2 changes labels, D3 the population, D4 the training/evaluation samples, D5 the training folds | ablation.csv; D:1229–1234 | DEFINITION WRONG |
| 89 | "random split ~+0.11 vs region-grouped" | CH:47 | D5 − baseline | seed 0: 0.790 − 0.679 = +0.111; 20-seed means 0.7912 − 0.6760 = +0.115 | ablation.csv; `uncertainty_seeds.csv` | MATCH |
| 90 | "Metric D-CTRL: CV of detrended mean intensity … PIL mask (±150 G, 16 px dilation, 30 G AR mask) minus mean CV of 20 pixel-count-matched random controls (seeds 0–19)" | CH:50 | ΔCV = mean over 20 draws of (CV_PIL − CV_ctrl,k); PIL subsampled only if ctrl_short | equivalent when not ctrl_short | D-CTRL verbatim entry; `euv_dctrl.py` | MATCH |
| 91 | "Pilot: 3 dev episodes (HARP 4231 true, 6975 delayed, 3248 false)" | CH:51 | | as stated | euv_pilot_episodes.csv | MATCH |
| 92 | "Cost: JSOC 1 export at a time; 12 s cadence ruled out" | CH:52 | | 1 pending export MATCH; 12 s was never formally ruled out, it was simply not in the pre-registered candidate set {2, 3, 6, 12} | D:2099; combined-test entry | NOT FOUND (no explicit decision; implicit) |
| 93 | "url-tar test: HARP 6975, 1,800 files in ~14 min (prep 475 s + download 375 s) vs ~105 min per-file (HARP 4231) ≈ 7.5× faster" | CH:52 | 105 min = extrapolation of the 4231 per-file rate | 6975: wall 844.5 s (475 + 375); 4231: 3,244 s for ~914 files = 3.55 s/file → ~106 min per 1,800 | download_log.csv | MATCH (105 min is extrapolated, not a single measured run) |
| 94 | "Synoptic vs cutout ΔCV (24 h, same masks): max \|diff\| 0.017 (HARP 4231 94 Å), ≤0.004 in 5 of 6" | CH:52 | current values (exposure rule applied) | 4231 94 Å: \|−0.1171 − (−0.1361)\| = **0.0190**; the others 0.0015, 0.0008, 0.0008, 0.0021, 0.0038 | `data/euv_pilot/dctrl_cutout.csv`, `dctrl_synoptic.csv` | MISMATCH (0.017 was pre-exposure-rule, `*_preexp.csv`) |
| 95 | "→ synoptic viable (n = 3)" | CH:52 | | superseded: pre-registered source rule **FAILED** (median 0.0183, ρ 0.600, n = 6) → JSOC cutouts | `data/euv_cad/source_decision.csv` | MISMATCH (superseded) |
| 96 | "HARP 6975 1600 Å synoptic: 8 of 120 files missing in archive" | CH:52 | | 112 frames | dctrl_synoptic.csv | MATCH |
| 97 | "ΔCV 12 s vs 12 min: 4231 0.208 vs 0.150 (+0.058), 6975 0.212 vs 0.232 (−0.021), 3248 0.178 vs 0.198 (−0.020)" | CH:53 | 6 h window, 94 Å, D-CTRL | current: 4231 **0.2086** vs 0.1497 (+0.059); 6975 0.2116 vs 0.2322; 3248 0.1780 vs 0.1980 | `dctrl_cadence.csv` | MISMATCH (4231 12-s value 0.208 → 0.209 after the exposure rule; others MATCH) |
| 98 | "Ranking of the 3 HARPs changes with cadence" | CH:53 | | (a) 6975 > 4231 > 3248; (b) 6975 > 3248 > 4231 | dctrl_cadence.csv | MATCH |
| 99 | "± reported = control-draw spread only, not sampling error" | CH:53 | SD across 20 draws | as stated | `euv_dctrl.summarise` | MATCH |
| 100 | "offset-subsampling test proposed" | CH:53 | | done: percentile of the current value 24.2 / 84.2 / 94.2 | `data/euv_pilot/offset_test_12s_94.csv`; D:2507ff | MISMATCH (outdated) |
| 101 | "JSOC per file ~3.5 s/file; url-tar 14 min / 1,800 frames" | CH:54 | | 3.55 s/file; 844.5 s | download_log.csv | MATCH |
| 102 | "synoptic 1.08 files/s (6 connections)" | CH:54 | 20-file test | measured in the session scratchpad, not saved; the saved full run gives **2.06 files/s at 12 connections** | `data/euv_cad/run.log`; D:2536 | NOT FOUND (1.08 not in repo) |
| 103 | "Rough full-study estimate …: synoptic both channels ~21 h; JSOC url-tar ~1 day per channel" | CH:54 | 547 dev alarms | synoptic at 1.08/s: 2 × 40,070 / 1.08 = 20.6 h (at 2.06/s: 10.8 h); JSOC measured projection **14.3 h for 2 channels pipelined (~7 h/channel)** | cost_full_study.csv | MISMATCH (JSOC part) |
| 104 | "40,070 unique 12-min timestamps for 547 dev alarms" | CH:54 | union of (t−24h, t] 12-min slots | 40,070 | recomputed from `data/stage3/cohort_dev.csv` | MATCH |
| 105 | "url-tar being timed" | CH:54 | | timed: 25 exports | `cutout_timing_*.csv` | MISMATCH (outdated) |
| 106 | Dissauer, Leka & Wagner 2023 details | CH:57 | | — | — | NOT CHECKABLE |
| 107 | Kniezewski et al. 2024 details | CH:58 | | — | — | NOT CHECKABLE |
| 108 | Zhong, Kolotkov & Nakariakov 2026 details | CH:59 | | — | — | NOT CHECKABLE |
| 109 | Nishizuka et al. 2018 details | CH:60 | | — | — | NOT CHECKABLE |
| 110 | Galvez et al. 2019: "built FROM the AIA synoptic series (4×4 averaged → 1024×1024, 2.4"/px, 2-min cadence)" | CH:61 | | the synoptic series properties MATCH the JSOC README (1024², 2.4″, 2-min, level 1.5, DN per original pixel); the SDOML provenance is external | JSOC README (session); D:2507ff | NOT CHECKABLE (SDOML part) |
| 111 | "12-min sampling has Nyquist 0.69 mHz …; 3-min … reaches 2.8 mHz" | CH:62 | 1/(2Δt) | 1/1,440 s = 0.694 mHz; 1/360 s = 2.78 mHz | arithmetic | MATCH |
| 112 | "FILE ERROR: 'doria_rosales_2026_multimodal_forecast.pdf' is … Brevi et al." | CH:65 | | — | — | NOT CHECKABLE (file not in repo) |
| 113 | BADPIT "PIA = \|B\| > ±150 G masks dilated 16 HMI px (8") overlap, AR mask 30 G — IDENTICAL to our D-CTRL PIL mask" | CH:66 | | the parameters match our recorded BADPIT extraction and `euv_pilot.py` (150 G, 16 px, 30 G); the v2/journal status is external | D:1912–1913; `euv_pilot.py` constants | MATCH (parameters); publication NOT CHECKABLE |
| 114 | Leka et al. AARP II; Dissauer et al. 2025; Harra et al. 2026; Jonas et al.; Nishizuka 2017/2021; Alatoom & Nikolaou 2026; Roy et al. | CH:67–73 | | — | — | NOT CHECKABLE (9 claims) |
| 115 | "Pattern: every physics/precursor study here uses ≤3 min cadence …" | CH:74 | interpretation | — | — | NOT CHECKABLE |
| 116 | "Cadence rule → 12 min passes (ρ 0.952 [0.615, 1.000], median \|Δ\| 0.0077, n = 8; cutout second opinion ρ 1.000, median 0.0174, n = 5)" | CH:77 | synoptic 94 Å; alarms valid at both cadences | as stated | `agreement_synoptic.csv`, `agreement_cutout.csv` | MATCH |
| 117 | "synoptic FAILS (median \|diff\| 0.0183, ρ 0.600 [−0.636, 1.000], n = 6) … 0 rejections in 25 overlapped exports" | CH:78 | | as stated; 10 + 15 exports, no "OVERLAP REJECTED" in the logs | source_decision.csv; cutouts.log, cutouts_resume.log, cut131.log | MATCH |
| 118 | "Exposure rule adopted; crop verified" | CH:79 | \|ΔCV_crop − ΔCV_full\| < 1e-6 | \|diff\| = 0 for 3 HARPs | `data/euv_cad/verify_crop.csv` | MATCH |
| 119 | "only 8/15 alarms valid at 2 min; 131 Å 10/15 valid at 12 min → risk of label-dependent exclusion" | CH:80 | ≥ 90% filled by valid frames | 8/15 (true 2/8, false 6/7); 131 Å 10/15 | `validity_summary.csv`; `cv_cutout_131.csv` | MATCH |
| 120 | "94+1600 Å 86,060 files, 18.6 GB, ~14 h download, 3.3 h processing; +131 Å 129,090 files, 32 GB, ~21.5 h. HMI mask exports not included" | CH:81 | 547 dev alarms, 12-min cutouts, 180 per-HARP exports/channel, pipelined; 1600 Å cost assumed = 94 Å | 86,060; 18.6; 14.3; 3.3; 129,090; 32.0; 21.5; HMI not included | cost_full_study.csv | MATCH |
| 121 | "52 of 852 alarms (6.1%) counted 'false' with HEK are real M1+ flares in SWPC originals" | CH:85 | **episodes** (T1–T4), HEK-false → K2-true, 2010–2024 excl. 2020 | 52/852 | `data/diag/patha_phantom_HEK_vs_K2.csv` | DEFINITION WRONG ("alarms" = alarm episodes; "real M1+ flares" = K2-positive at t) |
| 122 | "34 of 386 (8.8%) in 2021–24 (2022: 15, 2023: 17). 0 region-loss phantoms in 2010–19. Scale-only effect (K → K2): 45 of 846" | CH:85 | episodes | 34/386; HEK vs K 2010–19 phantoms 0; K→K2 45/846 | patha_phantom_*.csv | MATCH |
| 123 | "hourly FAR HEK 0.838 [0.760, 0.911] vs K2 0.733 [0.661, 0.804]; difference 0.105 [0.066, 0.147]" | CH:87 | 2021–2024 incl. 2022, single-region, 5,145 alarm hours, 2,000 HARP resamples, seed 0 | 0.8383 [0.7599, 0.9112]; 0.7331 [0.6609, 0.8040]; 0.1052 [0.0662, 0.1466] | pac | MATCH |
| 124 | "region FAR HEK 0.763 [0.691, 0.829] vs K2 0.576 [0.494, 0.659]; difference 0.187 [0.122, 0.252]" | CH:88 | 139 alarmed regions of 605 | 0.7626 [0.6905, 0.8288]; 0.5755 [0.4937, 0.6593]; 0.1871 [0.1224, 0.2517] | pac | MATCH |
| 125 | "34 phantoms in 20 HARPs (2021: 2, 2022: 15, 2023: 17, 2024: 0). HEK region number 0: 27; two HEK events both 0: 3; no HEK event within ±10 min: 4" | CH:89 | | as stated | `data/pathA/phantoms_2021_24.csv` | MATCH |
| 126 | "Evidence pack … HARPs 8942, 9121, 9182 (2023) — HEK AR = 0 AND location fields zero (hpc_x 0, hgs 0/0)" | CH:90 | | as stated | `data/pathA/evidence/*/hek_record.csv` | MATCH |
| 127 | "Primary test years only: hourly FAR HEK 0.801 vs K2 0.702, diff 0.099 [0.057, 0.150]; region FAR 0.724 vs 0.543, diff 0.181 [0.112, 0.259] (105 alarmed regions of 450). K2 hourly FAR matches the gate's test FAR (~0.70). 2022 alone: hourly FAR 0.968 vs 0.840; hourly precision HEK 0.032 vs K2 0.160" | CH:91 | | all as stated; K2 hour FAR 0.7021 = g5 FAR 0.7021 | pay; g5 | MATCH |
| 128 | "7 later alarm hours within an episode" | CH:92 | recorded reason: "K2-positive alarm hour that is not an episode's t"; episode membership **not checked** | 7 | `data/pathA/region_flips_2021_24.csv` | DEFINITION WRONG |
| 129 | "flip because region-level truth = 'region flared at all'" | CH:92 | region truth = ≥ 1 labelled hour with M1+ in its (t, t+24h] | 4 regions | region_flips csv; `diag_patha3.py` | DEFINITION WRONG (not "flared at all"; flared within 24 h after some labelled hour) |
| 130 | "all 34 phantom flares are GOES-16 (30) / GOES-18 (4) … HEK class = SWPC class for all 30 with HEK events" | CH:93 | first SWPC M1+ after t | Obs G16 30, G18 4; HEK class list contains the SWPC class in 30/30 (exact single match 27; 3 have two HEK events) | phantoms_2021_24.csv | MATCH |
| 131 | "Phantoms caused by HEK AR = 0, not by K2" | CH:93 | | 30/34 have HEK events with AR = 0; **4/34 have no HEK event at all** (±60 min, start and peak) | phantoms csv; `no_hek_phantoms_pm60min.csv` | DEFINITION WRONG (4 are missing from HEK, not AR = 0) |
| 132 | "Open: 2024 zero phantoms (HEK AR=0 counts per year running); 4 'no HEK event' cases (±60 min search running)" | CH:94 | | done: HEK 2024 AR=0 72/949 (7.6%); 0 of 8 searches found an event | fb1fdd4; hek_ar_zero_by_year.csv | MISMATCH (outdated) |
| 133 | Hu et al. 2026 details (authors, >3,000 flares AR = 0, p. 9, Fig. 4, Section 4/5, Table 11) | CH:95–97 | | recorded by Claude chat | D:2396–2401 | NOT CHECKABLE |
| 134 | Pending list: "reconcile 26 vs 20 regions; 2024 zero phantoms; 4 no-HEK-event cases; primary-test-years-only … EUV: 12 s cadence check; synoptic D-CTRL rerun …; url-tar timing; choose source" | CH:100–101 | | all done (fb1fdd4, 9a56c68) | commits | MISMATCH (outdated) |
| 135 | "2025–2026 fresh confirmation set — paused" | CH:102 | | paused | D:1853 | MATCH |
| 136 | "Research plan NOT yet written or signed" | CH:106 | | recorded "not yet signed at this point" on 2026-09-21; the current status is not recorded | D:1014 | NOT CHECKABLE (current status) |
| 137 | "AI use: Claude Code wrote code; Codex ran an earlier exploratory run …; Claude chat drafted instructions" | CH:107 | | Claude Code and Codex MATCH D:712–717; the Claude chat role appears in D:2396 ("recorded by: Claude chat") but not in the AI-use list | D:712–717 | MATCH (AI-use list should add Claude chat) |
| 138 | "IRIS deadline still unknown" | CH:109 | | — | — | NOT CHECKABLE |

## C. decisions.md result sections (table cells cross-checked against CSVs; one row per table)

| # | claim | source | definition | verified value | evidence | status |
|---|---|---|---|---|---|---|
| 139 | Stage 2 per-fold/pooled table (30 cells) | D:1052–1059 | dev OOF, single-region | 26/30 cells identical; 4 differ by ≤ 0.001 because the table predates the duplicate fix (pooled 0.6789 → 0.6793, documented) | s2; D:1096–1100 | MATCH (superseded, documented) |
| 140 | Stage 3b cohort (547 / 98 / 449 / 47 / 180 / 41 / 24.13) | D:1358 | dev, T1–T4 | 547, 98, 47 delayed, 180 HARPs, 41 true HARPs, weighted true 0.1341 × 180 = 24.14 | `data/stage3/cohort_dev.csv` | MATCH |
| 141 | Stage 4 pooled Δ 0.0043 [−0.0114, 0.0253]; LL 0.3336 / 0.3293; AUC 0.7432 / 0.7695 | D:1498–1500 | dev OOF, weighted, 1,000 HARP resamples | 0.004308 [−0.011435, 0.025286]; 0.333575 / 0.329267; 0.743196 / 0.769536 | `data/stage4/cv_primary.csv`; `stage4_result.json` | MATCH |
| 142 | Stage 5 gate table (168 cells) | D:1570–1595 | | 168/168 | g5 | MATCH |
| 143 | Stage 5 models table (84 cells) | D:1612–1625 | | 84/84 | m5 | MATCH |
| 144 | Stage 5 cohort sizes and matched pairs | D:1599–1636 | | all cells identical | `cohort_sizes.csv`, `pairs_summary.csv` | MATCH |
| 145 | Step A table (12 cells) | D:1690–1697 | | 12/12 | stepA_dev.csv | MATCH |
| 146 | Ablation (21 cells) and 20-seed table (35 cells) | D:1242–1304 | | all identical | ablation.csv; uncertainty_seeds.csv | MATCH |
| 147 | Bootstrap: baseline 0.6793 [0.5863, 0.7484]; D6 0.6865 [0.5624, 0.7827] | D:1310–1311 | | baseline reproduced (pa dev K2 hour); D6 has no saved artefact | pa | MATCH (baseline) / NOT FOUND (D6) |
| 148 | D7 / D7t / D8 / D7b | D:1422, 1447, 1847, 1423 | | 0.5267 ± 0.0500; 0.7065 ± 0.0401; 0.7155 ± 0.0403; D7b 0.5861 [0.4665, 0.6800] | repeats CSVs; `diag_d7.log`:14 | MATCH |
| 149 | SWAN-SF validation (18 cells) | D:2211–2218 | | 18/18 | swansf_validation.csv | MATCH |
| 150 | R1–R4 table | D:2247–2256 | | identical | r_runs.csv | MATCH |
| 151 | Path A gate table (60), follow-up CIs (36), by-years CIs (72), phantom tables | D:2341–2440 | | 168/168 cells; phantom totals 52/852, 20/852, 45/846 | pa, pac, pay, patha_phantom_*.csv | MATCH |
| 152 | GOES empty-day table | D:323–335 | K-era thresholds | superseded by K2 (2 days changed, D:847–849); current: 824 / 3 / 5 / 3 | goes_empty_days.csv | MATCH (superseded, documented) |
| 153 | K2 per-year M1+ and positive rows | D:862–876 | pre-dedup rows | all 15 years identical to jr (e.g. 2024: 935 M1+, 4,599 rows; post-dedup file 4,591) | jr; labelled file | MATCH (pre-dedup, documented D:1092) |
| 154 | K2 completeness 140 / 134 / 6 | D:937–945 | | identical | completeness_check.csv | MATCH |
| 155 | Validation 1,281 of 1,285 SWPC matched | D:243–248 | | identical | validate_swpc.log:23 | MATCH |
| 156 | Audit 2018–2020 table | D:987–996 | | identical ("BUG count: 0") | audit_2018_2020.log | MATCH |
| 157 | EUV combined test: Phase 1 exposure (36 cells), agreement (24), source (3), cost, crop, validity, 131 Å | D:2507–2670 | | 28/36 exposure cells printed (the other 8 recorded as "unchanged", confirmed); all other cells identical | `data/euv_pilot/exposure_rule_old_vs_new.csv`; `data/euv_cad/*.csv` | MATCH |
| 158 | Flare-followed fraction (18 cells) | D:2673–2690 | | 18/18 | `data/stage5/flare_rate_by_alarm_primary.csv` | MATCH |
| 159 | Step 0: 2,322 HARPs, 801 with NOAA, 1,006 NOAA ARs | D:2197–2199 | | identical | recomputed | MATCH |

## Same quantity, different definitions

- **True-alarm rate:**
  - Dev episodes: 98/547 = **17.9%** (unweighted); region-weighted 24.13/180 = **13.4%**.
  - Test primary episodes: 45/313 = **14.4%** (unweighted); weighted 14.46/98 = **14.8%**.
  - Test **region** level: 48/105 = **45.7%** of alarmed regions have ≥ 1 flare-followed hour.
  - Test **hour** level: precision 1,188/3,988 = **29.8%**.
  - The unit differs: an episode is judged at its single t; a region is positive if any hour is; an hour is judged on its own window.
- **FAR (test, primary, K2):** hour 0.702; region 0.543; episode false fraction 268/313 = 0.856. Same unit differences.
- **Dev TSS 0.679 vs D6 0.687:** the first is hour-level OOF on all rows with the max-TSS threshold; the second uses B&C-style samples, a random split and threshold 0.
- **Region counts:** B&C "2,071 ARs" (unit not stated) vs our 2,322 HARPs vs 1,006 NOAA ARs (2010-05 → 2014-05). These are different counting units.
- **Phantoms:** 34 episodes vs 26 flipping regions vs 20 HARPs. Region flips also come from non-episode alarm hours (7) and from positives outside alarm hours (4).
- **GOES completeness:** 134/137 (distinct flares) vs 134/140 (raw peaks, including 3 decay artefacts).
- **EUV validity, synoptic:** 8/15 valid at 2 min; 11/15 valid at 12 min; n = 8 = alarms valid at **both**, the cadence-test sample.

## (a) Rows needing correction

**MISMATCH**
- #46 PS:92: item 4 is complete, no longer "paused at 191".
- #48 PS:94: the per-file cost is ~3.55 s/file, and url-tar is ~0.47 s/frame.
- #49 PS:95 and #50 PS:99: the cost table is delivered, and the open items are outdated.
- #84 CH:44: "0.05–0.08 lower" → **0.045–0.103** across D7/D8/R runs.
- #94 CH:52: the max synoptic-vs-cutout \|diff\| is now **0.019** (0.017 was pre-exposure-rule).
- #95 CH:52: "synoptic viable" is superseded; the source rule failed → JSOC cutouts.
- #97 CH:53: HARP 4231 12-s ΔCV is now **0.209** (was 0.208).
- #100 CH:53: the offset test is done.
- #103 CH:54: the JSOC estimate is **~14.3 h for 2 channels** (~7 h/channel), not ~1 day per channel.
- #105 CH:54: url-tar is timed (25 exports).
- #132 CH:94 and #134 CH:100–101: the listed "open"/"pending" items are all done.

**DEFINITION WRONG**
- #58 CH:11: the primary subset is single-region *rows*, not HARPs.
- #88 CH:47: the ablation is not "same gate scores, evaluation choices only".
- #121 CH:85: "alarms" are alarm *episodes*.
- #128 CH:92: "within an episode" was not checked.
- #129 CH:92: region truth is not "flared at all".
- #131 CH:93: 4 of 34 phantoms are missing from HEK, not AR = 0.

**NOT FOUND**
- #32 PS:67 and #147: the D6 bootstrap CI has no artefact.
- #76 CH:33: no 13-feature robustness gate was decided; SolarMonitor is the optional one.
- #79 CH:38: no conclusion wording was recorded for the primary result.
- #86 CH:45: the "not fully reproducible…" wording is not recorded.
- #92 CH:52: no explicit "12 s ruled out" decision.
- #102 CH:54: the 1.08 files/s test is not saved.

## (b) Ten headline numbers for the report

1. **Primary result: Δlog-loss(A − B) = −0.0051 [−0.0201, 0.0094].** Test 2021/2023/2024, single-region, 313 alarm episodes in 98 HARPs, episode weights 1/n per HARP, HARP bootstrap 10,000.
2. **Gate test TSS, hour level: 0.547 [0.412, 0.660].** 53,356 hours, frozen threshold −0.992496, HARP bootstrap 1,000.
3. **Gate test TSS, region level: 0.728 [0.630, 0.820].** 450 HARPs; a region is alarmed if any of its hours alarms, positive if any of its hours is positive.
4. **Alarmed hours followed by M1+ within 24 h: 29.8% [22.3, 38.3]** (= precision; FAR 0.702). Test primary, K2.
5. **Non-alarmed hours followed by M1+ within 24 h: 1.6% [1.1, 2.2].** Same set.
6. **Test true-alarm episode rate: 45/313 = 14.4%** (weighted 14.8%). Episodes T1–T4, primary.
7. **Dev gate TSS: 0.679 [0.586, 0.748].** Hour level, OOF, 2010–2019, single-region, HARP bootstrap 1,000; mildly optimistic because the threshold was chosen on the same scores.
8. **Closest B&C reproduction: TSS 0.527 ± 0.050 vs published 0.610 ± 0.048.** D7: 1,000 random 70/30 splits, 272 positives / 4,488 negatives, C1/C2 = 2, threshold 0.
9. **HEK vs K2 labels, test primary years: hourly FAR +0.099 [0.057, 0.150]; region FAR +0.181 [0.112, 0.259].** Same frozen alarms, HARP bootstrap 2,000, seed 0.
10. **Phantom false alarms: 34 of 386 HEK-false alarm episodes (8.8%) in 2021–2024 are K2-true.** 20 HARPs; 30 with HEK AR = 0, 4 absent from HEK.
