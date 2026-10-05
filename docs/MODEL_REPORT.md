# Model report: "Same Magnetic Field, Different Fate"

> **Revision 28 Sep 2026 (after an external review). These rules override anything below.**
> 1. **Dependence:** the 50 pairs reuse 18 flaring and 41 non-flaring regions, and 47 pairs are linked into one group. Quote the pre-registered CI (1.30–9.49) *and* the post-hoc both-sides interval (0.86–12.2). Say "the pass rule was met; the statistical margin is sensitive to region reuse". Never call it "replicated" or "confirmed" in prose. Source: `docs/verification/dependence_sensitivity.log`, RESULTS_SUMMARY C1.
> 2. **Wording:**
>    - "Same magnetic field" means a matched gate score, not identical fields. The missing information is "not captured by the magnetic score", not "not magnetic".
>    - Calm cases are "1 in 4 **true alarms**", not "real flares".
>    - "34 **true alarm episodes**" is a measured effect of a defect that **Hu et al. reported first**.
>    - 2025–26 is **archival** (held-out, run once), not prospective; only the C+ test is prospective.
>    - WARNING/WATCH is **descriptive**.
> 3. **Novelty:** Leka et al. already compared flare-imminent with flare-quiet epochs. Kniezewski et al. used other AIA channels, so their effect size is not comparable. What is new is the *conditional* test among score-matched alarms, on later years, with a failed veto test.
> 4. **Reproducibility:** do not write "every number was recomputed independently". The independent script uses the saved light curves and reports, not the raw FITS images.
>
> The revised reference paper (`Claude outputs/…REFERENCE_PAPER.pdf`) and `docs/RESULTS_SUMMARY.md` already follow these rules.
### Content-complete, structured reference for the IRIS research paper (rewrite every sentence yourselves)

Prepared 2026-09-28. It replaces `Claude outputs/Same_Magnetic_Field_Different_Fate_full_paper.pdf` as the reference.

**How to use this file**
- The report is in **note form on purpose**. Each bullet is one idea you turn into your own sentence. Tables and numbers can be copied as they are; they are data, not prose. Your own rule (decisions.md 2026-09-28) and IRIS ("your submission must be your own original work") require the text to be yours.
- Every number was checked against the repository on 2026-09-28. The headline numbers were also re-derived by an independent script from the raw SWPC reports, saved light curves and frozen models, not from raw FITS images (Appendix B). `[src: …]` shows where a number comes from, so you can answer "where does that come from?" in the interview. Delete the tags in your version.
- ⚠ marks a trap: wording that over-claims, or a correction to the old draft.
- Section order follows IRIS (title page → contents → introduction → methodology → discussion → conclusion → acknowledgements → references), plus a Results section as in the IRIS sample paper.

---

## Part A: Everything to include, and where (master map)

### A1. Figures

| # | file | goes in | what it shows | fix before use |
|---|---|---|---|---|
| Fig 1 | `Claude outputs/fig1_overview.png` | end of §3 (Methods overview); reuse in the video | A study design · B twins ratio per set · C WARNING vs WATCH flare rate | change "~40" → **40**. Panel C omits NO ALERT, so either say so in the caption or use Fig 5 in the paper. AI-made figure: disclose |
| Fig 2 | `figures/magnetic_vs_aia94_twin_pair.png` | §4.3 | a typical 2025–26 twin pair: same gate score −0.9812; CV 0.065 vs 0.023; M3.4 15 h later | none (verified: posthoc 1i) |
| Fig 3 | `figures/sensitivity_combined.png` | §4.4 (optional; Table 5 carries the numbers) | robustness of the ratio across frame sets and twin types | the V2 rows are all "undefined": crop them, or say in the caption "V2 = failed design, no pairs" |
| Fig 4 | `figures/model_comparison_tradeoff.png` | §4.6 | every rule: real flares kept vs false alarms cut, dev and 2021–26 | right-panel title "5 later sets combined" → **"4 later sets combined"** (160 true / 831 false = test + unseen + 2022 + 2025–26) |
| Fig 5 | `figures/alert_tiers.png` | §4.7 | NO ALERT / WATCH / WARNING flare rates with CIs, 3 sets | title already says "descriptive, post-hoc". Keep that |
| video | `figures/twin_pair_24h.gif` (or `twin_pair_24h_clean.gif`) | video 30–55 s | the Fig 2 pair animated over 24 h | none |

Not for the paper: `tier1_methods_twins.png`, `aia94_known_measures_5pairs.png`, `brightening_events_5pairs.png`, `r4a_illustration_*`, the `background_*` plots, and every `_chk_*`/`_gif_*` scratch file. They show 5-pair illustrations or dead ends, not results.

### A2. Tables (all data below are verified)

| # | content | section |
|---|---|---|
| Table 1 | HEK vs SWPC labels: FAR and phantom alarms | §2.2 |
| Table 2 | data sets: years, rule, episodes, true/false, HARPs, role | §2.4 |
| Table 3 | gate vs persistence (hour and region TSS, FAR) | §4.1 |
| Table 4 | H1 twins ratio in every set | §4.3 |
| Table 5 | robustness of the 2025–26 ratio | §4.4 |
| Table 6 | H2 Step B (Model A vs C) | §4.5 |
| Table 7 | H3 filter tests, primary and secondary | §4.6 |
| Table 8 | alert tiers (3 tiers, 3 sets) | §4.7 |
| Table 9 | C+ rule vs Model C (exploratory) | §4.8 |
| Table 10 | box vs PIL vs random-control restlessness (descriptive) | §5.1 |
| Table 11 | comparison with previous work | §5.3 |
| App. A | chronology of all 31 ideas | appendix |

### A3. Headline numbers (quote exactly these)

| claim | number | status word to use |
|---|---|---|
| gate, region TSS (test 2021/23/24) | 0.728 [0.630, 0.820], 450 HARPs | held-out |
| gate, hour TSS vs persistence | 0.547 [0.412, 0.660] vs 0.358 [0.244, 0.461] | held-out |
| true-alarm share of alarm episodes (test) | 45/313 = 14.4% | define "episode" |
| magnetic trends (original question) | Δ −0.0051 [−0.0201, 0.0094] | pre-registered, **not supported** |
| H1 twins 2025–26 | **3.26 [1.30, 9.49]**, 39/50 pairs | pre-registered; the pre-stated reading word was "REPLICATED", but in prose say **"pass rule met"** and add the region-reuse caveat (both sides resampled: 0.86–12.2, post-hoc) |
| H1 strict (history-matched + flare frames removed) | 2.73 [1.10, 6.20], 34/47 | post-hoc robustness |
| H2 flare recency, 2025–26 | Δ +0.0173 [0.0016, 0.0350] | pre-registered, passed **narrowly** |
| H3 filter on Model C, 2025–26 | true alarms kept −13.98 pts [−28.47, −4.42] | pre-registered, **failed** |
| tiers WARNING vs WATCH | 26% vs 8% · 32% vs 2% · 27% vs 5% | post-hoc, **descriptive** |
| HEK label defect | region FAR 0.724 vs 0.543; +0.181 [0.112, 0.259] | data-quality finding |

---

## Part B: The report, section by section

### Title page
- **Title:** "Same Magnetic Field, Different Fate"
- **Subtitle:** coronal restlessness and flare history separate true from false solar-flare alarms (or your own wording)
- **Authors:** **both team members**, as a team project. ⚠ The old draft listed one author and used "I".
- Category (Physics & Astronomy / Space science), month and year.
- ⚠ **No school name, city or state** (IRIS anonymity rule), and no school email.

### Table of contents
- Required by IRIS; missing from the old draft.

---

### Abstract (≤ 250 words; write it last)
Content points in order, one or two sentences each:
1. **Problem:** magnetic-field flare forecasts catch most big flares but raise many false alarms.
2. **What we built:** an SVM "gate" on 10 SHARP magnetic features trained on 2010–2019. Held-out region-level TSS **0.73**, yet only **14% of alarm episodes (45/313)** are followed by an M1+ flare within 24 h.
3. **Question:** among regions the gate already calls dangerous, what separates true from false alarms?
4. **Design:** every true alarm is paired with a false-alarm "magnetic twin" with a near-identical gate score. Tests use later years, region-level bootstrap intervals, and pre-registered pass/fail rules. The final test (2025–26) was run once.
5. **H1 result:** true alarms had a **3.3× higher median 94 Å restlessness** than their twins (95% CI 1.30–9.49; 39 of 50 pairs), and **2.7×** after also matching flare history and removing flare-time frames.
6. **H2 result:** hours since the last C-class flare added modest probabilistic skill (Δ log-loss +0.017, CI +0.002 to +0.035).
7. **H3 result:** as a hard filter, restlessness removed too many true alarms (−14 points), so it **grades** risk rather than deleting alarms. WARNING-tier alarms flared 26–32% of the time, WATCH-tier ones 2–8% (descriptive).
8. (Optional, one clause) The widely used HEK flare list inflates the false-alarm ratio through lost region numbers.
- ⚠ Do not say "confirmed", "proves" or "significant" anywhere in the abstract.

---

### 1. Introduction  (≈ 450–600 words in the paper)

**¶1: Why flares matter and how forecasts work**
- Large flares disrupt HF radio and GNSS within minutes, so space-weather centres issue daily probabilistic forecasts.
- Most methods use the photospheric magnetic field of active regions. SHARPs (Bobra et al. 2014) summarise each tracked region (HARP) with keywords such as total unsigned flux, current helicity and free-energy proxies.
- The SVM on SHARP features (Bobra & Couvidat 2015) is a standard benchmark.

**¶2: The false-alarm problem**
- The magnetic field shows *how much* free energy a region stores, not *when* it will be released, so false alarms are common.
- Bloomfield et al. 2012: the best TSS (≈ 0.52) came with precision ≈ 13%.
- Few methods beat climatology much, and rankings depend on definitions and metrics (Barnes et al. 2016; Leka et al. 2019).
- Camporeale & Berger 2025: operational M-class forecasts do not beat simple baselines (persistence TSS 0.46), and a high TSS can hide a high false-alarm ratio.
- Cutting false alarms after a magnetic model is hard. Deshmukh et al. 2022 removed ≈ 48% of false positives but lost ≈ 12% of true positives.
- Alatoom & Nikolaou 2026: the most common false positives are magnetically complex, historically productive regions. **So comparing flaring vs quiet regions is not enough; the fair comparison is dangerous vs dangerous.**

**¶3: Why coronal EUV, and the gap**
- AIA 94 Å in active-region cores is dominated by Fe XVIII from ~6–7 MK plasma, with a cooler ~1 MK contribution (Warren, Winebarger & Brooks 2012).
- 94 Å is ranked the most informative AIA channel (Leka et al. AARP II; Francisco et al. 2024), and short-timescale variability is one of the strongest discriminators (AARP II).
- Kniezewski et al. 2024: EUV variability rises in the hours before flares.
- **Gap:** most precursor studies compare flaring with quiet regions or epochs, so flaring regions may simply be "inherently variable". Nobody has tested variability *among regions a magnetic model already rates as equally dangerous*, on future years, with pre-registration.

**¶4: Project history and research question**
- The project first tested whether 24-h trends in magnetic parameters separate true from false alarms. The pre-registered answer was no (§4.2). The work then turned to coronal data.
- **Research question:** among active regions that a magnetic model flags as high-risk for an M1+ flare within 24 h, do true alarms differ from false alarms in recent flare history and in coronal 94 Å variability, beyond what the magnetic field shows?
- **Hypotheses, each with a pre-stated pass rule:**
  - **H1:** true alarms are more restless in 94 Å than false alarms with the same gate score. Pass = twins ratio > 1 **and** CI lower bound > 1.
  - **H2:** time since the region's last C-class flare improves probabilistic forecasts beyond flare counts. Pass = Δ log-loss > 0 **and** CI excludes 0.
  - **H3:** restlessness works as a filter that removes false alarms while losing ≤ 10 points of true alarms. The pre-stated three-level reading:
    - "confirmed safe filter" = D_false CI lower > 0 **and** D_true CI lower ≥ −10;
    - "meets operating criterion" = D_false CI lower > 0 **and** D_true point ≥ −10;
    - "removes false alarms but loses too many true alarms" = D_true point < −10.
  - ⚠ The old draft stated only the first level. State all three.

---

### 2. Data  (≈ 400 words)

**2.1 Magnetic parameters**
- `hmi.sharp_cea_720s` keywords, hourly, May 2010 → Aug 2026. For 2010–2024: 254,899 labelled rows after removing 393 duplicates. [src: VERIFIED_FACTS #8, #12]
- QUALITY = 0 (stricter than Bobra & Couvidat's ≤ 65536; this removes 99.5% of 06:00/18:00 TAI records) and |longitude| ≤ 45° (limits projection effects).
- Primary analysis uses single-region rows (one NOAA region per HARP at that hour). The 2025–26 test allows ≤ 2 regions (recorded fallback rule).

**2.2 Flare labels and a catalogue defect (a finding in itself)**
- Labels come from the original NOAA SWPC daily event reports, which keep the NOAA region number of each flare.
- Region numbers below 10000 get +10000. Duplicates are removed on (start time, class).
- GOES-13/14/15 fluxes are ÷ 0.7 to put them on the true-flux scale (NOAA/NCEI), while GOES-16+ fluxes are used as reported. This changed 4,170 of 27,219 events.
- Checks:
  - SWPC agrees with HEK on class in 1,281/1,281 matched events (March 2011–2019) and on region in 1,094/1,095.
  - SWPC contains 134/137 GOES M1+ flares in the sampled months.
  - None of the 835 empty-report days reaches M1.
  - The 2018–2020 audit found 0 bugs.
- Years: 2020 excluded (0% of M1+ flares with a usable region). 2022 is kept out of the primary test (89.7% usable, below the fixed 90% rule) and used as a sensitivity set.
- **HEK defect:** the widely used HEK copy of the GOES list loses region numbers (AR = 0), mostly in 2021–2023. For M1+ flares with unknown region: 2021 14/31, 2022 173/195, 2023 284/334, 2024 72/949. Hu et al. (arXiv:2512.13417) documented the defect; **we measured its effect on alarm verification.**

**Table 1. Same frozen gate alarms scored with HEK vs SWPC (K2) labels** [src: VERIFIED_FACTS #122–127]

| measure | HEK | SWPC (K2) | difference [95% CI] |
|---|---|---|---|
| region FAR, test years 2021/23/24 (105 alarmed regions of 450) | 0.724 | 0.543 | **+0.181 [0.112, 0.259]** |
| hour FAR, test years | 0.801 | 0.702 | +0.099 [0.057, 0.150] |
| alarm episodes 2021–24 labelled false by HEK but true in SWPC | 34 of 386 (8.8%), in 20 HARPs | — | 30 had HEK AR = 0; 4 were missing from HEK |

- ⚠ Say "alarm episodes", not "alarms" or "flares". In 2010–2019 there were 0 such phantom episodes, so the defect is recent.

**2.3 Coronal EUV data**
- AIA 94 Å JSOC cutouts over each HARP box at 12-min cadence for (t − 24 h, t].
- Frames with bad QUALITY or abnormal exposure were removed. Saturated pixels (> 12,000 DN) were masked. A window was used only if ≥ 80% of its 120 frames were valid.
- The choice of 12-min cadence was checked before any labels were used: restlessness at 12 min vs 2 min, Spearman ρ = 0.95 [0.62, 1.00], n = 8. The JSOC-vs-synoptic source rule failed, so JSOC cutouts were used. [src: VERIFIED_FACTS #116–117]

**2.4 Data sets**

**Table 2. Alarm-episode sets. Sets were never pooled for testing.** [src: decisions.md; posthoc checks; independent verification]

| set | years / rule | episodes (true / false) | with EUV (true / false) | HARPs (EUV set) | role |
|---|---|---|---|---|---|
| Development | 2010–2019, single-region | 547 (98 / 449) | 541 (96 / 445) | 179 | training and exploration only |
| Test | 2021, 2023, 2024, single-region | 313 (45 / 268) | 306 (44 / 262) | 98 | first held-out test |
| Unseen follow-up | 2021/23/24 two-region episodes not in Test | 158 included | 155 (32 / 123) | 40 | pre-registered filter test |
| 2022 | 2022 (fails the 90% label rule) | 152 (28 / 124) | 152 (28 / 124) | 44 | sensitivity only |
| Confirmation | Jan 2025 – Aug 2026, ≤ 2 regions | 387 (56 / 331) | 378 (56 / 322) | 101 | final pre-registered test, run once |

- Caption notes: delayed alarms (a flare 24–48 h later) count as false. HARPs never cross the dev/test split (split by HARP, seed 20260921).

---

### 3. Methods  (≈ 600 words; put Fig 1 at the start or end)

**3.1 The magnetic gate**
- RBF-kernel SVM with C = 4, γ = 0.075 and class weight 2:1, following Bobra & Couvidat 2015.
- 10 features: TOTUSJH, TOTPOT, TOTUSJZ, ABSNJZH, SAVNCPP, USFLUX, AREA_ACR, MEANPOT, R_VALUE, SHRGT45. B&C's other 3 are not SHARP keywords.
- Median/SD scaling inside each training fold. Training rows thinned to TAI hours {4, 10, 16, 22}.
- Five HARP-grouped folds on dev. The threshold **−0.9925** maximises TSS on the out-of-fold scores and was then frozen, along with all model files (SHA-256).
- Test score = mean of the 5 fold models' decision values.

**3.2 Alarm episodes and labels**
- An alarm episode is a run of consecutive alarm hours for one HARP, bridging gaps of ≤ 3 h (T1). It is evaluated at t, the first alarm hour with ≥ 18 of 24 prior hours available (T3/T4).
- Every eligible episode is used, weighted 1/n within its HARP so long-lived regions do not dominate (T2).
- **True alarm** = an M1+ flare from the same NOAA region(s) in (t, t + 24 h]. Otherwise false. A flare arriving later (delayed) counts as false, which makes the definition strict.

**3.3 Restlessness (CV_box)**
- b(tᵢ) = mean 94 Å brightness in the HARP box for each valid 12-min frame in (t − 24 h, t].
- Remove a straight-line trend, then take the coefficient of variation:
  **CV_box = SD(b − linear trend) / mean(b)** (sample SD, ddof = 1).
- High = hot plasma that brightens and fades repeatedly. Low = steady emission (Fig 2, right panels).
- Why the whole box: the first EUV idea, restlessness at the polarity inversion line, failed its pre-registered test (§4.9). On dev the box version separated twins best (Table 10).

**3.4 Magnetic twins**
- Each true episode is matched 1:1, without reuse, to the false episode from a **different HARP** with the nearest gate score.
- Caliper 0.0747 = 0.2 × SD of dev gate scores, frozen. Matching order is fixed by a seeded permutation (20260921).
- Maximum score difference within pairs: 0.060 (2025–26). ⚠ Delete the old draft's claim that pairs "differ in the fourth decimal". It was never measured.
- Statistic = median CV_box of true members ÷ median of false members. 95% CI from resampling pairs clustered by true HARP (2,000). Reported with the count of pairs where true > false.
- Strict version (T_b): twins must also share a flare-history group (JUST-FLARED: ≥ 1 M/X in 48 h; QUIET-NOW: no C/M/X in 48 h; C-only: otherwise). Frames during recorded flares are removed (V1).

**3.5 Probabilistic models**
- Logistic regression (L2, C = 1) with training-fold standardisation. Same 5 HARP-grouped dev folds and 1/n weights.
- **Model A** = gate score + number of C, M and X flares from the region in the previous 48 h.
- **Model C** = A + log(1 + R), where R = hours since the start of the last C1+ flare from the region (capped at 48).
- Model C_CV = C + log10 CV_box (A_CV likewise).
- Prediction on new years = mean of the 5 fold models. Operating thresholds were frozen on dev.

**3.6 Evaluation and pre-registration**
- **Chronological, not random:** development used 2010–2019 only. A random row split inflated dev TSS by ≈ 0.11 (0.790 vs 0.679) in our own ablation, consistent with Chen et al. 2024 and Wang et al. 2020.
- **Uncertainty:** episodes from one region are correlated, so every CI bootstraps whole HARPs (10,000 for log-loss, 2,000 otherwise).
- **Metrics:**
  - Δ log-loss = LL(base) − LL(new); positive favours the new model.
  - Filters: D_false = change in % of false alarms removed; D_true = change in % of true alarms kept (region-weighted).
- **Pre-registration:** hypotheses, data, statistic and a mechanical reading rule were committed to an append-only, version-controlled diary (git) **before** each test was computed. Frozen files were hash-checked before each run.
- ⚠ **Correct timeline for 2025–26** (the old draft was wrong): the 2025–26 EUV data were downloaded and restlessness was computed **label-blind first**. The tests were registered **after** that and **before** any 2025–26 label was joined to EUV values. [src: decisions.md entries at lines ~4129–4228]
- Fig 1 caption notes: A design; B ratio per set with 95% CIs; C tiers (descriptive).

---

### 4. Results  (≈ 900–1,100 words; one subsection per question)

**4.1 The magnetic gate works, but most alarms are false**

**Table 3. Frozen gate vs persistence, test 2021/23/24, single-region** (53,356 hours; 450 HARPs) [src: data/stage5/persistence_vs_gate.csv; recomputed]

| predictor | level | TSS [95% CI] | precision | FAR |
|---|---|---|---|---|
| gate | hour | **0.547 [0.412, 0.660]** | 0.298 | 0.702 |
| persistence (M1+ in previous 24 h) | hour | 0.358 [0.244, 0.461] | 0.394 | 0.606 |
| gate | region | **0.728 [0.630, 0.820]** | 0.457 | 0.543 |

- The gate beats persistence at the hour level. Persistence looks better at the region level only by construction (a region that flared has later hours with P = 1), so don't show that row or explain it.
- Base rate: 3.70% of test hours are followed by an M1+.
- **Reproduction:** B&C's protocol with random splits gave TSS 0.527 ± 0.050 (C1/C2 = 2) and 0.716 ± 0.040 (C1/C2 = 15) vs published 0.610 and 0.761. That is **0.083 and 0.045 lower**; across all reproduction runs, 0.045–0.103 lower. Causes are not proven (catalogue and SHARP revisions are possible). ⚠ "0.05–0.08 lower" in the old draft is wrong.
- **The problem the paper studies:** only 45 of 313 alarm episodes (14.4%) were true. ⚠ Give the unit: region-level precision is 45.7%, hour-level 29.8%.

**4.2 Original question: magnetic trends add nothing detectable (pre-registered, final)**
- Δ log-loss(A − B) = **−0.0051 [−0.0201, 0.0094]**, 313 episodes, 98 HARPs, 10,000 resamples. AUC 0.811 (A) vs 0.797 (B).
- All 12 robustness rows lie between −0.0067 and +0.0054, and every CI includes 0. Matched pairs (41) also found no difference.
- Keep it short, but keep it: an honest null that motivated the pivot.

**4.3 H1: true alarms are more restless than their magnetic twins**

**Table 4. Restlessness ratio, median true ÷ median false twin** [src: step 6, ec00afb, 5abc40a, ae1b174; independently re-matched: identical pairs]

| set | pairs (true HARPs) | ratio [95% CI] | true > false | status |
|---|---|---|---|---|
| Development 2010–19 | 81 (34) | 1.97 [1.47, 3.17] | 57/81 | exploratory (idea found here) |
| Test 2021/23/24 | 40 (25) | 1.31 [0.94, 2.22] | 25/40 | pre-registered: "direction consistent, not confirmed" |
| Unseen 2021/23/24 | 23 | 1.63 [0.79, 3.84] | 13/23 | secondary |
| 2022 | 25 | 3.24 [1.26, 4.55] | 18/25 | sensitivity |
| **Confirmation 2025–26** | **50 (18)** | **3.26 [1.30, 9.49]** | **39/50** | **pre-registered, run once: "REPLICATED"** |
| 2025–26 single-region only | 16 | 3.44 [1.36, 7.30] | 12/16 | descriptive |

- Points to make:
  - The direction is above 1 in every set. The CI excludes 1 in dev, 2022 and 2025–26, and includes 1 in both 2021/23/24 sets. **Say this plainly.**
  - The first held-out test was ambiguous. The one-shot pre-registered test on new years passed.
  - All-episodes ratio (no matching) in 2025–26: 3.30 [1.37, 6.46]. Matching barely changes it, so the magnetic score does not explain the difference.
  - Fig 2: a typical pair (its ratio 2.90 is closest to the median pair ratio 2.86). Same gate score −0.9812. The true region (M3.4 flare 15 h later) had CV 0.065; its twin had 0.023.
- ⚠ Pairs are not independent: 50 pairs come from 18 true regions. **Quote the region-bootstrap CI, not the sign-test p** (p ≈ 1e-4 treats pairs as independent).
- ⚠ Matching order: the pre-registered order gave 3.26, the lowest of 300 random orders (median 3.55). The CI lower bound stays above 1 in 81% of orders. This is good to know for the interview (conservative, but the significance is fragile).

**4.4 Is restlessness just recent flaring?** (post-hoc; defined in the diary before computing)

**Table 5. Robustness of the 2025–26 result** [src: 92027fa sensitivity; descriptive_aia94]

| check | pairs | ratio [95% CI] | true > false |
|---|---|---|---|
| magnetic twins (pre-registered) | 50 | 3.26 [1.30, 9.49] | 39/50 |
| + matched on flare-history group | 47 | 2.82 [1.02, 6.82] | 35/47 |
| flare-time frames removed | 49 | 2.92 [1.18, 8.25] | 37/49 |
| **both (strict)** | **47** | **2.73 [1.10, 6.20]** | **34/47** |
| saturated frames removed | 50 | 2.69 [1.17, 7.63] | — |
| exposure-change frames removed | 50 | 3.26 (unchanged) | — |
| photon + read noise corrected | 50 | 3.26 (noise ≈ 1.1% of CV_box, median) | — |

- The variability is present between recorded flares, and noise is ~1% of the signal (Boerner et al. 2012 constants via aiapy).
- ⚠ Be honest about the other sets under the strict version: unseen 1.34 [0.67, 2.15] and 2022 2.78 [0.89, 5.44] both include 1.
- ⚠ Restlessness correlates with recent C-flare counts (Spearman ρ 0.57 pooled). Within the same C-count bin, true alarms are still more restless: 0 C flares, 0.111 vs 0.056; 1 flare, 0.237 vs 0.110. [src: posthoc 1d; descriptive]
- The image-only spike removal (V2) collapsed on smooth light curves and removed about half of all frames, leaving 0 usable pairs. Report it as a failed design (one sentence).

**4.5 H2: flare recency adds modest skill**

**Table 6. Step B, Model A vs Model C (pre-registered TEST 2)** [src: ae1b174; recomputed independently]

| set | episodes (true / false) | LL(A) | LL(C) | Δ [95% CI] | AUC A → C |
|---|---|---|---|---|---|
| dev 2010–19 (out-of-fold, exploratory) | 547 (98 / 449) | 0.3336 | 0.3356 | −0.0020 [−0.0129, 0.0084] | 0.743 → 0.765 |
| **2025–26, ≤ 2 regions (primary)** | 387 (56 / 331) | 0.3930 | 0.3757 | **+0.0173 [0.0016, 0.0350]** | 0.749 → 0.753 |
| 2025–26 single-region (descriptive) | 165 (19 / 146) | 0.3659 | 0.3558 | +0.0101 [−0.0091, 0.0332] | 0.756 → 0.725 |

- The coefficient on log(1 + R) was negative in 5/5 dev folds: −0.18 to −0.36 standardised, mean −0.30, odds ratio 0.74 per SD. A more recent flare means a higher chance of another, consistent with flare clustering (Jonas et al. 2018). ⚠ The old draft's "−0.19 to −0.33" belongs to a different set of models.
- ⚠ "Passed its pre-registered rule, narrowly" is the honest wording. The lower bound is barely above 0, the dev estimate was slightly negative, and the single-region CI includes 0.

**4.6 H3: restlessness fails as a hard filter**

**Table 7. Filter tests (frozen dev thresholds; D in region-weighted percentage points; paired HARP bootstrap 2,000)** [src: 5abc40a, 4b65f23]

| set | comparison | role | D_false (more false removed) | D_true (change in true kept) | reading (same three-level rule) |
|---|---|---|---|---|---|
| Unseen 2021/23/24 | A vs A_CV | **pre-registered primary** | +60.20 [+46.92, +72.77] | **−16.17 [−37.58, −1.98]** | **loses too many true alarms** |
| Unseen 2021/23/24 | C vs C_CV | secondary | +35.32 [+17.11, +51.85] | −2.60 [−13.33, +3.49] | meets operating criterion (not "safe") |
| 2022 | A vs A_CV | sensitivity | +60.68 [+49.02, +72.57] | −14.33 [−32.52, −3.42] | loses too many |
| 2022 | C vs C_CV | sensitivity | +30.92 [+15.36, +46.18] | −8.68 [−27.03, +1.89] | meets operating criterion (not "safe") |
| **2025–26 re-test** | **C vs C_CV** | **pre-registered re-test** | +24.05 [+14.63, +33.45] | **−13.98 [−28.47, −4.42]** | **loses too many true alarms** |
| 2025–26 re-test | A vs A_CV | secondary | +63.12 [+54.38, +71.83] | −21.37 [−40.33, −7.32] | loses too many |

- Both pre-registered filter tests failed: the filter removes many false alarms but loses more than 10 points of true alarms.
- No comparison anywhere reached "confirmed safe filter".
- ⚠ Mention the two secondary/sensitivity C rows that met the operating criterion by point estimate. The result is mixed, not uniformly negative, and hiding it would be caught.
- The 2025–26 re-test was a pre-registered re-test on a set already used for H1/H2, not an untouched test. Say so.
- **Why it fails:**
  1. **Calm flarers.** 27%, 19% and 25% of true alarms (2025–26, unseen, 2022) are calm. They flare later in the window (median ≈ 11–17 h vs 7–9 h for restless ones), and in 2025–26 their median CV (0.069) sits at the false-alarm median (0.072).
  2. **Thresholds do not transfer across the solar cycle.** Model A's dev cutoff kept 100% of episodes in every later set. CV_box medians also drift by year, e.g. 2011 0.23, 2023 0.11, 2025 0.08. [src: euv_descriptive_after]
  3. **Small numbers:** ~30–56 true alarms per set.
- **Probabilistic view:** adding CV_box to Model C raised AUC in all three sets (0.775 → 0.808; 0.748 → 0.822; 0.769 → 0.798), but Δ log-loss never had a CI excluding 0 (2025–26: +0.0102 [−0.0170, +0.0371]). ⚠ **Keep "a difference between groups" (H1) separate from "added forecast skill" (not shown).**
- ⚠ Delete the old draft's "standard error 0.0165 … 7% power". It exists nowhere in the repository.
- Fig 4 = the whole trade-off picture (fix the right-panel title first).

**4.7 Grading instead of deleting** (post-hoc, descriptive)

**Table 8. Weighted share of alarms followed by an M1+ within 24 h, by tier** (Model C / C_CV at frozen dev thresholds) [src: descriptive_aia94]

| tier | 2025–26 | unseen 2021/23/24 | 2022 |
|---|---|---|---|
| **WARNING**: C alarm and restless | **26%** [15, 38] (n 154) | **32%** [18, 46] (n 82) | **27%** [12, 44] (n 76) |
| **WATCH**: C alarm but calm | **8%** [2, 16] (n 135) | **2%** [0, 7] (n 47) | **5%** [1, 11] (n 56) |
| NO ALERT: no C alarm | 4% [0, 12] (n 89) | 12% [0, 31] (n 26) | 4% [0, 12] (n 20) |

- No alarm is deleted, yet a WARNING is 3–15× more likely to be followed by a flare than a WATCH. Rate ratios: 3.4 [1.4, 11.4], 15.3 [3.0, 23.2], 5.9 [1.7, 33.1].
- ⚠ The tiers were defined after the filter results, so say "descriptive". Include the NO ALERT row (the old draft left it out; the unseen set's 12% is higher than its WATCH).
- Fig 5.

**4.8 Exploratory: protect alarms with a recent C-class flare (C+ rule)**
- Where it came from: 24 of the 44 true alarms the filter rejected had ≥ 1 C-class flare in the previous 24 h.
- Rule: keep an alarm if Model C_CV keeps it **or** the region had any C1.0+ flare in (t − 24 h, t).

**Table 9. C+ rule vs Model C (unweighted counts, frozen thresholds)** [src: posthoc Part 0, 1e]

| set | C+ true kept | C+ false removed | Model C true kept | Model C false removed |
|---|---|---|---|---|
| dev 2010–19 | 91/96 | 179/445 | 88/96 | 154/445 |
| test 2021/23/24 | 41/44 | 94/262 | 42/44 | 72/262 |
| unseen 2021/23/24 | 29/32 | 36/123 | 28/32 | 22/123 |
| 2022 | 24/28 | 27/124 | 26/28 | 18/124 |
| 2025–26 | 52/56 | 125/322 | 54/56 | 87/322 |
| **2021–26 total** | **146/160** | **282/831** | **150/160** | **199/831** |

- More false alarms were removed in every period, but the weighted difference had a CI excluding 0 only in 2025–26 (+7.9 pts [+0.7, +15.5]), and C+ kept slightly fewer true alarms.
- ⚠ Designed after seeing these data, so **exploratory**. A prospective test is pre-registered (Look 1 ≥ 2026-11-10; Look 2 ≥ 2027-03-15). Say "will be tested", never "works".

**4.9 What did not work** (short, with pointers to Appendix A)
- Magnetic 24-h trends (§4.2).
- Restlessness at the polarity inversion line (ΔCV): dev Δ −0.0043 [−0.0092, 0.0003]; test +0.0025 [−0.0074, 0.0139].
- Spikiness R4a: dev best; test "direction consistent, not confirmed" (+0.0084 [−0.0227, 0.0418]); as a filter +16 pts false removed but −13 pts true kept.
- Sizes, PIL brightness, brightening fractions, three localised masks, parasitic "dots", recharge vs clustering, new vs repeat brightenings, temporal contrast: no dev interval excluded 0, or not eligible.
- B-flare count + spikiness: stopped by a pre-set data check (B-flare region attribution 57% in 2023, below the 20-point rule; near solar maximum the X-ray background hides small flares).
- **31 ideas in total** (Appendix A). ⚠ The old draft says "about 25" in one place and "about 30" in another. Use one count.

---

### 5. Discussion  (≈ 600–700 words)

**5.1 Physical interpretation (a hypothesis, not tested)**
- Among regions with the same magnetic danger, those heading for a major flare may be releasing energy in many small heating events that make hot plasma flicker.
- This is consistent with enhanced short-timescale 94 Å variability (Leka et al. AARP II) and with clustering of pre-flare transient brightenings (Dissauer et al. 2025).
- **The effect is region-wide, not concentrated at the inversion line:**

**Table 10. Restlessness measured in different areas: twins ratio (descriptive)** [src: F2 dev; F2 replication test]

| area | dev 2010–19 | test 2021/23/24 |
|---|---|---|
| whole HARP box (CV_box, the chosen measure) | 1.97 [1.47, 3.17] | 1.31 [0.94, 2.22] |
| polarity inversion line (CV_PIL) | 1.62 [0.97, 2.59] | 1.35 [0.89, 2.35] |
| random in-region control pixels (CV_ctrl) | 2.33 [1.47, 2.96] | 1.68 [1.03, 2.57] |

- ⚠ Be ready for "why CV_box and not CV_ctrl, which did better?" Honest answer: CV_box was fixed as the pre-registered measure before the test years, because it is the simplest (no magnetic mask, no random draws). CV_ctrl is shown only as descriptive support that the signal is region-wide.
- Say explicitly that the mechanism was not directly tested.

**5.2 Why the signal grades risk but cannot veto it**
- A population difference (ratio of medians) is not an individual rule. The distributions overlap, and calm flarers sit in the false-alarm range.
- Calm flarers flare later in the window, so their energy release may not have started at alarm time. The 24-h window ending at t cannot see precursors closer to the flare (median lead time of true test episodes ≈ 12 h; Kniezewski: variability peaks 1–2 h before onset).
- Operational use: raise or lower an alarm's priority (WARNING / WATCH) rather than delete it.

**5.3 Relation to previous work**

**Table 11. Comparison with closely related studies**

| study | design | relation to this work |
|---|---|---|
| Bobra & Couvidat 2015 | SVM on SHARP, random splits; TSS 0.61–0.76 | gate built on it; reproduced 0.045–0.103 lower |
| Deshmukh et al. 2022 | two-stage magnetic model; FP −48%, TP −12% | same trade-off; here chronological, with an EUV layer |
| Kniezewski et al. 2024 | EUV variability, flaring vs quiet ARs | similar size (2–3×); answers their "inherent variability" caveat with twins |
| Leka et al. (AARP II) | 8 AIA channels, short bursts | consistent: 94 Å variability; our 12-min whole-box measure is coarser |
| Francisco et al. 2024 | multimodal deep learning, chronological split | consistent with a small, real EUV contribution |
| Alatoom & Nikolaou 2026 | deep learning on SDOBenchmark | consistent: false positives are complex, productive regions |
| Camporeale & Berger 2025 | operational forecasts vs baselines | motivates reporting FAR and precision, not only TSS |
| Hu et al. 2026 | flare-catalogue defects | we quantify the defect's effect on FAR (+0.18) |

**5.4 Limitations** (the most important part for judges; don't cut)
1. **Many ideas were tried** (31), and CV_box was chosen after dev exploration and an ambiguous first replication. The one-shot pre-registered 2025–26 test reduces but does not remove this concern.
2. **Small, clustered samples:** 50 pairs from 18 true regions. The upper CI bound is 9.5, and the result depends somewhat on matching order (CI > 1 in 81% of orders).
3. **Heterogeneity:** the ratio ranges from 1.31 to 3.26 across sets. Both 2021/23/24 sets have CIs including 1, and so do the strict version on the unseen set and 2022.
4. **Multiple tests on 2025–26** (TEST 1 and TEST 2, plus the filter re-test) with no correction for multiplicity.
5. **Population change:** models were trained on single-region episodes, while 2025–26 allows up to two regions.
6. **Confounding with flare activity:** CV_box correlates with recent C-flare counts (ρ 0.57). The strict matching reduces but may not remove this.
7. **Coarse EUV measure:** 12-min cadence and a whole-box average can miss the short, small-scale variability the literature finds most informative.
8. **No proven operational gain:** no method beat Model C with a log-loss CI excluding 0, and thresholds and CV_box levels drift across the solar cycle.
9. **Label noise:** SWPC is missing ~2% of M1+ flares (134/137), and there is a ~8% GOES-15/16 calibration residual, not corrected.
10. **AI assistance** (see statement): the code was AI-written, so we verified it with an independent re-implementation (Appendix B).

---

### 6. Conclusion  (≈ 150–200 words)
- Among regions a magnetic model flags as dangerous, true and false alarms differ in ways the field cannot see.
- As a group, regions about to produce an M1+ flare have ~3× higher median 94 Å restlessness than magnetically identical regions that stay quiet. This held in a one-shot pre-registered test and after matching flare history and removing flare frames.
- How recently a region flared adds modest probabilistic skill.
- Restlessness is not a switch: about one true alarm in four was calm beforehand, so it should **grade** alarms, not delete them.
- Along the way: a widely used flare catalogue inflates false-alarm ratios by ~0.18.
- Next steps: the pre-registered prospective test of the C+ rule on 2026–27 data; higher-cadence and spatially resolved EUV; thresholds recalibrated through the cycle.

---

### 7. Acknowledgements and AI-use statement
**Acknowledgements** (IRIS allows a guide; no school name):
- NASA SDO (HMI, AIA science teams), JSOC Stanford, NOAA SWPC and NCEI for open data.
- Your project guide (by role, not institution).

**AI-use statement** (specific and prominent; judges will ask):
- **Claude Code (Anthropic)** wrote and ran nearly all analysis code, drafted the non-decision entries of the diary and the pre-registration wording (reviewed and adopted by us), and wrote the independent verification script.
- **Claude (chat)** proposed several candidate ideas and tests and made several figures (Fig 1; list them). It drafted an earlier version of this paper, which we did not submit; this text is our own.
- **Codex** ran one early exploratory analysis, not used in the results.
- **We (name both and split the roles honestly):**
  - chose the research question and the original EUV flicker idea;
  - proposed measurement ideas (e.g. new vs repeat brightenings);
  - made every go/no-go and pre-registration decision (recorded "decided by: user" in the diary);
  - handled all data access (JSOC account);
  - wrote this paper.
- Every numeric result was re-derived by an independent script (Appendix B).
- ⚠ **Do not** reuse the old line "This document is not a competition submission."

---

### 8. References  (verify each against the paper before submitting; ⚠ = check details)
- Alatoom & Nikolaou 2026, Space Weather, doi:10.1029/2026SW005010
- Barnes, G., et al. 2016, ApJ, 829, 89
- Bloomfield, D. S., et al. 2012, ApJL, 747, L41
- Bobra, M. G., & Couvidat, S. 2015, ApJ, 798, 135
- Bobra, M. G., et al. 2014, Sol. Phys., 289, 3549
- Boerner, P., et al. 2012, Sol. Phys., 275, 41
- Camporeale, E., & Berger, T. 2025, Space Weather, doi:10.1029/2025SW004546
- Chen et al. 2024, arXiv:2405.12331 (review)
- Deshmukh, V., et al. 2022, ApJS, doi:10.3847/1538-4365/ac5b0c
- Dissauer, K., Barnes, G., Leka, K. D., & Wagner, E. L. 2025, arXiv:2503.12338
- Francisco et al. 2024, arXiv:2410.16116
- Hu et al., "Defects and Inconsistencies in Solar Flare Data Sources," arXiv:2512.13417
- Jonas, E., et al. 2018, arXiv:1708.01323
- Kniezewski, Mason, Uritsky & Garland 2024, ApJL, 977, L29
- Leka, K. D., Dissauer, K., Barnes, G., & Wagner, E. L. (AARP Paper II), arXiv:2212.11255 ⚠ journal version
- Leka, K. D., et al. 2019, arXiv:1907.02905 ⚠ journal version
- Lemen, J. R., et al. 2012, Sol. Phys., 275, 17 (AIA)
- Scherrer, P. H., et al. 2012, Sol. Phys., 275, 207 (HMI)
- Wang et al. 2020, arXiv:1912.00502
- Warren, H. P., Winebarger, A. R., & Brooks, D. H. 2012, ApJ, 759, 141
- (Only if cited in the text) André-Hoffmann et al. (BADPIT), arXiv:2604.26036; Dissauer et al. 2023 (AARP I), ApJ, 942, 83.

---

## Appendix A: Chronology of all 31 ideas (corrected statuses)
"Pre-registered" = hypothesis, data, statistic and reading rule committed before the outcome was computed. "Dev" = exploratory, cross-validated on 2010–2019 only.

| # | idea | data | status | result |
|---|---|---|---|---|
| 1 | 24-h magnetic trends (Model B) | test 2021/23/24 | pre-registered | Δ −0.005 [−0.020, +0.009]: not supported |
| 2 | 94 Å restlessness at the PIL (ΔCV) | dev → test | pre-registered | dev −0.004; test +0.003 [−0.007, +0.014]: not supported |
| 3–19 | PIL variants, spikiness (R4a/b/c), sizes, brightness, B-flare counts, combinations | dev | exploratory | all dev CIs include 0; R4a best on dev |
| 20 | spikiness R4a on new years | test; 2025–26 | pre-registered | test: "direction consistent, not confirmed"; filter −13 pts true; 2025–26: CI includes 0 |
| 21 | **restlessness twins (CV_box)** | dev → test → 2025–26 | pre-registered on test and 2025–26 | dev 1.97; test 1.31 (not confirmed); **2025–26 3.26 [1.30, 9.49], replicated** |
| 22 | **flare recency (Model C)** | 2025–26 | pre-registered | Δ +0.0173 [+0.0016, +0.0350]: passed narrowly |
| 23–27 | timing, log-spikiness, three masks, recharge vs clustering, parasitic dots, new vs repeat brightenings | dev | exploratory | no detectable effect / not eligible |
| 28 | restlessness filter on Model A | unseen 2021/23/24 | pre-registered | +60 pts false, −16 pts true: failed |
| 29 | restlessness filter on Model C | 2025–26 | pre-registered re-test | +24.0 false, −14.0 true: failed |
| 30 | B-flare count + spikiness | test; 2025–26 | pre-registered re-analysis | stopped by the data check (57% attribution in 2023) |
| 31 | C+ protection rule | all sets | exploratory; prospective test registered | more false removed in all 5 periods; see §4.8 |

⚠ The old draft wrote "confirmed" for rows 21 and 22. Use "pass rule met (margin sensitive to region reuse)" and "passed narrowly".

## Appendix B: Independent verification (optional in the paper; strong for the interview)
- A separate script with its own SWPC parser, restlessness code, twin matching, bootstrap and model refits: `docs/verification/verify_independent.py`.
- Results:
  - 0 label mismatches in 1,875 episodes.
  - CV_box identical to ~1e-13 in 1,556 episodes.
  - Gate TSS exactly reproduced.
  - The same twin pairs in every stored set.
  - Every headline Δ and D reproduced to the 3rd–4th decimal (bootstrap seeds differ).
- Full table: `docs/PAPER_WRITING_KIT.md` §7.

## Appendix C: Definitions judges may ask about
- **TSS** = TPR − FPR. **FAR** = FP / (TP + FP) = 1 − precision (a ratio, not a rate).
- **Alarm episode vs region vs hour:**
  - test true share: 14.4% of episodes, 45.7% of regions, 29.8% of hours;
  - test FAR: 0.856 of episodes are false, 0.543 by region, 0.702 by hour.
- **Log-loss** (weighted) = mean of −[y log p + (1 − y) log(1 − p)] with 1/n-per-HARP weights. Lower is better; Δ > 0 favours the new model.
- **HARP bootstrap:** resample whole regions with replacement, recompute, take the 2.5/97.5 percentiles.
- **Caliper:** the maximum allowed gate-score difference for a twin pair (0.0747 = 0.2 SD of dev scores).

---

## Part C: What changed from the old draft (checklist)
1. **Pre-registration timing sentence was false.** Corrected in §3.6.
2. Removed the invented "SE 0.0165 / 7% power".
3. Both authors, "we", specific contributions.
4. Step B "confirmed" → "passed narrowly"; dev −0.0020 and the single-region CI now shown.
5. log(1 + R) coefficients: −0.18 to −0.36 (mean −0.30; OR 0.74), not −0.19 to −0.33.
6. B&C reproduction gap: 0.083 / 0.045 (0.045–0.103 over all runs), not "0.05–0.08".
7. "3.26 times more restless" → "3.3× higher median restlessness"; sign-test p de-emphasised (18 regions).
8. Table 4: "~40" → 40; true HARPs and true > false columns added; status words fixed.
9. Removed "pairs differ in the fourth decimal" (unmeasured); max difference 0.060 given instead.
10. Tiers table now includes NO ALERT and CIs.
11. Filter section now shows the full three-level rule and the secondary C vs C_CV rows (unseen −2.6, 2022 −8.7) that met the operating criterion; the result is mixed, and nothing reached "safe".
12. Added heterogeneity, clustering, matching-order, multiplicity, confounding and cycle-drift limitations.
13. Added Table 10 (box vs PIL vs control) and the honest answer on why CV_box was chosen.
14. One idea count (31) everywhere.
15. Fig 4 right-panel label: 4 later sets, not 5. Fig 1: 40, not ~40.
16. Added a title page, table of contents, anonymity check and a submission-grade AI statement.

## Part D: Synopsis and video map (IRIS form fields)
| field (limit) | take from | must contain |
|---|---|---|
| Abstract (≤ 250) | Part B abstract points 1–8 | 3.26 [1.30, 9.49]; 2.73; +0.017; −14 pts; tiers |
| Introduction & Objective (100–150) | §1 ¶1–¶4 | false-alarm problem; dangerous-vs-dangerous gap; RQ in one sentence |
| Innovation (50–100) | §1 gap + §3.4 + §3.6 | pick 2: magnetic twins; one-shot pre-registered future-year test (plus the HEK finding if room) |
| Methodology (150–250) | §2–§3 | gate; episode + label; CV_box formula in words; twins; models A/C; sets; HARP bootstrap |
| Results & Conclusions (100–150) | Part A3 table | H1 yes, H2 narrowly, H3 no; grades not vetoes |
| Acknowledgement & References (50–100) | §7–§8 | data providers; guide; AI clause; 4–5 cites |
| Video (≤ 90 s) | Fig 1, Fig 2 GIF, Table 8 | hook → gate and 86% false → twins → 3.3× → honest filter failure → tiers; both on camera |
