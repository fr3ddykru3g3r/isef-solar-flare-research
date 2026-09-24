
## 2026-09-24 — DOCUMENTATION ENTRY: frame-rule check, literature review, design justification, open proposals, Q&A  (recorded by: Claude chat, on user request; documentation only)
**Scope:** no rule, frozen file, result or code was changed. No ΔCV value was read, computed or reported, and nothing was split by label. The only new number (item 1c) is a frame count from `data/euv_full/series/*.csv` (columns `exp_ok`, `flare`, `q_ok`), read-only.
**Sources:** literature quotes were checked in the PDF text on 2026-09-24 unless marked otherwise. Items marked *(2026-09-23 read)* come from Claude chat's PDF reads on 2026-09-23 (project status doc), and were not re-checked today.

### 1. Frame rules: code vs recorded rules (read in `euv_full.py` `compute_episode`, `euv_pilot.py` `flare_excluded`)
**a. How each rule is applied, per frame:**
- **QUALITY:** `q_ok = quality == 0`.
- **Exposure:** the median EXPTIME is taken over QUALITY == 0 frames in the episode's (t−24h, t] window. `exp_ok = exptime >= 0.5 × median`.
- **P2 amended (flare in progress):** the frame's T_OBS falls inside the begin–end interval of either:
  - (a) a C1+ SWPC event (K2) with `noaa_ar` in the HARP's NOAA region(s), or
  - (b) any M1+ event.
  - Events are loaded for [t − 2 d, t].
- **Saturation (P4/U4):** `raw > 12,000 DN` → those pixels are set to NaN before exposure normalisation. The frame is kept, with `sat_flag = True` and the count stored in `sat_px`.
- **Versions:**
  - `valid_primary = q_ok & exp_ok & box.notna()`
  - `valid_sens = valid_primary & ~flare`

**b. Conclusion:** the code matches the recorded rules. Check B of the proposed go-ahead (saturation wording) is already answered by two existing entries:
- the amendment's "Note (me)": P4/U4 removes pixels, not frames;
- step 2a: the flag area includes the 50″ margin.

The only inaccuracy is the phrase "Frames are still removed by … saturation rule P4/U4" in the amendment's PRIMARY bullet. Pixels are removed there; frames are only flagged.

**c. NEW descriptive count: exposure rule vs flare intervals** (546 episodes, 65,253 frames):

| exposure-rule frames | count |
|---|---:|
| total | 661 |
| of which also QUALITY ≠ 0 | 544 |
| of which QUALITY == 0 | 117 |
| inside a P2 flare interval, any QUALITY | 86 |
| inside a P2 flare interval, QUALITY == 0 | 68 |

- The exposure rule removes only 68 QUALITY-good flare-interval frames from the PRIMARY version. For scale, 2,180 frames lie in P2 flare intervals (any QUALITY).
- Background: AIA's Automatic Exposure Control (AEC) shortens exposures during flares. Dissauer et al. 2023 show an example of 2 s → 0.43 s at 193 Å.

### 2. How other studies handle flares inside the analysis window
| study | what they do with flare-contaminated data | sample |
|---|---|---|
| Dissauer, Leka & Wagner 2023, ApJ 942:83 (AARP I) | Flare times **included**; AEC (short-exposure) images **avoided** (72-s sampling): "Avoiding the AEC images allows for times of flares to be included with less dramatic impact to the moment analysis." | 2010-06 → 2018-12, all HARPs |
| Leka, Dissauer, Barnes & Wagner, arXiv:2212.11255 (AARP II) | Flares **not removed**: "Flares occur during the data acquisition … but rarely do their influence persist more than 2 – 3 hr … the linear fits generally all but ignore them." "Perfect storm" outliers "typically occur no more than 0.1% of the time." | same |
| André-Hoffmann et al. 2026, Solar Physics (BADPIT) | Flares **kept**: TBs "include potential subflaring events but also up to C- and M-class flares and does not distinguish them." Pixels > 12,000 DN "replaced by values derived via linear interpolation in time." | 2 ARs, 24 h |
| Jonas et al. 2018 (arXiv:1708.01323) | "we discard data during the flash phase of the flare." Flare history: "prior flaring activity has significant predictive capacity in and of itself." | 4,272 flares ≥ C1.0 (3,836 C, 406 M, 30 X) |
| Kniezewski, Mason, Uritsky & Garland 2024, ApJL 977:L29 (Sec 2.1) | Whole events **selected**: "discounted if a flare of magnitude C5.0 or greater occurred in the same active region within 6 hr." Flares < C5 were allowed inside the window. Quiet cases: ≥ 12 hr with no ≥ C flare, and a 6-hr window with ≥ 3-hr buffers. | 53 flares vs 30 quiet windows |
| Kniezewski, Mason, Emmons, Fitch & Garland, arXiv:2506.14004 (submitted to ApJ; checked on the arXiv HTML page only) | Flares removed if a ≥ C5.0 flare occurred in the same AR within 6 h; quiet = no ≥ C5.0 for 7 h. NLFFF magnetic variability. | 18 flares (6 C/6 M/6 X) |
| Dissauer, Barnes, Leka & Wagner 2025, arXiv:2503.12338 (Sec 2) | Active epoch = pre-flare period "during which no other flaring events above the C1.0 level occur". Activity below C1 is analysed. 2-h windows end 4 min before the GOES start. Flare list = SWPC warehouse. | 3 events |
| Zhong, Kolotkov & Nakariakov, arXiv:2602.18133 (Sec 2.1) | "There should be no other flares at least 3 hours earlier than the start time of the candidates." No class or region threshold stated. | 14 flares in 13 ARs + 1 quiet AR |

**Where this project sits:**
- **PRIMARY** version = the AARP approach: flare frames kept, short-exposure frames removed.
- **SENSITIVITY** version = frame-level removal of flare intervals (the Jonas idea).
- **Model A** already contains flare history (n_C, n_M, n_X, 48 h).

Event-selection designs (Kniezewski, Dissauer 2025, Zhong) are not usable for an alarm-time forecast. They drop regions that flared recently, and here they would drop true alarms preferentially (validity audit 4c25475; step 4 table: the 90% sensitivity rule kept 64% of true vs 85% of false).

### 3. Design choices vs published work (justification)
| choice | this project | published basis |
|---|---|---|
| Question: true vs false among magnetically flagged regions | Alarm vs alarm (both "dangerous") | Alatoom & Nikolaou 2026, Space Weather (10.1029/2026SW005010): the most common FPs "are magnetically complex, historically productive regions … physical readiness does not necessarily translate into imminent eruption." Kniezewski 2024 matched quiet ARs by complexity so results "were not skewed by inherent differences between the types of active regions." |
| Second stage to cut a magnetic model's false alarms | EUV at the PIL, tested as added information over the gate + flare history | Deshmukh, Flyer, van der Sande & Berger (arXiv:2111.10704; published in ApJS as "Decreasing False-alarm Rates in CNN-based Solar Flare Prediction Using SDO/HMI Data"): magnetic-only second stage; "reduces false positives by ≈ 48% without significantly affecting the true positives (reduction by ≈ 12%)". |
| Flare labels | SWPC originals, K2 (÷0.7 for GOES-13/14/15) | Hu et al. 2026, arXiv:2512.13417 (entry 2026-09-22). Dissauer 2025 also uses the SWPC warehouse. |
| Split | Dev 2010–2019, grouped CV; test 2021/2023/2024 | Francisco, Guastavino, Fernandes, Barata & Del Moro, arXiv:2410.16116 (journal version not verified): "5-fold CV done on the period ranging from May 2010 to December 2019", test Jan 2020 → Apr 2023 *(arXiv HTML)*. Chen et al. 2024 review and Wang et al. 2020: results depend on split and years *(2026-09-23 read)*. |
| Magnetic gate | Bobra & Couvidat 2015-style SVM, 10 SHARP features | Bobra & Couvidat 2015, ApJ 798:135 (reproduction entries 2026-09-21/22). |
| Channel | AIA 94 Å only | Leka 2023: "The 94 Å filter data provides the most parameters with discriminating power." BADPIT: "The 94 Å channel proved to be the most suitable channel for the tracking." Francisco 2024: "The 94Å wavelength provides the most discriminative features for flare prediction." |
| Location | PIL mask ±150 G, 16-px dilation, 30 G AR mask | BADPIT PIA (after Schrijver 2007): identical. Dissauer 2025: TBs cluster near strong-gradient PILs before flares *(2026-09-23 read)*. |
| Window | (t − 24 h, t] | BADPIT: 24 h. AARP: hourly bursts over ~6 h. Kniezewski: 6 h. Dissauer 2025: 2 h. Zhong: ≥ 2 h. |
| Cadence | 12 min (12 vs 2 min: ρ 0.952, n = 8; commit 9a56c68) | Physics studies: 12 s (Zhong, Harra 2026, BADPIT), 72 s (AARP), 3 min (Kniezewski). Forecasting: 12 min (Jonas 2018), 6 min (SDOML), 1 h (Nishizuka), 2 h (Francisco 2024). |
| Metric | CV of the detrended PIL-mean series minus the mean CV of 20 matched in-image controls | Closest: Kniezewski 2024 (SD ratios of integrated emission). Harra 2026 (temporal SD maps; 2 flares). See risk 4a. |
| Saturation | Pixels > 12,000 raw DN removed, not interpolated | BADPIT uses the same 12,000 DN threshold (following Schwartz et al. 2015) but interpolates. |
| Baseline includes flare history | Model A = gate + n_C, n_M, n_X | Jonas 2018 (quote above). Camporeale & Berger 2025, Space Weather (10.1029/2025SW004546): persistence TSS 0.46; SWPC does not outperform the baselines *(2026-09-23 read of the arXiv version)*. |
| Metrics reported | log-loss, AUC, TSS, FAR, precision | Leka 2023: "no single metric provides a thorough evaluation of performance." Camporeale & Berger warn about high TSS reported alongside very high FAR *(2026-09-23 read)*. |

### 4. Known risks and limitations (stated before step 6)
- **a. Metric type.**
  - Leka 2023: "enhanced variability in EUV and UV intensity on short timescales and small spatial scales is one of the strongest discriminators", "spatial resolution matters", and "surprisingly poor is the mean intensity and its longer-term trending."
  - ΔCV is the variability of a PIL-averaged mean at 12 min, so it may miss that signal. A null result is a possible and reportable outcome.
- **b. Timing.**
  - The window ends at alarm time t, but the flare can occur up to 24 h later.
  - Kniezewski 2024: variability "increases from 4 hr before flare onset, peaking in the 1–2 hr before onset."
  - Test-years lead time from episode onset (entry 2026-09-23 "Read-only checks"): median 12.4 h for true episodes. Precursors close to the flare can therefore fall after the window.
  - Rationale for the design: an operational forecaster must decide at alarm time.
- **c. Cadence (inference, Claude chat).** 12-min sampling has a Nyquist frequency of 0.69 mHz, below Zhong's 0.9–10 mHz band. Faster variability can alias.
- **d. Residual flare emission.**
  - The SWPC end time is not the end of 94 Å emission, and Leka 2023 says flare influence lasts up to 2–3 hr.
  - So the SENSITIVITY version (begin–end removal) can still contain post-flare emission (inference).
- **e. Coverage.** 26 episodes (14 HARPs) have HMI patch pixels outside the cutout; the maximum fraction is 5.8%.
- **f. Sample.** Dev n = 98 true / 449 false (unweighted episodes); EUV is dev-only until a held-out EUV test is run.

### 5. Open proposals — NOT decided (user decision needed before step 6)
Proposed by Claude chat on 2026-09-24. Status: **not sent to Claude Code, not recorded as decisions.**
- **A.** Fill threshold 80%. Already fixed by the pre-registered rule (ff3c11c); no decision needed.
- **B.** Saturation wording check. Answered in 1b; no action needed.
- **C.** Added sensitivity: repeat the primary test without the 26 overhang episodes.
- **D.** Pre-register (do not run yet) a held-out EUV test on 2021/2023/2024: single-region T2 cohort, 313 episodes; E94 = model A + ΔCV_94 (primary version); same pipeline and rules; weighted Δlog-loss (E94 − A); HARP bootstrap 10,000; AUC.
- **E.** Run step 6 exactly as in the amendment.
- **F. (new)** Added sensitivity: also exclude frames up to 2 h after each P2 event's end time. Report n valid per group at 80%.
- **G. (new)** Report the item-1c counts alongside step 6.

### 6. Questions and answers (plain language; numbers from the entries cited)
**Q: What is the project about?**
A standard magnetic model (the gate) raises alarms for regions that look dangerous. Most alarms are false. The question: among alarmed regions, does EUV brightness variability above the polarity inversion line (PIL) separate real alarms (M1+ within 24 h) from false ones, beyond what the magnetic score and recent flare history already tell us?

**Q: What is an alarm episode, and how many are there?**
- An episode is a run of consecutive alarm hours for a HARP (rules T1–T4; alarm time = first evaluable hour).
- Dev 2010–2019: 547 episodes in 180 HARPs, of which 98 true and 449 false.
- Test 2021/2023/2024: 313 episodes (45 true, 26 delayed, 242 other false); delayed episodes count as false.

**Q: How often is an alarm real?**
- At episode onset (test): 45/313 = 14.4% (14.8% region-weighted).
- Hour level (test): 1,188/3,988 = 29.8% (FAR 0.70).
- Region level: 48/105 = 45.7% (time-linked: 39/105).

**Q: Why not use accuracy?**
Positives are rare. Hourly base rate in test rows = 3.70%, so "always no" is ~96% accurate by hour and ~85% at episode onset. AUC 0.81 (model A) is a ranking measure, not accuracy.

**Q: Is the gate a strawman?**
On test hours the gate beats persistence (TSS 0.547 vs 0.358). Its FAR (0.70 by hour) is in the range of published baselines, e.g. Bloomfield et al. 2012: best TSS 0.52 with precision ≈ 13% *(2026-09-23 read)*. Region-level persistence looks better only by construction (definition note, entry 2026-09-23).

**Q: Did 24-h magnetic trends help?**
No. Δlog-loss(A − B) = −0.0051 [−0.0201, 0.0094]. AUC: A (no trends) 0.811, B (with trends) 0.797.

**Q: What were the "phantom" false alarms (Path A)?**
Alarms counted false with HEK labels but true with SWPC originals, because HEK loses region numbers (AR = 0). The defect is already published (Hu et al. 2026); Path A quantifies its effect on FAR (entry 2026-09-22). The ×0.7 scaling is not the cause: all 34 phantoms are GOES-16/18 flares.

**Q: Why these years?**
- 2020: excluded by the ≥ 90% region-join rule.
- 2022: sensitivity only.
- 2025–2026 confirmation set: paused.
- The chronological test (train on the past, test on later years) follows Francisco 2024 and avoids the optimism of random splits (ablation: random split ~+0.11 TSS vs region-grouped).

**Q: Why keep flare frames in the primary version?**
- Removing them dropped true alarms more than false ones (90% rule: 64% vs 85% kept).
- Keeping them, with short-exposure frames removed, is the AARP method.
- The sensitivity version removes them to check that the result is not just "a flare was already happening".

**Q: Why 94 Å, the PIL mask, 24 h and 12 min?**
See section 3.

**Q: How are the frame checks done?**
See section 1a: QUALITY keyword; exposure ≥ 50% of the window median; SWPC begin–end intervals; pixel saturation > 12,000 DN.

**Q: What do the step 4 numbers mean?**
- Each episode needs enough valid 12-min slots (120 in total).
- Rule chosen in advance: the strictest level where true and false alarms lose a similar share (≤ 10 pp) in both versions.
- 90% failed (sensitivity gap 20.8 pp); 80% passed (1.15 and 6.96 pp).

**Q: Can the method change after submitting?**
ISEF: no project changes after the affiliated fair. Extra data only with the same method and only if it is in the approved research plan. So all planned phases (including the held-out EUV test) must be written into the research plan.

### 7. Administrative facts recorded (checked 2026-09-23 on the official sites; re-check before relying on them)
**IRIS 2026–27** (iris.exstemplar.com):
- Registration/submission window: 1 Aug – 3 Oct 2026, "no extensions".
- One project guide required.
- Submit: synopsis (word limits per section), full research paper and a 90-s video.
- "Maintain a research data book."
- No school name, city or state in any material.
- Eligibility with OCI: to be confirmed with IRIS.

**ISEF 2027:**
- Forms 1, 1A (with research plan), 1B, 2A, and the abstract.
- Research plan, abstract, poster and citations to be written by the student; AI use cited.
- Experiments run before a signed plan must be discussed with the sponsor/SRC.

**Sources for this entry:** the PDFs in `output/` (literature, not in git) and arXiv/journal pages: 2212.11255, 2411.12704, 2506.14004, 2503.12338, 2602.18133, 2604.26036, 1708.01323, 2410.16116, 2111.10704, 2512.13417, 10.1029/2025SW004546, 10.1029/2026SW005010, 10.1007/s11207-026-02691-5.
