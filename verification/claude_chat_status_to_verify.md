# Solar-flare false-alarm project — status summary
Last updated: 2026-09-22 (night). Written by Claude (chat) as a reference for Lokesh. NOT research-plan or board text (ISEF Rule 8: those must be written by the student). The authoritative log is `decisions.md` in the repo.

## 1. Question
Among solar active regions that a standard magnetic-field model flags as high risk for an M1+ flare within 24 h, what separates true alarms from false alarms?

## 2. Data (built and audited)
- SHARP keywords (hmi.sharp_cea_720s), 2010-05 → 2024-12, hourly: 254,899 labelled rows after dedup.
- Flare labels from SWPC original daily event reports (not HEK). Region numbers: 4-digit Reg# + 10000.
- Flare scale: K2 = true irradiance (GOES-13/14/15 fluxes ÷ 0.7), per NOAA/NCEI recommendation (Hudson et al. 2023; SWSC 2025).
- Filters: QUALITY == 0, |LON| ≤ 45°, usable NOAA mapping. Primary subset = single-region HARPs.
- Empty SWPC days checked against GOES XRS flux; missing/low-coverage days excluded.
- Years excluded by fixed ≥90% region-join rule: 2020; 2022 (primary test; kept as sensitivity).

### Data-audit findings
- HEK's SWPC events lose NOAA region numbers (ar_noaanum = 0) — almost entirely after ~2020, some already in 2014. SWPC originals retain them. ALREADY PUBLISHED: Hu et al. 2026 (arXiv:2512.13417, p. 9) — see 7b.
- SWPC flare classes change scale in late 2019 (GOES-15 ×0.7 operational → GOES-16 true flux). Also documented by Hu et al. 2026 (Fig. 4) and NOAA/NCEI.
- HMI QUALITY bit 0x10000 (QUAL_LOWINTERPNUM) removes ~all 06:00/18:00 TAI records.
- Month-boundary duplicate records from inclusive JSOC ranges (fixed).
- SWPC M1+ completeness vs GOES flux (sampled Marches): 134/137 (~98%).
- Residual GOES-15 vs GOES-16 calibration difference ~8% (NCEI ratio 0.923).
- The current public NCEI/NGDC GOES XRS flare report has NO flare locations for 2011 (0 of 2,171 rows), although Bobra & Couvidat (2015) required NGDC flare locations. Their flare list cannot be rebuilt from today's public files.

## 3. Split
- Dev (train+validation): 2010–2019, grouped 5-fold CV by HARP. Test: 2021, 2023, 2024 (2022 sensitivity). split.csv hash f3ab4056…
- Positive single-region HARPs: dev ~86; primary test 55.

## 4. Gate (danger detector) — FINAL: 10-feature gate is primary for all analyses
- Bobra & Couvidat 2015-style SVM: 10 of their 13 features (TOTUSJH, TOTPOT, TOTUSJZ, ABSNJZH, SAVNCPP, USFLUX, AREA_ACR, MEANPOT, R_VALUE, SHRGT45); RBF, C=4, γ=0.075, C1/C2=2; median/SD scaling; training rows thinned to TAI hours {4,10,16,22}.
- Threshold = max TSS on pooled out-of-fold scores (−0.9925).
- Dev OOF TSS 0.679 (region bootstrap 95% CI 0.59–0.75), mildly optimistic.
- Test 2021/23/24: hour-level TSS 0.547 [0.41, 0.66], FAR 0.70; region-level TSS 0.728 [0.63, 0.82].
- 13-feature gate: only used in the reproduction and, optionally, as a labelled robustness gate.

## 5. Main result (pre-registered, run once on test)
- Question: do 24 h relative slopes of USFLUX and TOTUSJH add information beyond gate score + C/M/X flare history (48 h)?
- Test Δ log-loss(A − B) = −0.0051, 95% CI [−0.020, 0.009]; AUC A 0.811 vs B 0.797. All robustness variants near zero.
- Conclusion: no detectable improvement from these two slopes in this cohort; any benefit is small at most. Does NOT show magnetic evolution is uninformative in general.
- Dev exploratory: gate score alone gave the lowest log-loss; adding C/M/X counts did not improve it.

## 6. Bobra & Couvidat (2015) reproduction — CLOSED
- Paper (arXiv:1411.1405; ApJ 798:135): Table 2 TSS 0.610 ± 0.048 (C1/C2 = 2); Table 3 0.761 ± 0.039 (C1/C2 = 15). ± = SD over 1,000 random 70/30 splits.
- Ours: D7/D8 0.527 / 0.716; R1 0.515 / 0.706; R2 (NGDC) 0.520 / 0.708; R4 (13 features, SWAN-SF) 0.530 / 0.695; R4-cgem 0.507 / 0.695; D7t (learned threshold) 0.707. Pre-registered target (±1 SD) not reached.
- Same qualitative behaviour, consistently 0.05–0.08 lower TSS. Likely causes (none proven): changed NGDC catalogue (no 2011 locations), unstated details (threshold, parameter validation), possible SHARP reprocessing.
- Wording: "not fully reproducible from the published description".
- Paper inconsistency: top-4 feature list differs between p. 25 and p. 32.
- Ablation (dev): same gate scores 0.34–0.81 depending only on evaluation choices; random split ~+0.11 vs region-grouped.

## 7. EUV pilot (in progress)
- Metric D-CTRL: CV of detrended mean intensity over (t−24h, t] in PIL mask (hmi.sharp_720s LoS, ±150 G, 16 px dilation, 30 G AR mask) minus mean CV of 20 pixel-count-matched random controls (seeds 0–19). AIA 94 Å primary, 1600 Å secondary, 12-min cadence.
- Pilot: 3 dev episodes (HARP 4231 true, 6975 delayed, 3248 false). No scientific result (n = 3).
- Cost: JSOC 1 export at a time; 12 s cadence ruled out. url-tar test: HARP 6975, 1,800 files in ~14 min (prep 475 s + download 375 s) vs ~105 min per-file (HARP 4231) ≈ 7.5× faster. Synoptic vs cutout ΔCV (24 h, same masks): max |diff| 0.017 (HARP 4231 94 Å), ≤0.004 in 5 of 6 channel-cases → synoptic viable (n = 3). HARP 6975 1600 Å synoptic: 8 of 120 files missing in archive.
- Cadence check (6 h window, 94 Å): ΔCV 12 s vs 12 min: 4231 0.208 vs 0.150 (+0.058), 6975 0.212 vs 0.232 (−0.021), 3248 0.178 vs 0.198 (−0.020). Ranking of the 3 HARPs changes with cadence. ± reported = control-draw spread only, not sampling error. 12 s still ruled out on cost; cadence dependence = limitation; offset-subsampling test proposed.
- Download rates: JSOC per file ~3.5 s/file; url-tar 14 min / 1,800 frames; synoptic 1.08 files/s (6 connections). Rough full-study estimate (mine, unverified): synoptic both channels ~21 h; JSOC url-tar ~1 day per channel. Synoptic AIA: 1.08 files/s with 6 connections; 40,070 unique 12-min timestamps for 547 dev alarms. url-tar being timed.

### EUV literature: cadence and resolution (verified from the PDFs, 2026-09-23)
- Dissauer, Leka & Wagner 2023, ApJ 942:83 (AARPs, Paper I = dataset): native AIA resolution (1.5" at 0.6"/px) HARP-centred patches; 8 channels (94, 131, 171, 193, 211, 304, 335, 1600); ~13-min bursts at 72 s (11 images/h), hourly 15:48–21:48 UT daily; 2010-06 → 2018-12. NOT flare-timed. 72 s chosen because native-cadence S/N was low and 'full time resolution is unnecessary to capture the short-lived brightenings'; AEC (auto-exposure) images avoided. Explicitly criticises ML studies' spatial binning ('hampers the ability to discern any small-scale processes').
- Kniezewski, Mason, Uritsky & Garland 2024, ApJL 977:L29: 3-min cadence, 6 h before onset; off-limb loops of limb flares (±850"); channels 131, 171, 193, 304 (no 94, no 1600); level 1.5 via SunPy, exposure-normalised, no background subtraction; 53 flares ≥C5.0 (4 X, 25 M, 24 C; 2011–2022; XRT + HEK catalogues) vs 30 flare-quiet windows in 30 ARs; pooled-SD ratios, DFA, structure functions. 131 & 304 Å ratios >2; variability rises from ~4 h, peaks 1–2 h before onset; flare-active ARs' ratio never drops to 1 (possible inherent variability). CLOSEST PRIOR WORK: cite. Our design (alarm vs alarm, both 'dangerous' ARs) addresses their inherent-variability caveat.
- Zhong, Kolotkov & Nakariakov, arXiv:2602.18133v1 (Feb 2026 preprint; journal version NOT verified): native 12-s full-resolution JSOC cutouts (level 1.5), on-disk near centre; per-pixel Fourier spectra averaged in 10×10 macropixels; 30-min windows slid in 1-min steps; low-frequency band 0.9–10 mHz; 14 flares (4 C, 5 M, 4 X in 13 ARs) + 1 quiescent AR.
- Nishizuka et al. 2018, ApJ (DeFN, arXiv:1805.03421): AIA 1600 & 131 Å (native 12 s) reduced to 1-h cadence; 2010–2015.
- Galvez et al. 2019, ApJS (SDOML, arXiv:1903.04538): built FROM the AIA synoptic series (4×4 averaged → 1024×1024, 2.4"/px, 2-min cadence), then 512×512 (~4.8"/px), AIA at 6-min.
- Inference (mine): 12-min sampling has Nyquist 0.69 mHz, below Zhong's 0.9–10 mHz band; 3-min (Kniezewski) reaches 2.8 mHz. Single-exposure frames at 12 min can alias faster variability. Supports running the 2/3/6/12-min test.

### Literature batch 2 (15 PDFs uploaded 2026-09-23; read by Claude chat)
- FILE ERROR: 'doria_rosales_2026_multimodal_forecast.pdf' is actually Brevi et al., arXiv:2602.11193, deuteron physics-informed NN — not solar. Discard.
- André-Hoffmann et al. (BADPIT), arXiv:2604.26036v2 (Solar Physics format; publication not verified): AIA 94/131/171/193/1600, 12 s, full res (0.6"/px) JSOC cutouts, exposure-normalised, desaturated; 24 h windows; 2 ARs (flaring 11429 vs non-flaring 13186). PIA = |B| > ±150 G masks dilated 16 HMI px (8") overlap, AR mask 30 G (Schrijver 2007) — IDENTICAL to our D-CTRL PIL mask → must cite. 94 Å best channel; ~5× more transient brightenings in flaring AR.
- Leka, Dissauer, Barnes & Wagner (AARP Paper II), arXiv:2212.11255: 94 Å gives most discriminating parameters; 'enhanced variability ... on short timescales and small spatial scales is one of the strongest discriminators'; 'spatial resolution matters'; mean intensity and its longer-term trending 'surprisingly poor'; evolution parameters 'little preference over static'. TSS 0.68–0.82.
- Dissauer, Barnes, Leka & Wagner, arXiv:2503.12338: 3 events, 2-h pre-flare vs paired quiet epochs of the SAME AR; 72 s, full res; TBs cluster near strong-gradient PILs before flares; smaller, scattered clusters in quiet epochs.
- Harra et al. 2026, Solar Physics 301:93: AIA 171 Å 12 s, temporal SD maps; SD enhancement in high-free-energy regions peaks minutes before GOES; 2 flares.
- Jonas et al. (arXiv:1708.01323): 12-min cadence, AIA 1600/171/193 + HMI, 2010–2014, 2,182 ARs; photospheric + flare history best for TSS.
- Nishizuka et al. 2017 (arXiv:1611.01791): 1600 Å, 1-h cadence; fully shuffled split gave TSS > 0.9. Nishizuka et al. 2021 (operational DeFN, EPS): NRT data, 1-h training cadence, forecasts every 6 h.
- Alatoom & Nikolaou 2026, Space Weather 24 e2026SW005010: SDOBenchmark, 256→128 px, 4 frames before t0; most common false positives = 'magnetically complex, historically productive regions' — 'physical readiness does not necessarily translate into imminent eruption'.
- Roy et al. (SuryaBench), arXiv:2508.14107: full-res 4096², 12-min, 2010–2024, ~600 MB per file, ~360 TB total → impractical source.
- Pattern: every physics/precursor study here uses ≤3 min cadence and full resolution; ML forecasting uses 6 min–1 h and/or downsampled images. Our planned synoptic/12-min ΔCV is closest to Kniezewski-style integrated variability, not to the short-timescale/small-scale signal Leka 2023 found strongest.

### EUV settings test — RESULT (commit 9a56c68, 2026-09-23)
- Cadence rule → 12 min passes (ρ 0.952 [0.615, 1.000], median |Δ| 0.0077, n = 8; cutout second opinion ρ 1.000, median 0.0174, n = 5).
- Source rule → synoptic FAILS (median |diff| 0.0183, ρ 0.600 [−0.636, 1.000], n = 6) → full study uses JSOC cutouts (url-tar, pipelined; 0 rejections in 25 overlapped exports).
- Exposure rule adopted; crop verified.
- Fill rule (≥90% valid slots, flare-in-progress frames not counted) left only 8/15 alarms valid at 2 min; 131 Å 10/15 valid at 12 min → risk of label-dependent exclusion (flaring regions excluded more). Needs handling before full run.
- Cost (547 dev alarms, cutouts, 12 min, per-HARP exports, pipelined): 94+1600 Å 86,060 files, 18.6 GB, ~14 h download, 3.3 h processing; +131 Å 129,090 files, 32 GB, ~21.5 h. HMI mask exports not included.

## 7b. Path A — "phantom false alarms" (done; commit 7eb9c55)
- Compared the gate's alarms scored with HEK labels vs SWPC-original K2 labels.
- 52 of 852 alarms (6.1%) counted "false" with HEK are real M1+ flares in SWPC originals; 34 of 386 (8.8%) in 2021–24 (2022: 15, 2023: 17). 0 region-loss phantoms in 2010–19. Scale-only effect (K → K2): 45 of 846.
- FAR 2021–24 (includes 2022; 5,145 alarm hours; 139 alarmed regions of 605; 2,000 HARP bootstrap resamples, seed 0; commit 2ba51d3):
  - hourly FAR HEK 0.838 [0.760, 0.911] vs K2 0.733 [0.661, 0.804]; difference 0.105 [0.066, 0.147]
  - region FAR HEK 0.763 [0.691, 0.829] vs K2 0.576 [0.494, 0.659]; difference 0.187 [0.122, 0.252]
- 34 phantoms in 20 HARPs (2021: 2, 2022: 15, 2023: 17, 2024: 0). HEK region number 0: 27; two HEK events both 0: 3; no HEK event within ±10 min: 4 (HARP 9699; HARP 10430 ×3).
- Evidence pack (data/pathA/evidence/): HARPs 8942, 9121, 9182 (2023) — HEK AR = 0 AND location fields zero (hpc_x 0, hgs 0/0).
- Primary test years only (2021/23/24): hourly FAR HEK 0.801 vs K2 0.702, diff 0.099 [0.057, 0.150]; region FAR 0.724 vs 0.543, diff 0.181 [0.112, 0.259] (105 alarmed regions of 450). K2 hourly FAR matches the gate's test FAR (~0.70). 2022 alone: hourly FAR 0.968 vs 0.840; hourly precision HEK 0.032 vs K2 0.160.
- 26 region flips explained: 15 phantom first-hour episodes; 7 later alarm hours within an episode; 4 regions whose K2 flares fall only outside alarm hours (flip because region-level truth = 'region flared at all').
- Verified in code: all 34 phantom flares are GOES-16 (30) / GOES-18 (4), so ÷0.7 not applied; HEK class = SWPC class for all 30 with HEK events. Phantoms caused by HEK AR = 0, not by K2.
- Open: 2024 zero phantoms (HEK AR=0 counts per year running); 4 'no HEK event' cases (±60 min search running).
- Prior work: Hu, Jin, Verma, Liu, Manchester, Zhao, Gombosi & Chen, "Defects and Inconsistencies in Solar Flare Data Sources: Implications for Machine Learning Forecasting", arXiv:2512.13417v3 (June 2026). Already reports: >3,000 flares after 2022 with AR = 0 in the SunPy-HEK GOES list, and recommends not using it (p. 9); the SWPC ×0.7 scaling (Fig. 4); recommends SWPC-FTP labels + definitive SHARPs for AR-based ML with the scaling documented (Section 5, Table 11).
- What they did not do (main text read in full; appendix tables only skimmed): measure the effect of the HEK AR = 0 defect on forecast skill or FAR. Their Section 4 compares SWPC-FTP vs NCEI Science-Quality labels (LSTM + logistic regression, train 2010–2019, test 2020–2024), not HEK.
- Framing: Path A is NOT a discovery of the defect. It is independent confirmation + alarm-level quantification of its effect on FAR. Must cite Hu et al. Our label choices already match their recommendation.

## 8. Pending / next
1. Path A: CIs, phantom list, evidence pack DONE (2ba51d3). Remaining: reconcile 26 vs 20 regions; 2024 zero phantoms; 4 no-HEK-event cases; primary-test-years-only (2021/23/24) version.
2. EUV: 12 s cadence check; synoptic D-CTRL rerun of 3 pilots vs cutouts; url-tar timing; choose source; full-study download.
3. 2025–2026 fresh confirmation set — paused.
4. Optional: R4-honest (region-grouped split).

## 9. Compliance / risks
- Research plan NOT yet written or signed; experiments already run (logged honestly). Must be resolved with sponsor/SRC.
- AI use: Claude Code wrote code; Codex ran an earlier exploratory run and produced some text (disclosed); Claude chat drafted instructions.
- Student must be able to explain every decision without notes.
- IRIS deadline still unknown.
