# Same Magnetic Field, Different Fate
### Resolving False Alarms in Solar Flare Forecasting via High-Temperature Coronal Restlessness

[![Data Audit](https://img.shields.io/badge/Data_Audit-75K_Files_Verified-success.svg)](#data-acquisition--inventory)
[![Pre-registration](https://img.shields.io/badge/Pre--registered-2025--26_Confirmation-blue.svg)](docs/RESULTS_SUMMARY.md)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](#license)

**Authors:** Kyros Goyal & Lokesh Chaudhary  
**Affiliation:** International Science and Engineering Fair (ISEF) Research  
**Repository:** [github.com/fr3ddykru3g3r/isef-solar-flare-research](https://github.com/fr3ddykru3g3r/isef-solar-flare-research)

---

## Table of Contents
1. [Executive Summary & Core Question](#executive-summary--core-question)
2. [Key Scientific Findings](#key-scientific-findings)
3. [Repository Architecture](#repository-architecture)
4. [Data Acquisition & Master Download Script](#data-acquisition--master-download-script)
5. [Step-by-Step Pipeline & Reproduction](#step-by-step-pipeline--reproduction)
6. [Pre-registration & Research Integrity](#pre-registration--research-integrity)
7. [Verification & Auditing](#verification--auditing)
8. [License & Acknowledgements](#license--acknowledgements)

---

## Executive Summary & Core Question

### The Operational Problem
State-of-the-art solar flare forecasters rely on photospheric vector magnetic field parameters (SDO/HMI SHARP) fed into machine learning classifiers (e.g., Support Vector Machines, Bobra & Couvidat 2015). While these models achieve high True Skill Statistics (TSS $\approx 0.73$), **TSS is base-rate insensitive**. 

Because major solar flares ($\ge \text{M1.0}$) are rare ($\approx 2\text{--}3\%$ base rate), operational forecasts suffer from extreme false-alarm rates: **6 out of every 7 operational alarms are false** (268 of 313 alarm episodes in held-out test years 2021–2024 were false positives).

```
   Photospheric Magnetic Field (HMI SHARP)
                     │
                     ▼
          ┌─────────────────────┐
          │ Frozen SVM Gate     │  TSS = 0.728
          │ Threshold = -0.9925 │  Catches 87% of flaring regions
          └──────────┬──────────┘
                     │
          ┌──────────┴──────────┐
          ▼                     ▼
     True Alarms           False Alarms
       (14%)                  (86%)
      45 episodes          268 episodes
          │                     │
          └──────────┬──────────┘
                     ▼
       "Magnetic Twin" Conditioning
   (Matched on identical magnetic score)
                     │
                     ▼
      SDO/AIA 94 Å Coronal Restlessness
                 (CV_box)
```

### The Central Question
When two solar active regions present nearly identical photospheric magnetic fields and receive the exact same danger score from a frozen magnetic model, **what determines why one erupts into an M1+ flare while the other remains quiet?**

### The Solution: "Magnetic Twins" & High-Temperature Coronal Restlessness
1. **The Twin Design:** For each true alarm episode, we select a "magnetic twin" — a false alarm from a different active region whose frozen magnetic gate score was nearly identical ($\pm 0.0747$, within $0.2 \times \text{SD}$).
2. **Coronal Restlessness ($CV_{\text{box}}$):** We measure high-temperature plasma variability in the 24 hours preceding each alarm using SDO/AIA 94 Å extreme ultraviolet imagery ($\text{Fe XVIII}$, $\approx 6\text{--}7\text{ MK}$):
   $$\text{CV}_{\text{box}} = \frac{\text{SD}(\text{brightness} - \text{linear trend})}{\text{mean brightness}}$$
3. **Hypothesis:** Flaring regions exhibit elevated pre-flare thermal fluctuation and reconnection in the corona that cannot be measured from the photosphere alone.

---

## Key Scientific Findings

### 1. Pre-registered 2025–2026 Confirmation Test
In a confirmatory test on unseen 2025–2026 data—pre-registered before downloading or inspecting flare labels—the flaring twin was more restless in **39 of 50 pairs** (78% binomial sign test $p = 9.0 \times 10^{-5}$):
- **Median Restlessness Ratio:** **3.26** (the flaring region's hot corona was $3.3\times$ more restless than its matched magnetic twin).
- **Pre-registered 95% Confidence Interval:** **[1.30, 9.49]** (2,000 resamples by flaring region).
- **Two-way Region Resample (Sensitivity):** **[0.86, 12.23]** (accounting for active region reuse across pairs; 14 of 18 flaring regions were more restless in the majority of their pairs).

### 2. Operational Alert Tiers (WARNING vs. WATCH)
Coronal restlessness **cannot act as an unconditional veto filter** because $1$ in $4$ true alarms was calm ($\approx 27\%$ calm flarers). A hard cut-off removes false alarms but loses too many true flares.

Instead, conditioning on $CV_{\text{box}}$ enables **Operational Alert Tiering**:
- **WARNING Tier:** Top quartile of $CV_{\text{box}}$ $\rightarrow$ **26%–32%** flare follow-up rate.
- **WATCH Tier:** Lower $CV_{\text{box}}$ $\rightarrow$ **2%–8%** flare follow-up rate.
- **NO ALERT:** Sub-threshold $\rightarrow$ **4%** baseline.

The WARNING tier is **$3.4\times$ to $15.3\times$** more dangerous than the WATCH tier despite identical magnetic classification.

### 3. Solar Catalogue Defects Discovered & Quantified
- **HEK Active Region Drop:** Discovered that the standard HEK flare catalogue drops active region numbers ($\text{ar\_noaanum} = 0$) for 173 of 195 M1+ flares in 2022. Scoring against HEK inflates the false-alarm ratio from 0.543 to 0.724 and creates 34 phantom false alarms. All labels were rebuilt from original NOAA SWPC daily text reports.
- **True-Flux Harmonization (K2 Scale):** Corrected NOAA SWPC's historical $0.7\times$ scaling on GOES-13/14/15 operational fluxes by converting to the true physical irradiance scale ($\div 0.7$), altering the flare class of 4,170 events.

---

## Repository Architecture

```
.
├── download_all.py                # Unified master acquisition & verification pipeline
├── build_dataset.py               # HMI SHARP CEA keyword query & label synthesis
├── run_all.py                     # Resumable monthly chunk runner for 2010–2025
├── fetch_extra.py                 # Query extra Bobra & Couvidat (2015) features
├── swpc.py                        # NOAA SWPC daily event report scraper & parser
├── goes_xrs.py                    # 1-minute GOES XRS science NetCDF flux processing
├── cohort.py                      # Active region episode construction & eligibility rules
├── stage2_gate.py                 # Train & freeze primary RBF SVM magnetic gate
├── stage3_cohort.py               # Dev cohort episode extraction & eligibility cuts
├── stage4_models.py               # Internal 5-fold cross-validation on dev period
├── stage5_test.py                 # Held-out evaluation on 2021, 2023, 2024 test cohort
├── euv_download.py                # EUV pilot cutouts download & manifest verification
├── euv_cad.py                     # EUV cadence & subsampling experiments
├── euv_full.py                    # EUV dev 2010–2019 full study processing pipeline
├── euv_test_download.py           # Held-out 2021/23/24 EUV cutout download
├── euv_confirm.py                 # 2025–2026 confirmation cohort download & computation
├── euv_extra.py                   # Unseen follow-up validation sets (primary + 2022)
├── euv_confirm_tests.py           # Execution of pre-registered confirmation tests
├── descriptive_aia94.py           # Alert tiers, noise audit, calm-flarer profiling
├── sensitivity_combined.py        # Spike filtering (V0/V1/V2) & twin sensitivity matrix
├── decisions.md                   # Append-only chronological research decision log (5,600+ lines)
├── frozen/
│   ├── frozen_spec.json           # Frozen model parameters, thresholds, and SHA-256 hashes
│   └── split.csv                  # Frozen HARP assignment (dev 2010–19 vs test 2021–24)
├── figures/                       # Scientific figures, trade-off curves, and diagnostic plots
├── verification/                  # Independent statistical verification & bootstrap audits
└── docs/
    ├── DATA_ACQUISITION.md        # Comprehensive data architecture & reproduction guide
    ├── MODEL_REPORT.md            # Complete model specifications & performance tables
    ├── RESULTS_SUMMARY.md         # Full results hierarchy A–F with exact numbers & CIs
    ├── TEAM_UNDERSTANDING.md      # Quiz-style conceptual mastery & defense guide
    └── AI_USE_LOG.md              # Transparent log of AI assistance and idea provenance
```

---

## Data Acquisition & Master Download Script

The project uses approximately **80 GB** of multi-instrument astronomical data across 184,000 files. All downloads are orchestrated through the master pipeline script: [`download_all.py`](download_all.py).

### Quick Status Audit
Inspect existing local files, verify file counts, disk usage, and cryptographic checksums:
```bash
python3 download_all.py --status
```

### Staged Downloads
All downloads are **strictly resumable** — existing, verified files are never re-downloaded:

```bash
# 1. NOAA SWPC Daily Reports (2010-04-29 to 2026-08-17)
python3 download_all.py --stage swpc --workers 8

# 2. NOAA GOES XRS 1m NetCDF files for empty SWPC days
python3 download_all.py --stage goes

# 3. SWAN-SF Benchmark Archive (Harvard Dataverse, MD5: 379da8ba2920a82c81d1c4d3293fc709)
python3 download_all.py --stage swansf

# 4. HMI SHARP CEA 720s Keywords & Flare Labels (2010–2026)
python3 download_all.py --stage sharp

# 5. EUV FITS Cutouts (Stanford JSOC DRMS Export Queues)
python3 download_all.py --stage euv-pilot       # Exploratory pilot cutouts
python3 download_all.py --stage euv-cad         # Cadence test cutouts
python3 download_all.py --stage euv-full        # Dev cohort (2010-2019) cutouts
python3 download_all.py --stage euv-test        # Held-out test cohort (2021, 2023, 2024)
python3 download_all.py --stage euv-confirm     # 2025-2026 confirmation cohort
python3 download_all.py --stage euv-extra       # Extra unseen follow-up cohorts

# 6. Rebuild Downstream Post-Hoc & Sensitivity CSVs
python3 download_all.py --stage derived
```

### Combined Downloads
```bash
# Download all external catalogues (SWPC + GOES + SWAN-SF):
python3 download_all.py --stage all-catalogues

# Download all tabular/keyword datasets:
python3 download_all.py --stage all-sharp

# Download all EUV FITS image sets:
python3 download_all.py --stage all-euv

# Download EVERYTHING from scratch:
python3 download_all.py --stage all
```

> [!IMPORTANT]
> **Stanford JSOC DRMS Rate Limits:**  
> Exporting SDO/AIA and SDO/HMI tracked cutouts (`im_patch`) requires Stanford cluster compute time. JSOC enforces a limit of **1 active pending export request per registered email address**. The script automatically handles polling, queuing, exponential backoff, and tarball extraction using `--email lc09.11146@gmail.com` (configurable with `--email your_email@domain.com`). See [`docs/DATA_ACQUISITION.md`](docs/DATA_ACQUISITION.md) for full details.

---

## Step-by-Step Pipeline & Reproduction

### 1. Environment Installation
Requirements: Python 3.10–3.13 with scientific libraries.
```bash
pip install numpy scipy pandas astropy sunpy drms xarray scikit-learn joblib
```

### 2. Feature Extraction & Label Synthesis
Extract hourly SHARP CEA parameters and join with SWPC flare labels under the true-irradiance scale ($K2$):
```bash
# Monthly chunking across development and test years
python3 run_all.py 2010-05-01 2025-01-01
python3 fetch_extra.py 2010-05-01 2025-01-01

# Confirmation period (frozen end: 2026.08.16_23:00_TAI)
JSOC_END_OVERRIDE="2026-08-17|2026.08.16_23:00_TAI" python3 build_dataset.py 2025-01-01 2026-08-17
JSOC_END_OVERRIDE="2026-08-17|2026.08.16_23:00_TAI" python3 fetch_extra.py 2025-01-01 2026-08-17
```

### 3. Magnetic Gate Training & Cohort Formation
Train the RBF Support Vector Machine on dev active regions (2010–2019) and freeze decision thresholds:
```bash
# Stage 2: Train 5-fold grouped SVM gate and freeze threshold (-0.9925)
python3 stage2_gate.py

# Stage 3: Extract dev cohort episodes and filter eligibility
python3 stage3_cohort.py
```

### 4. Held-Out Evaluation (2021, 2023, 2024)
Evaluate the frozen gate and magnetic evolution models on untouched test years:
```bash
python3 stage5_test.py
```

### 5. Coronal Restlessness & Confirmation Testing
Compute coronal variability ($CV_{\text{box}}$) and evaluate magnetic twins on the 2025–2026 confirmation set:
```bash
# Run confirmation evaluation
python3 euv_confirm_tests.py

# Rebuild alert tiers, calm-flarer profiles, and sensitivity matrices
python3 descriptive_aia94.py
python3 sensitivity_combined.py
```

---

## Pre-registration & Research Integrity

All primary tests and methodological changes in this project followed strict pre-registration protocols to prevent p-hacking and HARKing:
- **Append-Only Decision Log ([`decisions.md`](decisions.md)):** Every research question, hypothesis, sampling rule, threshold, and feature set was committed to git **before** test years were unlocked or labels were joined.
- **Frozen Models & Splits ([`frozen/`](frozen/)):** Cross-validation splits, SVM weights, and scaling parameters are stored with SHA-256 hashes in [`frozen/frozen_spec.json`](frozen/frozen_spec.json).
- **Run-Once Discipline:** Confirmatory tests on 2021–2024 and 2025–2026 data were run exactly once without hyperparameter tuning or threshold post-selection.
- **Negative Results Documented:** Disproved hypotheses are reported with equal prominence (e.g., photospheric magnetic evolution slopes $\Delta \text{USFLUX}/\Delta t$ provided zero added value over the static gate score, $\Delta \text{log-loss} = -0.0051$, $95\%\text{ CI: } [-0.0201, +0.0094]$).

---

## Verification & Auditing

The repository includes an independent verification suite to audit all claims, tables, and bootstrap intervals:
```bash
python3 verify_facts.py
python3 verification/evaluate.py
```

Key audited benchmarks:
- **Gate Test TSS:** $0.728 \pm 0.048$ (region level), $0.547 \pm 0.063$ (hour level).
- **Confirmed Twin Restlessness Ratio:** $3.262$ (95% CI: $1.296 \text{--} 9.489$, 39/50 pairs).
- **Flare-Frames-Excluded Sensitivity ($V1$):** $2.73$ (95% CI: $1.10 \text{--} 6.20$, 34/47 pairs).
- **Labelled Dataset Cryptographic Integrity:**
  - `data/labelled_20100501_20250101.csv`: `62a0e4ccffe8b1fc4dacd2a0ba80570bf56018540d57367c16eb37337380ffeb`
  - `data/labelled_20250101_20260817.csv`: `1f6673956db3599616fe4d04fbd14b285a383737156a49d393f6c5d617c49263`

---

## License & Acknowledgements

### Data Sources & Services
- **SDO/HMI and SDO/AIA:** Data courtesy of NASA/SDO and the AIA and HMI science teams, retrieved via Stanford University's Joint Science Operations Center (JSOC).
- **NOAA SWPC & NCEI:** Solar event reports and GOES XRS 1-minute science data courtesy of the National Oceanic and Atmospheric Administration and National Centers for Environmental Information.
- **SWAN-SF:** Benchmark dataset courtesy of Angryk et al. (2020), hosted on Harvard Dataverse.

### License
This repository is open-sourced under the MIT License. See [LICENSE](LICENSE) for details.
