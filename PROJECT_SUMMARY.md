# Project summary

All numbers verified in VERIFIED_FACTS.md (f572994).

Generated 2026-09-22 from `decisions.md`, `frozen/` and the git log (not from memory). Where this file and
`decisions.md` disagree, `decisions.md` wins. **[unverified]** marks statements no check in this repo establishes.

## 1. Question (decision R)
Does 24-h magnetic evolution (relative slopes of USFLUX and TOTUSJH) add information beyond current magnetic risk
(the gate score) and recent flare history (n_C, n_M, n_X in the previous 48 h)? The target is separating true from
false M1+ alarms. The primary contrast is held-out log-loss(A) − log-loss(B), with a region-level bootstrap 95% CI.
A wide or inconclusive CI was pre-stated as a possible outcome.

## 2. Data and filters
- **SHARP:** `hmi.sharp_cea_720s` keywords only, hourly (`@1h`), 2010-05-01 → 2025-01-01. TAI→UTC via astropy.
  - QUALITY == 0 (stricter than B&C's ≤ 65536). This removes 99.5% of 06:00/18:00 TAI records.
  - |LON_FWT| ≤ 45°.
  - Rows with no NOAA mapping are excluded.
- **Labels:** `flared_M1_next_24h` over (t, t+24h].
  - Flares come from SWPC original daily event reports (NCEI), XRA lines only (A). Reg# < 10000 → +10000; dedup on (begin time, reported class).
  - **True irradiance scale (K2)**: GOES-13/14/15 fluxes ÷ 0.7; GOES-16+ as reported.
- **Missing and empty days:** days with no report exclude overlapping label windows (C). Empty reports are classified with GOES XRS 1-min science data (E, H, I), and `history_incomplete` is set (D).
- **Multi-region:** primary analysis = single-region rows; robustness = ≤ 2 regions and all HARPs, ANY rule (B, M).
- **History control:** n_C, n_M, n_X only; `n_flares_prev_48h` is kept but never used (F, J).
- **Years dropped:** 2020 excluded (L). 2022 removed from the primary test because it fails CHECK 5 at 89.7% (L2).
- **Labelled file (frozen):** `data/labelled_20100501_20250101.csv`, SHA-256 `62a0e4cc…`, 254,899 rows after the month-boundary duplicate fix.

## 3. Data-audit findings
- **HEK drops region numbers**, so HEK was replaced by SWPC originals. SWPC vs HEK, March 2011–2019: class agreement 100%, 1 region disagreement in ~1,100 pairs.
- **835 empty-report days;** none reaches M1 in GOES XRS.
- **SWPC M1+ completeness at K2:** 134 of 137 GOES M1+ peaks in the sampled months. The 3 misses are near-threshold, two beside eclipse gaps. Recorded as label noise.
- **JSOC range queries include both ends:** 393 duplicate labelled rows were removed after checking the copies were identical.
- **The 2018–2020 audit found 0 bugs.** A residual ~8% GOES-15/16 calibration difference is not corrected.
- **2024:** 80% of positive rows are multi-region; B was chosen because of this.

## 4. Split (N, N2)
Held-out split by HARP (`frozen/split.csv`, SHA-256 `f3ab4056…`, seed 20260921).
- Test = 2021–2024 HARPs (801); dev = 2010–2019 (1,218 HARPs); no HARP in two sets.
- Thresholds use grouped, stratified 5-fold CV on dev.

## 5. Gate and its metrics (Q, S, Stage 2)
- **Model:** SVM, RBF, C = 4, γ = 0.075, tol = 1e-8, class weight 2:1. Median/SD scaling inside each training fold.
- **Features:** 10 of B&C's 13 (TOTUSJH, TOTPOT, TOTUSJZ, ABSNJZH, SAVNCPP, USFLUX, AREA_ACR, MEANPOT, R_VALUE, SHRGT45).
- **Training rows:** thinned to TAI hours {4, 10, 16, 22}.
- **Threshold:** −0.992496, maximising TSS on the pooled out-of-fold scores.
- **Dev pooled OOF TSS 0.679** (mildly optimistic).
- **Test, primary years, single-region, frozen threshold:**
  - Hour-level TSS **0.547** [0.412, 0.660].
  - Region-level TSS **0.728** [0.630, 0.820].
  - At decision value 0: 0.323 (hour) and 0.476 (region).
- `frozen/frozen_spec.json` SHA-256 `1d205068…`, verified before the test run.

## 6. Primary pre-registered result (Stage 5, run once; recorded FINAL)
| Setting | Episodes | True | HARPs | Log-loss A | Log-loss B | Δ = A − B | 95% CI (10,000 HARP resamples) |
|---|---:|---:|---:|---:|---:|---:|---|
| Primary years, single-region, all eligible episodes | 313 | 45 | 98 | 0.3686 | 0.3737 | **−0.0051** | **[−0.0201, 0.0094]** |

- **Robustness and sensitivity:** Δ ranges from −0.0067 to +0.0054, and every CI includes 0.
- **Score-matched pairs** (41 pairs): CIs for both slope differences include 0.
- **2021–2024 is closed:** no new analysis may be run on it.

## 7. Replication diagnostics (dev period only; the gate is unchanged by all of them)
- **D1–D6 ablation** (OOF TSS): baseline 0.679.
  - D1: threshold 0 → 0.335.
  - D2: K labels → 0.677.
  - D3: ±68° → 0.646.
  - D4: B&C samples → 0.812.
  - D5: random row split → 0.790.
  - D6: D1–D5 together → 0.687. (Its bootstrap CI [0.562, 0.783] is recorded in decisions.md only; no saved artefact. VERIFIED_FACTS #32.)
- **D7 closest reproduction** (272 pos / 4,488 neg, 1,000 random 70/30 splits):
  - C1/C2 = 2: TSS 0.527 ± 0.050, vs B&C 0.610 ± 0.048.
  - D7t (threshold learned on the training 70%): 0.707 ± 0.040.
  - D8 (C1/C2 = 15): 0.716 ± 0.040, vs B&C 0.761 ± 0.039.
- **B&C's missing 3 features:** TOTBSQ, TOTFZ and EPSZ are not SHARP keywords, but they **are** keywords in JSOC `cgem.lorentz` (correction, 2026-09-22).
- **SWAN-SF validation** (pre-registered: ρ ≥ 0.95 and median |rel diff| ≤ 10%), 4,757 records:
  - Only masked EPSZ passes.
  - The masked variant is closer on all three parameters.
  - Suggested causes, both **[unverified hypothesis]**: the mask threshold (61 vs 90), and a TOTFZ unit or constant difference.
- **NCEI catalogue:** it would recover 8 of the 121 location-proxy flare losses.
- **Region count:** our 2,322 HARPs (2010-05 → 2014-05) vs B&C's "2,071 ARs"; their counting unit and end date are **[unverified]**.
- **Ahmed et al. 2013 definitions** are taken from B&C's description, and the original was not read: **[unverified]**.
- **R-runs** (defined in `3e04525`; R3 skipped): none reaches the pre-registered TSS target in any run.
  - C1/C2 = 2: R1 0.515, R2 0.520, R4 (SWAN-SF) 0.530, R4-cgem 0.507.
  - C1/C2 = 15: R1 0.706, R2 0.708, R4 0.695, R4-cgem 0.695.
  - Targets: 0.562–0.658 and 0.722–0.800. All values are ± ~0.04–0.05.

## 8. EUV pilot and settings test (exploratory; dev data only)
- **Episodes:** 3 dev episodes chosen by rule P6 (HARPs 4231 true, 6975 delayed, 3248 false).
- **Items 1–3 downloaded from JSOC and checked:**
  - 6 HMI files and 717 AIA 12-min frames.
  - HARP 6975 is missing 3 frames.
- **Processing:** approved registration method on cutouts, QUALITY ≠ 0 exclusion and the trailing baseline, plus `aiapy.update_pointing`.
- **Primary feature:** first the design fix CV_PIL − CV_ctrl, then superseded by D-CTRL: ΔCV = mean over 20 pixel-count-matched random control draws (seeds 0–19).
- **Item 4 (12-s cost test): done.** 1,800 files for each of the 3 HARPs.
  - HARP 4231: per file, ~3.55 s/file.
  - HARPs 6975 and 3248: `url-tar`. HARP 6975 took 844.5 s in total (prep 475 s + download 375 s).
- **JSOC:** 1 pending export per address. The next export is accepted once the previous one is complete (0 rejections in 25 overlapped exports).
- **Combined EUV settings test (15 dev alarms): done** (decisions.md, 9a56c68):
  - Cadence rule: 12 min passes (ρ 0.952 [0.615, 1.000], median |Δ| 0.0077, n = 8).
  - Source rule: synoptic fails (median |diff| 0.0183, ρ 0.600, n = 6) → full-study source = JSOC cutouts.
- **Cost table: delivered** (`data/euv_cad/cost_full_study.csv`). For 547 dev alarms at 12 min:
  - 94 + 1600 Å: 86,060 files, 18.6 GB, ~14.3 h download (pipelined), 3.3 h processing.
  - Adding 131 Å: 129,090 files, 32.0 GB, ~21.5 h.
  - 1600 Å cost is assumed equal to 94 Å; HMI mask exports are not included.
- **Validity count test: done.** Synoptic at 2 min: 8/15 alarms valid at ≥ 90% (true 2/8, false 6/7). Synoptic at 12 min: 11/15.
- **No true-vs-false ΔCV comparison has been made.**

## 9. Open items
- **Full-study EUV download:** awaiting the user's go-ahead.
  - A draft amendment is not yet recorded (primary = flare frames kept). It needs a count-first threshold rule and a test specification.
- **Done:** EUV item 4; the cost table; the synoptic-vs-cutout and cadence tests; Path A (phantom false alarms, FAR/precision CIs, consistency checks); the full fact check (VERIFIED_FACTS.md).
- The confirmation set 2025-01-01 → 2026-08-16 is **paused**. Data is fetched; overlap exclusion and the ≤ 2 fallback are decided but not applied. Step B (feature R) is pre-registered and not computed.
- AR 11429 / 13186 BADPIT validation (after the pilot).
- The repo must not be pushed: a 137 MB CSV remains in git history, and history will not be rewritten.
- **[unverified]** B&C's threshold rule, and whether their parameter selection used held-out data (not stated).

## 10. AI-use disclosure
- **Claude (Anthropic), via Claude Code:** wrote and ran the pipeline, analyses and diagnostics in this repository. It also drafted the non-decision entries of `decisions.md` and this summary.
- **Claude (chat):** drafted instructions and `verification/claude_chat_status_to_verify.md` (unverified; checked in VERIFIED_FACTS.md).
- **Codex:** generated and ran `verification/`, an exploratory pre-registration run on HEK-era labels, 2010-05 → 2016-04. It is not used in the final analysis, and its results were seen by the user.
- **Scientific decisions:** every one is recorded as the user's. Implementation choices are marked "decided by: me".

## 11. Decisions (ID — one line — commit that recorded it)
- **J1–J5** (join defect): unknown region never joined; ≥ 90% usable-region year rule; SWPC via HEK (later superseded by A); QUALITY == 0; CHECK 5 — `7ab7a12`
- **A** SWPC original reports for all years; **B** single-region primary; **C** no-report days exclude label windows — `4fd57aa`
- **D** `history_incomplete` flag — `b2a713a`
- **E** GOES decides empty days; **F** history = C/M/X; **G** HEK is a cross-check only — `75b0d29`
- **H** secondary-satellite fallback; **I** < 90% coverage = missing; **J** `n_flares_prev_48h` excluded — `c53f080`
- **K** old operational scale (superseded by K2) — `7015872`
- **L** 2020 excluded; **M** single-region primary (fallback not triggered); **N** split — `a19949e`
- **N2** grouped stratified 5-fold CV — `eecc96f`
- **O** fetch B&C keywords; **Q** B&C-style gate; **R** research question (supersedes the unadopted draft P) — `5beac0a`
- **Q amended** 10 features; QUALITY == 0 kept; `data/` untracked, `frozen/` tracked — `c73956c`
- **Repo policy**: no history rewrite, no push — `0ff1757`
- **S** 6-hourly thinning — `e1ca3f0`; **S amended** TAI {4,10,16,22}, fixed B&C hyperparameters — `b423ca4`
- **K2** true irradiance scale — `afa4d17`; **L2** 2022 out of the primary test — `00eaf41`
- **Training authorised**, staged plan, median/SD scaling — `73171b0`; **Checkpoint 2** unscorable-row rule — `b0cea10`
- **T1–T3** episode merging, all-episode unit, 18-of-24 rule — `9cc998a`; **T4** first evaluable hour — `405c80b`
- **D1–D6** ablation — `e5305f7`; ablation uncertainty — `1a2808d`; accepted wording and replication protocol — `405c80b`
- **D7** full-fidelity reproduction — `471021e`; **D7t** — `faf6654`; replication conclusion, Stage 4 released — `b7f5ac0`
- **Checkpoint 4**, Stage 5 prediction rule — `ca53f8b`; Stage 5 test run — `f84a613`
- **Primary result FINAL**; Steps A/B/C — `9745de2`; τ_A, confirmation-set rules, confirmatory tests — `08c474f`
- **Confirmation set frozen** — `e3e4075`; **D8** — `efb0ad7`; confirmation set **paused** and EUV pilot scope — `528d888`
- **EUV part 1** (U1–U10, 3σ only, LoS masks, D8 wording) — `6e1b406`; **EUV part 2** (primary measure, 12-s test, AR 13186 exception) — `65a5900`
- **P1–P6** approved (P2 amended, P4 raw-DN cut, AARP not used) — `463b00c`; **download rules** — `ecabe4b`
- **EUV Checkpoint 2** approvals and **design fix** CV_PIL − CV_ctrl — `d164496`; **item 4 paused** — `3b646a6`
- **D7 improvement** scope — `39b7754`; **correction** (cgem.lorentz), R4a/R4b, SWAN-SF pass rule — `0e78962`
- **R1–R4** definitions (R3 skipped) — `3e04525`; results — see the R1–R4 RESULTS entry
