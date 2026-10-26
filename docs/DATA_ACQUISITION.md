# Data Acquisition & Download Guide

This document specifies the exact sources, download mechanisms, rate limits, checksums, and restoration procedures for all datasets used in this repository (~80 GB, ~184,000 files).

The master pipeline script is [download_all.py](file:///Volumes/09/Isef%20fuck%20me%20hard/isef%20new/download_all.py).

---

## 1. Dataset Overview & Inventory

| Dataset | Location | Count / Size | Source / Protocol | Verification |
|---|---|---|---|---|
| **NOAA SWPC Daily Reports** | `data/swpc_events/` | ~5,955 `.txt` files (12.7 MB) | NOAA NCEI HTTP (`solar_event_reports/`) | `_missing_days.txt` (404 log) |
| **NOAA GOES XRS 1m NetCDF** | `data/goes_xrs/` | 2,686 `.nc` files (598 MB) | NOAA NCEI Science Data (GOES 13–19) | [goes_xrs.py](file:///Volumes/09/Isef%20fuck%20me%20hard/isef%20new/goes_xrs.py) |
| **SWAN-SF Benchmark** | `data/swansf/SWAN.tar.gz` | 1 archive (701.15 MB) | Harvard Dataverse (file 3642432) | MD5: `379da8ba2920a82c81d1c4d3293fc709` |
| **SHARP CEA 720s Keywords** | `data/raw_sharp_*.csv` | 199 monthly chunks | Stanford JSOC DRMS (`hmi.sharp_cea_720s`) | Deduped key: `(HARPNUM, T_REC)` |
| **SHARP Extra Parameters** | `data/raw_sharp_extra_*.csv` | 196 monthly chunks | Stanford JSOC DRMS (Bobra & Couvidat 2015) | 1:1 merge validation |
| **Labelled Primary Dataset** | `data/labelled_20100501_20250101.csv` | 254,899 rows (103 MB) | Generated via [build_dataset.py](file:///Volumes/09/Isef%20fuck%20me%20hard/isef%20new/build_dataset.py) | SHA-256: `62a0e4ccffe8b1fc4dacd2a0ba80570bf56018540d57367c16eb37337380ffeb` |
| **Labelled Confirmation** | `data/labelled_20250101_20260817.csv` | 50,227 rows (20 MB) | Generated via [build_dataset.py](file:///Volumes/09/Isef%20fuck%20me%20hard/isef%20new/build_dataset.py) | SHA-256: `1f6673956db3599616fe4d04fbd14b285a383737156a49d393f6c5d617c49263` |
| **EUV Pilot Cutouts** | `data/euv_pilot/` | 6,835 FITS (1.56 GB) | Stanford JSOC DRMS exports | `manifest.csv` SHA-256 |
| **EUV Cadence Cutouts** | `data/euv_cad/` | 19,641 FITS (4.74 GB) | Stanford JSOC DRMS exports | `run.log`, `source_decision.csv` |
| **EUV Full Dev Set** | `data/euv_full/` | 55,500 FITS (13.80 GB) | Stanford JSOC DRMS exports | `exports.csv`, `verify_per_harp.csv` |
| **EUV Held-Out Test Set** | `data/euv_test/` | 32,257 FITS (11.52 GB) | Stanford JSOC DRMS exports | `verify_per_harp.csv` |
| **EUV Confirmation Set** | `data/euv_confirm/` | 35,639 FITS (14.85 GB) | Stanford JSOC DRMS exports | `verify_per_harp.csv` |
| **EUV Extra Unseen Sets** | `data/euv_extra/` | 33,613 FITS (16.71 GB) | Stanford JSOC DRMS exports | `manifest.csv` |

---

## 2. Using `download_all.py`

### Check Status & Audit Existing Files
```bash
python download_all.py --status
```
Scans all directories, counts files, verifies checksums for frozen files and benchmark archives, and prints whether each component is `[READY]` or `[MISSING/INCOMPLETE]`.

### Stage 1: NOAA SWPC Event Reports
```bash
python download_all.py --stage swpc --workers 8
```
- Fetches daily text reports from NOAA NCEI (`https://www.ngdc.noaa.gov/stp/space-weather/swpc-products/daily_reports/solar_event_reports/`).
- Multithreaded, checks existing files, records 404 days in `data/swpc_events/_missing_days.txt`.

### Stage 2: NOAA GOES XRS 1-Minute Science NetCDF
```bash
python download_all.py --stage goes
```
- Reads empty days from `data/swpc_events/`.
- Downloads 1-minute science data from primary and secondary GOES satellites across 2010–2026.
- Classifies peak flux and produces `data/goes_empty_days.csv`.

### Stage 3: SWAN-SF Benchmark Archive
```bash
python download_all.py --stage swansf
```
- Streams `SWAN.tar.gz` (701.15 MB) from Harvard Dataverse (file 3642432).
- Verifies MD5 checksum `379da8ba2920a82c81d1c4d3293fc709` against published ground truth.

### Stage 4: SHARP CEA 720s Keywords & Labelled Data
```bash
python download_all.py --stage sharp
```
- Runs [run_all.py](file:///Volumes/09/Isef%20fuck%20me%20hard/isef%20new/run_all.py) (2010-05-01 to 2025-01-01) in monthly chunks with automatic retry logic against JSOC timeouts.
- Runs [fetch_extra.py](file:///Volumes/09/Isef%20fuck%20me%20hard/isef%20new/fetch_extra.py) to fetch Bobra & Couvidat extra parameters.
- Runs confirmation chunk with override `JSOC_END_OVERRIDE="2026-08-17|2026.08.16_23:00_TAI"`.
- Reconstructs `data/labelled_20100501_20250101.csv` and `data/labelled_20250101_20260817.csv`.

### Stage 5: EUV FITS Cutouts (JSOC DRMS Export Queues)
Because EUV cutouts total ~63 GB and ~183,500 files, they are separated into individual stages:
```bash
# Pilot cutouts
python download_all.py --stage euv-pilot

# Cadence test cutouts
python download_all.py --stage euv-cad

# Dev 2010-2019 full study cutouts
python download_all.py --stage euv-full

# Held-out 2021, 2023, 2024 test cutouts
python download_all.py --stage euv-test

# 2025-2026 confirmation cutouts
python download_all.py --stage euv-confirm

# Extra unseen follow-up cutouts (primary + 2022)
python download_all.py --stage euv-extra

# Or all EUV stages sequentially:
python download_all.py --stage all-euv
```

> [!IMPORTANT]
> **JSOC Rate Limits & Queues:**
> Stanford's JSOC export system restricts each registered email address to **at most 1 active pending export request**.
> The download scripts automatically wait for each batch export to be processed on Stanford's cluster, unpack the FITS cutouts into `data/`, and then submit the next active region.
> Default email is `lc09.11146@gmail.com`. You can override it with `--email your_email@example.com`.

### Stage 6: Downstream Descriptive & Sensitivity Tables
```bash
python download_all.py --stage derived
```
- Re-runs [descriptive_aia94.py](file:///Volumes/09/Isef%20fuck%20me%20hard/isef%20new/descriptive_aia94.py) -> produces `data/descriptive_aia94_S1.csv`, `S2.csv`, `S3.csv`, and `figures/alert_tiers.png`.
- Re-runs [sensitivity_combined.py](file:///Volumes/09/Isef%20fuck%20me%20hard/isef%20new/sensitivity_combined.py) -> produces `data/sensitivity_combined_S1.csv`, `S2.csv`, `S3.csv`, `cells.csv`, and `figures/sensitivity_combined.png`.

---

## 3. Full Download Command
To run all stages sequentially from start to finish:
```bash
python download_all.py --stage all
```
The script is fully resumable: any chunk, daily report, or FITS cutout already downloaded and verified on disk is automatically skipped.
