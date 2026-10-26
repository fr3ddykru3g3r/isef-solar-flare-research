# RESULTS SUMMARY: results hierarchy (factual; not presentation text)

PART 3 of the documentation update requested in decisions.md (8aa1797). This is a new file; no older summary (PROJECT_SUMMARY.md, VERIFIED_FACTS.md) was edited. It was compiled on 2026-09-28 by Claude (chat session) from decisions.md, the git log and the committed logs. Each item gives the number, the CI, the data set and the commit hash. Where a reading is quoted, it is the mechanical pre-stated reading, quoted verbatim.

Set names:
- **dev** = 2010–2019, single-region.
- **test** = 2021/2023/2024, single-region (313 episodes; 306 with EUV).
- **unseen** = 2021/2023/2024 two-region episodes, also called "extra" or "EUV-unseen" (158; 155 with EUV).
- **2022** = 2022 sensitivity set (152).
- **2025–26** = confirmation set, Jan 2025 – Aug 2026, ≤ 2 regions (387; 378 with EUV).

Weights are 1/n per HARP; CIs are HARP bootstraps unless stated otherwise.

---

## A. CONFIRMED (pre-registered, run once)

| # | result | number [95% CI] | set | reading (verbatim) | pre-registration → run |
|---|---|---|---|---|---|
| A1 | **TEST 1: CV_box magnetic twins** (ratio of medians, true ÷ twin; pairs resampled by true HARP, 2,000, seed 0) | **3.262 [1.296, 9.489]**; true > twin in **39/50** pairs; 18 true HARPs | 2025–26 (378 ep., 56 true) | "REPLICATED" | 749208e → ae1b174 |
| A2 | **TEST 2: Step B**, A vs C = A + log(1 + R); Δ = LL(A) − LL(C) (10,000) | **+0.0173 [+0.0016, +0.0350]**; AUC 0.7489 → 0.7527 | 2025–26 (387 ep.) | "C beats A" | 749208e → ae1b174 |
| A3 | Gate, region level (frozen τ −0.9925) | TSS **0.7284 [0.6301, 0.8198]**, 450 HARPs, 48/55 flaring regions caught, region FAR 0.5429 | test | results only; no pre-stated reading recorded | ca53f8b → f84a613 |
| A4 | Gate, hour level | TSS 0.5467 [0.412, 0.660]; FAR 0.702; 53,356 hours | test | as A3 | ca53f8b → f84a613 |
| A5 | **Stage 5 primary: magnetic trends** (Model B vs A); Δ = LL(A) − LL(B) | **−0.0051 [−0.0201, +0.0094]**; AUC 0.811 → 0.797; 313 ep., 98 HARPs | test | no conclusion wording recorded (VERIFIED_FACTS row 79); paper wording: "no added information" | ca53f8b → f84a613 |
| A6 | **Filter test** (PRIMARY, A vs A_CV); D_false / D_true in weighted points (paired, 2,000) | D_false **+60.20 [+46.92, +72.77]**; D_true **−16.17 [−37.58, −1.98]** | unseen (155) | "REMOVES FALSE ALARMS BUT LOSES TOO MANY TRUE ALARMS (point estimate)" | 338c0aa, f7c6646 → 5abc40a |
| A6s | Filter test, secondary and sensitivity rows | unseen C vs C_CV +35.32 [+17.11, +51.85] / −2.60 [−13.33, +3.49]; 2022 A vs A_CV +60.68 / −14.33 [−32.52, −3.42]; 2022 C vs C_CV +30.92 / −8.68 [−27.03, +1.89] | unseen, 2022 | secondary rows cannot change the primary reading | 5abc40a |
| A7 | **2025–26 re-test** (C vs C_CV) | D_false **+24.05 [+14.63, +33.45]**; D_true **−13.98 [−28.47, −4.42]** | 2025–26 (378); "pre-registered re-test on an already-analysed set", not an untouched test | "REMOVES FALSE ALARMS BUT LOSES TOO MANY TRUE ALARMS (point estimate)" | 25fcd66, 6aecccf → 4b65f23 |
| A8 | **Held-out R4a ("spikiness")** A vs A + R4a | Δ **+0.0084 [−0.0227, +0.0418]**; AUC 0.8002 → 0.7737; R4a_nf +0.0080 [−0.0233, +0.0423] | test (306) | "direction consistent, not confirmed" | f3d6489 → 7438177 |
| A9 | Held-out R4a operating point (frozen τ) | false removed +16.27 [+7.27, +25.28] pts (+46 ep.); true kept **−12.96 [−28.73, −1.14]** pts (−4) | test (306) | "condition not met" | f3d6489 → 7438177 |
| A10 | Held-out ΔCV_94 (PIL) E94 vs A | PRIMARY +0.0025 [−0.0074, +0.0139]; S1 +0.0022 [−0.0061, +0.0122]; S2 +0.0055 [−0.0047, +0.0181] | test (306) | not met (see step 6 rule) | 3283478 → 7438177 |
| A11 | Held-out R4c (secondary) | Δ −0.0044 [−0.0218, +0.0140]; operating point: false removed +46.84, true kept −10.57 [−21.37, −2.38] pts | test (306) | secondary; cannot upgrade | f3d6489 → 7438177 |
| A12 | **Held-out replication of F2** (CV_box twins) | **1.306 [0.937, 2.218]**; 25/40 pairs; 25 true HARPs | test | "direction consistent, not confirmed" | 8420876 → ec00afb |
| A13 | SWAN-SF validation (cgem.lorentz vs SWAN-SF on D7 records) | 1 of 6 pass | dev period | pre-stated pass rule | 0e78962 → 73e4959 |

Note on A1: the pre-registered interval resamples only the true side. See C1 for a post-hoc check of region reuse on both sides.

## B. POST-HOC ROBUSTNESS (defined and recorded before computing, after the main result)

| # | check | number [95% CI] | set | commit (recorded → run) |
|---|---|---|---|---|
| B1 | Sensitivity cells: T_a (magnetic twins) / T_b (magnetic + flare-history twins) × V0 (all frames) / V1 (flare frames removed) / V2 (image-only spike removal) | **T_b × V1 = 2.73 [1.10, 6.20]**, 34/47 pairs; T_a × V1 2.92 [1.18, 8.25], 37/49; T_b × V0 2.82 [1.02, 6.82], 35/47 (all 2025–26). T_b × V1: unseen 1.34 [0.67, 2.15]; 2022 2.78 [0.89, 5.44] | 2025–26, unseen, 2022 | 92027fa, 9a6a1dc → 1465063 |
| B2 | V2 image-only spike removal | leaves **0 pairs** at 3 s in all sets (the robust-scale definition collapses on smooth light curves) → failed design, not evidence | all | 1465063 |
| B3 | Noise / exposure / saturation (AIA V3 error table) | photon + read noise ≈ 1% of CV_box; saturated frames removed: 2.69 [1.17, 7.63]; exposure-change frames removed: unchanged | 2025–26 | 947e4c0 → 5af931b |
| B4 | Alert tiers (Model C alarm × CV_box; frozen euv_extra thresholds): weighted M1+ rate [CI]; n | 2025–26 WARNING 26% [15, 38], 154; WATCH 8% [2, 16], 135; NO ALERT 4% [0, 12], 89. Unseen 32% [18, 46] / 2% [0, 7] / 12% [0, 31]. 2022 27% [12, 44] / 5% [1, 11] / 4% [0, 12]. WARNING ÷ WATCH 3.4 [1.4, 11.4]; 15.3 [3.0, 23.2]; 5.9 [1.7, 33.1] | 2025–26, unseen, 2022 | 947e4c0 → 5af931b |
| B5 | Calm-flarer profile | calm share of true alarms 27% (2025–26), 19% (unseen), 25% (2022); 2025–26 calm-flarer median CV_box 0.069 vs false median 0.072 | as B4 | 947e4c0 → 5af931b |
| B6 | Descriptive after confirmation: Model C log(1 + R) coefficient | negative in 5/5 dev folds (−0.198, −0.326, −0.185, −0.261, −0.321; per SD) | dev | eacd2d0 → 5ecb255 |

## C. POST-HOC EXPLORATORY (not results)

| # | item | number | commit |
|---|---|---|---|
| **C1** | **Region-reuse sensitivity of TEST 1.** Defined and computed by Claude AI in chat on 2026-09-28 after an external review; **not recorded before computing**. Structure: 50 pairs, 18 true HARPs (up to 7 pairs each), 41 false HARPs (up to 4 each), 8 HARPs on both sides; 47 pairs form one linked group (4 groups in total). | Intervals for the same ratio 3.262 (2,000 resamples, seed 0): true side [1.30, 9.49] (pre-registered); false side [1.48, 8.94]; **both sides independently (two-way) [0.86, 12.23]**, with 3.8% of resamples ≤ 1 (seed 777: [0.81, 12.56]); 4 linked groups [0.68, 18.87] (unstable). Region level: 14/18 true HARPs have true > twin in most of their pairs (2 tied, 2 minority). | f060c86 (`docs/verification/dependence_sensitivity.py` + `.log`) |
| C2 | Chat post-hoc analyses reproduced with repo label code and frozen models | all 288 compared values match | 4a0eb43 (`docs/posthoc_2026-09-28.md`) |
| C3 | C+ protection rule vs Model C (unweighted true kept / false removed) | dev 91/96, 179/445 vs 88/96, 154/445; 2021–26 146/160, 282/831 vs 150/160, 199/831; 2025–26 52/56, 125/322 vs 54/56, 87/322. Weighted D_false 2025–26 +7.9 [+0.7, +15.5] (post-hoc) | designed after inspection (8aa1797); counts 4a0eb43 |
| C4 | COMBO-T (secondary prospective model; 12-h window, C2.0, from a 90-configuration dev grid) | τ 0.0792 | 9a88d70 → e17a8a3 |
| C5 | Literature-style metrics on 2025–26 (chat) | unclustered pair bootstrap [1.63, 8.04]; Wilcoxon p 1.5e-6; sign test p 9.0e-5 (39/50). These treat pairs as independent and overstate the evidence (see C1). | 4a0eb43 |
| C6 | Descriptive: gate vs persistence; lead time; operating point (not pre-registered) | persistence hour TSS 0.358 [0.244, 0.461] | bb23ec0, 3b7938f, 14083a5 |

## D. FAILED / STOPPED

**D-i. Dev candidates** (EXPLORATORY, dev 2010–2019, internal 5-fold CV). Δ = LL(A) − LL(A + x), HARP bootstrap 10,000. Rows restated in the F7 summary (fcafca8) unless noted.

| # | candidate | Δ [95% CI] | reading / status | original commit |
|---|---|---|---|---|
| 1 | trends (Model B), dev | +0.0043 [−0.0123, +0.0249] | went to Stage 5 (A5): null | 4d83691 |
| 2 | ΔCV_94 (PIL flicker, step 6 PRIMARY) | −0.0043 [−0.0092, +0.0003] | "no detectable improvement" | 04a2abf |
| 3 | R1 | −0.0023 [−0.0088, +0.0023] | no PIL candidate qualifies | 315ca5b |
| 4 | R2 | −0.0031 [−0.0080, +0.0013] | as #3 | 315ca5b |
| 5 | R3 | −0.0034 [−0.0132, +0.0041] | as #3 | 315ca5b |
| 6 | R4a ("spikiness") | +0.0124 [−0.0048, +0.0294] | not eligible under the Phase X rule; chosen after dev results (disclosed) → held-out A8/A9 | 315ca5b |
| 7 | R4b | −0.0051 [−0.0177, +0.0027] | reported only | 315ca5b |
| 8 | R4c | +0.0037 [−0.0058, +0.0132] | → held-out A11 (secondary) | 315ca5b |
| 9 | R4a_nf (flare frames excluded) | +0.0133 [−0.0112, +0.0374] | flare check | 382df4e |
| 10 | n_B (B-class count) | −0.0049 [−0.0132, +0.0019] | exploratory | 33e5f5f |
| 11 | n_B + R4a (combination) | +0.0092 [−0.0103, +0.0281] | → stopped (D-iii) | 33e5f5f |
| 12 | S1 (size) | −0.0042 [−0.0129, +0.0016] | exploratory | 4218c32 |
| 13 | S2 (size) | −0.0057 [−0.0123, +0.0001] | exploratory | 4218c32 |
| 14 | B1 (PIL brightness) | +0.0050 [−0.0050, +0.0149] | exploratory | e09e9ab |
| 15 | B2 | −0.0018 [−0.0089, +0.0056] | exploratory | e09e9ab |
| 16 | B1_nf | +0.0047 [−0.0057, +0.0150] | exploratory | e09e9ab |
| 17 | B2_nf | −0.0023 [−0.0087, +0.0048] | exploratory | e09e9ab |
| 18 | K3 temporal contrast (PRIMARY A + R4a vs + K3) | +0.0013 [−0.0069, +0.0095] | "NOT ELIGIBLE" | da4b582 |
| 19 | log R4a (paired vs raw R4a) | +0.0057 [−0.0087, +0.0204] | "raw vs log makes no clear difference" | 6efb692 |
| 20 | M1 SG-PIL mask | +0.0013 [−0.0066, +0.0095] (98.33% CI [−0.0082, +0.0112]) | "NOT ELIGIBLE" | 490e8bd |
| 21 | M2 brightest core | +0.0026 [−0.0049, +0.0099] (98.33% [−0.0067, +0.0115]) | "NOT ELIGIBLE" | 490e8bd |
| 22 | M3 SPOT | −0.0041 [−0.0103, +0.0018] (98.33% [−0.0118, +0.0030]) | "NOT ELIGIBLE" | 490e8bd |
| 23 | recharge vs clustering (#22) | +0.0017 [−0.0144, +0.0184] | "NO DETECTABLE EFFECT" | bd89593 |
| 24 | parasitic-polarity dots (#23) | −0.0056 [−0.0218, +0.0083] | "NOT ELIGIBLE"; follow-up not run | d89a1a0 |
| 25 | new vs repeat brightenings (#24) | +0.0075 [−0.0062, +0.0208] | "NOT ELIGIBLE"; follow-up not run | 0303d05 |
| 26 | F2 literature ratios under magnetic matching (includes CV_box twins, dev 1.97 [1.47, 3.17]) | ratios, not Δ | CV_box → A12 / A1 | 0fa1f26 |
| 27 | Prospective dev exploration: BF(a), CV6, CV_box | twins ratios and Δ in 208202b | exploratory; the prospective test is pending (E) | 208202b |

The reference paper's Appendix A groups these candidates loosely into rows 3–19 and 23–27. Its total of 31 ideas also counts the pre-registered tests in A, so it is an approximate count, not a one-to-one index of this table.

**D-ii. Pre-registered tests that did not pass:** A5, A6, A7, A8/A9, A10, A12 (see A).

**D-iii. Stopped or failed designs**

| item | finding | commit |
|---|---|---|
| V2 image-only spike removal | 0 pairs in all sets (B2) | 1465063 |
| BF (bursty fraction) | median BF_noise / BF = 1.1464 → "BF IS NOISE-DOMINATED"; redefined as BF(a), 5 × 5 blocks | a215701, eb3e7d5 |
| n_B + R4a re-analysis | "n_B NOT COMPARABLE ACROSS YEARS — TEST NOT RUN": 2023 B-class region attribution −21.76 pp vs dev mean (−20.13 pp vs pooled); permanent stop | 68e57b1, f70f1e7 → b7e7749 |
| CV6 dev exclusion | label-dependent: 12/96 true vs 7/445 false undefined; the prospective report must give CV6 undefined counts by true/false | 313c1c0 |
| D7 / D8 / R1–R4 B&C reproduction runs | no run reached the pre-registered TSS target (see F2) | 57c925d |

## E. PENDING (pre-registered, not yet run)

| item | design | earliest run | commits |
|---|---|---|---|
| Prospective test | PRIMARY CV_box twins; secondary CV6, BF(a), COMBO-T; data from 2026-08-17 | with "run the prospective test once", not before 2026-11-10 | 2f62f88, bb8a137, eb3e7d5, d2ed360, 9a88d70, e17a8a3 |
| Look 1 (C+ rule) | descriptive only, t in [2026-08-17, E], E = min(2026-10-31, coverage end) | not before 2026-11-10 | 8aa1797, 784b1a8 |
| Look 2 (C+ rule) | **confirmatory**; t in [2026-08-17, E2], E2 = min(2027-02-28 23:00 TAI, coverage); size rule < 150 evaluable → "TOO SMALL — DESCRIPTIVE ONLY" | not before 2027-03-15 | 8aa1797, 784b1a8 |

## F. DATA-QUALITY FINDINGS

| # | finding | numbers | commits |
|---|---|---|---|
| F1 | HEK AR = 0 phantom false alarms (defect reported first by Hu et al., arXiv:2512.13417; the effect on this verification was measured here) | region FAR 0.724 (HEK) vs 0.543 (SWPC), +0.181 [0.112, 0.259]; hour FAR 0.801 vs 0.702, +0.099 [0.057, 0.150]; 34/386 alarm episodes 2021–24 in 20 regions (30 HEK region = 0, 4 missing from HEK); none in 2010–19 | 7eb9c55, 50c5895 → 2ba51d3, fb1fdd4 |
| F2 | Bobra & Couvidat: partial reproduction | D7 closest reproduction TSS 0.527 ± 0.050 (1,000 splits) vs published 0.610 ± 0.048; D7b our baseline 0.586 [0.467, 0.680]; D7t 0.707 ± 0.040; D8 (Table 3 setting) in 24e318c; gap 0.045–0.103 across runs; no R1–R4 run reached the target | d2f3b57, 2312d82, 24e318c, 57c925d |
| F3 | B-flare disappearance near solar maximum | 2023 B-class region attribution 57%; −21.76 pp vs dev mean | b7e7749 |
| F4 | Cutoff drift across the cycle | CV_box yearly medians 0.23 (2011), 0.11 (2023), 0.08 (2025); Model A frozen τ kept all test episodes (306/306 at τ 0.0680, A11 table) | 5ecb255, 7438177 |
| F5 | SWPC completeness at the K2 scale | 134/137 GOES M1+ found; 2018–2020 audit 0 bugs; G15/G16 cross-calibration residual ≈ 8% not corrected | 69f706a, 3afd6fe, 73171b0 |

---

**Reproducibility notes** (added with this summary):
- `docs/verification/verify_independent.py` re-derives A1–A7 and A3/A4 from the raw SWPC reports, the saved per-frame light curves, the stored cohorts and the frozen models. It does not re-process raw AIA FITS images. Paths are repo-relative (f060c86).
- Two historical scripts still point at a Claude scratch directory from the original machine that no longer exists. They are left unchanged, because they are the records of what was run:
  - `stage3_cohort.py:47` is used only for a printed diagnostic after all outputs are written. It needs `stage3_v1/cohort_dev.csv`, which is not in the repo.
  - `diag_ablation.py:18` is used only for ablation row D2 (old-scale K labels). It needs `labelled_K.csv` (sha256 85b88518…), which is not in the repo.
  - Neither affects any result in sections A or B.
