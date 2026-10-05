#!/usr/bin/env python3
"""Master Data Acquisition & Download Pipeline for Flare Forecasting Project.

This script coordinates downloading and verifying all data sources required by the project:
  1. NOAA SWPC daily solar event reports (2010-04-29 to 2026-08-17) -> data/swpc_events/
  2. NOAA NCEI GOES XRS 1-minute science data (empty days) -> data/goes_xrs/, data/goes_empty_days.csv
  3. SWAN-SF benchmark dataset archive -> data/swansf/SWAN.tar.gz (Harvard Dataverse)
  4. JSOC HMI SHARP CEA 720s hourly keywords & extra features -> data/raw_sharp_*.csv, data/labelled_*.csv
  5. JSOC EUV FITS Cutouts (AIA 94 A, AIA 1600 A, HMI magnetogram/bitmap):
     - euv_pilot: Exploratory pilot cutouts (data/euv_pilot/)
     - euv_cad: Cadence tests (data/euv_cad/)
     - euv_full: Dev cohort 2010-2019 full study (data/euv_full/)
     - euv_test: Held-out test years 2021, 2023, 2024 (data/euv_test/)
     - euv_confirm: 2025-2026 confirmation set (data/euv_confirm/)
     - euv_extra: Unseen follow-up sets (data/euv_extra/)
  6. Downstream descriptive and sensitivity tables (descriptive_aia94_S*.csv, sensitivity_combined_S*.csv)

Usage:
  python download_all.py --status                      # Audit disk usage and report missing data
  python download_all.py --stage swpc                  # Download NOAA SWPC daily reports
  python download_all.py --stage goes                  # Download GOES XRS netCDF files for empty days
  python download_all.py --stage swansf                # Download SWAN-SF benchmark archive
  python download_all.py --stage sharp                 # Query JSOC SHARP keywords & build labelled tables
  python download_all.py --stage euv-pilot             # Download EUV pilot cutouts
  python download_all.py --stage euv-cad               # Download EUV cadence cutouts
  python download_all.py --stage euv-full              # Download EUV full dev cutouts
  python download_all.py --stage euv-test              # Download EUV held-out test cutouts
  python download_all.py --stage euv-confirm           # Download EUV confirmation cutouts
  python download_all.py --stage euv-extra             # Download EUV extra unseen cutouts
  python download_all.py --stage all-catalogues        # Stages: swpc + goes + swansf
  python download_all.py --stage all-sharp             # Stages: swpc + goes + sharp
  python download_all.py --stage all-euv               # All EUV cutout stages (JSOC export queue)
  python download_all.py --stage all                   # Everything from start to finish
"""

import argparse
import concurrent.futures
from datetime import datetime, timedelta
import glob
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

DEFAULT_EMAIL = "lc09.11146@gmail.com"
SWAN_URL = "https://dataverse.harvard.edu/api/access/datafile/3642432"
SWAN_SIZE = 735206766
SWAN_MD5 = "379da8ba2920a82c81d1c4d3293fc709"

FROZEN_SPEC = "frozen/frozen_spec.json"
SPLIT_FILE = "frozen/split.csv"

SWPC_DIR = "data/swpc_events"
GOES_DIR = "data/goes_xrs"
SWAN_DIR = "data/swansf"
SWAN_FILE = "data/swansf/SWAN.tar.gz"

EUV_DIRS = [
    ("euv_pilot", "data/euv_pilot"),
    ("euv_cad", "data/euv_cad"),
    ("euv_full", "data/euv_full"),
    ("euv_test", "data/euv_test"),
    ("euv_confirm", "data/euv_confirm"),
    ("euv_extra", "data/euv_extra"),
]


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def sha256_file(path):
    if not os.path.exists(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def md5_file(path):
    if not os.path.exists(path):
        return None
    h = hashlib.md5()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def format_bytes(n):
    for u in ["B", "KB", "MB", "GB", "TB"]:
        if abs(n) < 1024.0:
            return f"{n:6.2f} {u}"
        n /= 1024.0
    return f"{n:6.2f} PB"


def get_dir_stats(path, pattern="*"):
    if not os.path.exists(path):
        return 0, 0
    files = glob.glob(os.path.join(path, pattern), recursive=True)
    size = sum(os.path.getsize(p) for p in files if os.path.isfile(p))
    return len(files), size


# ==============================================================================
# STAGE: STATUS & AUDIT
# ==============================================================================
def check_status():
    print("=" * 80)
    print(" DATASET INVENTORY & AUDIT REPORT")
    print("=" * 80)

    # 1. SWPC Reports
    swpc_count, swpc_size = get_dir_stats(SWPC_DIR, "*events.txt")
    missing_file = os.path.join(SWPC_DIR, "_missing_days.txt")
    n_miss = len(open(missing_file).read().split()) if os.path.exists(missing_file) else 0
    swpc_ok = swpc_count >= 5950
    print(f"[1] NOAA SWPC Daily Reports ({SWPC_DIR}):")
    print(f"    - Event reports found : {swpc_count:5d} files ({format_bytes(swpc_size)}) [Expected: ~5955]")
    print(f"    - Recorded 404 days   : {n_miss:5d} days in _missing_days.txt")
    print(f"    - Status              : {'[READY]' if swpc_ok else '[MISSING/INCOMPLETE]'}")

    # 2. GOES XRS
    goes_count, goes_size = get_dir_stats(GOES_DIR, "*.nc")
    goes_csv = os.path.exists("data/goes_empty_days.csv")
    goes_ok = goes_count >= 2680 and goes_csv
    print(f"\n[2] NOAA GOES XRS 1m NetCDF ({GOES_DIR}):")
    print(f"    - NetCDF files        : {goes_count:5d} files ({format_bytes(goes_size)}) [Expected: ~2686]")
    print(f"    - Empty-days CSV      : {'[PRESENT]' if goes_csv else '[MISSING]'} (data/goes_empty_days.csv)")
    print(f"    - Status              : {'[READY]' if goes_ok else '[MISSING/INCOMPLETE]'}")

    # 3. SWAN-SF
    swan_exists = os.path.exists(SWAN_FILE)
    swan_size = os.path.getsize(SWAN_FILE) if swan_exists else 0
    swan_md5_ok = False
    if swan_exists and swan_size == SWAN_SIZE:
        swan_md5_ok = (md5_file(SWAN_FILE) == SWAN_MD5)
    print(f"\n[3] SWAN-SF Benchmark Archive ({SWAN_FILE}):")
    print(f"    - File exists         : {swan_exists}")
    print(f"    - Size                : {format_bytes(swan_size)} (Expected: {format_bytes(SWAN_SIZE)})")
    print(f"    - MD5 Verification    : {'[PASS]' if swan_md5_ok else ('[FAIL - HASH MISMATCH]' if swan_exists else '[MISSING]')}")
    print(f"    - Status              : {'[READY]' if swan_md5_ok else '[MISSING/INCOMPLETE]'}")

    # 4. SHARP Keywords & Labelled Data
    spec = json.load(open(FROZEN_SPEC)) if os.path.exists(FROZEN_SPEC) else {}
    lab1_path = "data/labelled_20100501_20250101.csv"
    lab2_path = "data/labelled_20250101_20260817.csv"
    lab1_sha = sha256_file(lab1_path)
    lab2_sha = sha256_file(lab2_path)
    raw1_count = len(glob.glob("data/raw_sharp_20*.csv"))
    raw_extra_count = len(glob.glob("data/raw_sharp_extra_20*.csv"))

    expected_lab1 = spec.get("data", {}).get("labelled_sha256", "")
    expected_lab2 = "1f6673956db3599616fe4d04fbd14b285a383737156a49d393f6c5d617c49263"
    lab1_ok = (lab1_sha == expected_lab1)
    lab2_ok = (lab2_sha == expected_lab2)

    print(f"\n[4] SHARP CEA 720s Keywords & Flare Labels:")
    print(f"    - Monthly raw chunks  : {raw1_count} files")
    print(f"    - Monthly extra chunks: {raw_extra_count} files")
    print(f"    - Labelled 2010-2024  : {'[VERIFIED MATCH]' if lab1_ok else '[MISSING/MISMATCH]'} ({lab1_path})")
    print(f"    - Labelled 2025-2026  : {'[VERIFIED MATCH]' if lab2_ok else '[MISSING/MISMATCH]'} ({lab2_path})")
    print(f"    - Status              : {'[READY]' if (lab1_ok and lab2_ok) else '[MISSING/INCOMPLETE]'}")

    # 5. EUV FITS Cutouts
    print(f"\n[5] EUV FITS Cutouts (AIA 94 A, AIA 1600 A, HMI):")
    tot_fits = 0
    tot_euv_bytes = 0
    for name, p in EUV_DIRS:
        cnt, sz = get_dir_stats(p, "**/*.fits")
        tot_fits += cnt
        tot_euv_bytes += sz
        print(f"    - {name:15s}     : {cnt:6d} FITS files ({format_bytes(sz)})")
    print(f"    Total EUV FITS files  : {tot_fits:6d} files ({format_bytes(tot_euv_bytes)}) [Expected: ~183,500 files, ~63 GB]")

    # 6. Downstream Post-hoc & Sensitivity Tables
    s_files = ["data/descriptive_aia94_S1.csv", "data/descriptive_aia94_S2.csv", "data/descriptive_aia94_S3.csv",
               "data/sensitivity_combined_S1.csv", "data/sensitivity_combined_S2.csv", "data/sensitivity_combined_S3.csv"]
    s_present = [f for f in s_files if os.path.exists(f)]
    print(f"\n[6] Downstream Analysis & Sensitivity CSVs:")
    print(f"    - Present files       : {len(s_present)} / {len(s_files)}")
    print(f"    - Status              : {'[READY]' if len(s_present) == len(s_files) else '[CAN REGENERATE]'}")

    print("=" * 80)


# ==============================================================================
# STAGE 1: SWPC EVENTS DOWNLOAD
# ==============================================================================
def download_swpc_file(day_str):
    url = f"https://www.ngdc.noaa.gov/stp/space-weather/swpc-products/daily_reports/solar_event_reports/{day_str[:4]}/{int(day_str[4:6]):02d}/{day_str}events.txt"
    dest = os.path.join(SWPC_DIR, f"{day_str}events.txt")
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return "cached", day_str
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SolarFlareResearch/1.0"})
        with urllib.request.urlopen(req, timeout=45) as r:
            data = r.read()
        with open(dest, "wb") as f:
            f.write(data)
        return "ok", day_str
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return "missing", day_str
        return f"error_{e.code}", day_str
    except Exception as e:
        return f"error_{type(e).__name__}", day_str


def stage_swpc(start_date="2010-04-29", end_date="2026-08-17", workers=8):
    log(f"Starting SWPC events download from {start_date} to {end_date} (threads: {workers})...")
    os.makedirs(SWPC_DIR, exist_ok=True)
    cur = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    days = []
    while cur <= end:
        days.append(cur.strftime("%Y%m%d"))
        cur += timedelta(days=1)

    log(f"Total days in range: {len(days)}")
    missing = []
    cached = 0
    downloaded = 0
    errors = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(download_swpc_file, d): d for d in days}
        for i, fut in enumerate(concurrent.futures.as_completed(futures), 1):
            status, d = fut.result()
            if status == "cached":
                cached += 1
            elif status == "ok":
                downloaded += 1
            elif status == "missing":
                missing.append(d)
            else:
                errors += 1
            if i % 500 == 0 or i == len(days):
                log(f"SWPC Progress: {i}/{len(days)} processed (Cached: {cached}, Downloaded: {downloaded}, Missing 404: {len(missing)}, Errors: {errors})")

    missing_path = os.path.join(SWPC_DIR, "_missing_days.txt")
    known = set(open(missing_path).read().split()) if os.path.exists(missing_path) else set()
    all_missing = sorted(known | {f"{d[:4]}-{d[4:6]}-{d[6:8]}" for d in missing})
    with open(missing_path, "w") as f:
        f.write("\n".join(all_missing) + "\n")

    log(f"SWPC events download completed: {downloaded} new, {cached} cached, {len(all_missing)} missing days recorded.")


# ==============================================================================
# STAGE 2: GOES XRS SCIENCE DATA
# ==============================================================================
def stage_goes():
    log("Starting GOES XRS science data download for empty SWPC days...")
    if not os.path.exists(SWPC_DIR):
        sys.exit(f"Error: {SWPC_DIR} does not exist. Run '--stage swpc' first.")
    cmd = [sys.executable, "goes_xrs.py"]
    res = subprocess.run(cmd)
    if res.returncode != 0:
        sys.exit(f"Error: goes_xrs.py failed with code {res.returncode}")
    log("GOES XRS processing complete -> data/goes_empty_days.csv created.")


# ==============================================================================
# STAGE 3: SWAN-SF BENCHMARK ARCHIVE
# ==============================================================================
def stage_swansf():
    log("Starting SWAN-SF benchmark archive download...")
    os.makedirs(SWAN_DIR, exist_ok=True)
    if os.path.exists(SWAN_FILE):
        if os.path.getsize(SWAN_FILE) == SWAN_SIZE:
            log("SWAN.tar.gz exists and has expected size. Verifying MD5 checksum...")
            m = md5_file(SWAN_FILE)
            if m == SWAN_MD5:
                log(f"SWAN.tar.gz is already present and verified ({SWAN_MD5}). Skipping download.")
                return
            else:
                log(f"Hash mismatch ({m} != {SWAN_MD5}). Re-downloading...")
        else:
            log(f"Existing file size ({os.path.getsize(SWAN_FILE)}) != expected ({SWAN_SIZE}). Re-downloading...")

    part_file = SWAN_FILE + ".part"
    log(f"Downloading from {SWAN_URL} -> {SWAN_FILE} ({format_bytes(SWAN_SIZE)})...")
    req = urllib.request.Request(SWAN_URL, headers={"User-Agent": "Mozilla/5.0 (SolarFlareResearch)"})
    with urllib.request.urlopen(req, timeout=120) as resp, open(part_file, "wb") as out:
        downloaded = 0
        t0 = time.time()
        last_log = t0
        while True:
            chunk = resp.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)
            downloaded += len(chunk)
            now = time.time()
            if now - last_log >= 5:
                pct = (downloaded / SWAN_SIZE) * 100 if SWAN_SIZE else 0
                mbps = (downloaded / (now - t0)) / (1024 * 1024)
                log(f"SWAN-SF: {format_bytes(downloaded)} / {format_bytes(SWAN_SIZE)} ({pct:.1f}%) - {mbps:.2f} MB/s")
                last_log = now

    os.replace(part_file, SWAN_FILE)
    log("Download finished. Verifying MD5 checksum...")
    m = md5_file(SWAN_FILE)
    if m == SWAN_MD5:
        log(f"Verification SUCCESS: MD5 {m} matches published benchmark archive.")
    else:
        sys.exit(f"Checksum verification FAILED: expected {SWAN_MD5}, got {m}")


# ==============================================================================
# STAGE 4: SHARP CEA 720s KEYWORDS & LABELS
# ==============================================================================
def stage_sharp():
    log("Starting SHARP CEA 720s keyword query & label build...")
    # Step A: 2010 to 2025 chunks
    log("Step 4a: Running run_all.py for dev/test periods (2010-05-01 -> 2025-01-01)...")
    r1 = subprocess.run([sys.executable, "run_all.py", "2010-05-01", "2025-01-01"])
    if r1.returncode != 0:
        sys.exit(f"run_all.py failed with return code {r1.returncode}")

    log("Step 4b: Running fetch_extra.py for extra Bobra parameters (2010-05-01 -> 2025-01-01)...")
    r2 = subprocess.run([sys.executable, "fetch_extra.py", "2010-05-01", "2025-01-01"])
    if r2.returncode != 0:
        sys.exit(f"fetch_extra.py failed with return code {r2.returncode}")

    # Step B: Confirmation period 2025-01-01 to 2026-08-17
    log("Step 4c: Fetching confirmation period (2025-01-01 -> 2026-08-17)...")
    env = os.environ.copy()
    env["JSOC_END_OVERRIDE"] = "2026-08-17|2026.08.16_23:00_TAI"

    log("Building confirmation SHARP keywords and labels...")
    r3 = subprocess.run([sys.executable, "build_dataset.py", "2025-01-01", "2026-08-17"], env=env)
    if r3.returncode != 0:
        sys.exit(f"build_dataset.py for confirmation failed with code {r3.returncode}")

    r4 = subprocess.run([sys.executable, "fetch_extra.py", "2025-01-01", "2026-08-17"], env=env)
    if r4.returncode != 0:
        sys.exit(f"fetch_extra.py for confirmation failed with code {r4.returncode}")

    log("SHARP keywords & labelled tables build completed successfully.")


# ==============================================================================
# STAGE 5-10: EUV FITS CUTOUTS (JSOC DRMS EXPORTS)
# ==============================================================================
def stage_euv(substage="all", email=DEFAULT_EMAIL):
    log(f"Starting EUV Cutouts acquisition (Substage: {substage}, Email: {email})...")
    log("NOTE: Stanford JSOC permits 1 pending export request per registered email address.")
    log("Export jobs are submitted, queued, processed on Stanford's cluster, and streamed into data/.")

    env = os.environ.copy()
    env["EMAIL"] = email

    if substage in ("pilot", "all"):
        log("\n--- EUV Pilot Cutouts (euv_download.py all) ---")
        subprocess.run([sys.executable, "euv_download.py", "all"], env=env, check=True)

    if substage in ("cad", "all"):
        log("\n--- EUV Cadence Cutouts (euv_cad.py) ---")
        if not os.path.exists("data/euv_cad/alarms.csv"):
            subprocess.run([sys.executable, "euv_cad.py", "select"], env=env, check=True)
        subprocess.run([sys.executable, "euv_cad.py", "cutouts"], env=env, check=True)

    if substage in ("full", "all"):
        log("\n--- EUV Full Dev Set (euv_full.py run) ---")
        subprocess.run([sys.executable, "euv_full.py", "run"], env=env, check=True)

    if substage in ("test", "all"):
        log("\n--- EUV Held-Out Test Set (euv_test_download.py run) ---")
        subprocess.run([sys.executable, "euv_test_download.py", "run"], env=env, check=True)

    if substage in ("confirm", "all"):
        log("\n--- EUV Confirmation Set (euv_confirm.py download) ---")
        subprocess.run([sys.executable, "euv_confirm.py", "download"], env=env, check=True)

    if substage in ("extra", "all"):
        log("\n--- EUV Extra Unseen Sets (euv_extra.py download) ---")
        subprocess.run([sys.executable, "euv_extra.py", "download"], env=env, check=True)

    log("EUV cutout acquisition step completed.")


# ==============================================================================
# STAGE: DOWNSTREAM TABLES
# ==============================================================================
def stage_derived():
    log("Generating downstream descriptive and sensitivity tables...")
    if os.path.exists("descriptive_aia94.py"):
        log("Running descriptive_aia94.py...")
        subprocess.run([sys.executable, "descriptive_aia94.py"], check=True)
    if os.path.exists("sensitivity_combined.py"):
        log("Running sensitivity_combined.py...")
        subprocess.run([sys.executable, "sensitivity_combined.py"], check=True)
    log("Downstream tables generated successfully.")


# ==============================================================================
# MAIN ENTRYPOINT
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(
        description="Master download and data synchronization pipeline for solar flare forecasting data.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Audit current disk usage, inspect all data folders, and report missing components.",
    )
    parser.add_argument(
        "--stage",
        choices=[
            "swpc",
            "goes",
            "swansf",
            "sharp",
            "euv-pilot",
            "euv-cad",
            "euv-full",
            "euv-test",
            "euv-confirm",
            "euv-extra",
            "all-catalogues",
            "all-sharp",
            "all-euv",
            "derived",
            "all",
        ],
        help="Which download stage to execute.",
    )
    parser.add_argument(
        "--email",
        default=DEFAULT_EMAIL,
        help=f"Registered JSOC DRMS email address for exports (default: {DEFAULT_EMAIL}).",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=8,
        help="Number of concurrent worker threads for parallel HTTP downloads (default: 8).",
    )
    parser.add_argument(
        "--start",
        default="2010-04-29",
        help="Start date for SWPC/SHARP downloads (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--end",
        default="2026-08-17",
        help="End date for SWPC/SHARP downloads (YYYY-MM-DD).",
    )

    args = parser.parse_args()

    if len(sys.argv) == 1 or args.status:
        check_status()
        if len(sys.argv) == 1:
            print("\nTip: Run 'python download_all.py --help' to view available download stages.")
        return

    st = args.stage
    if st == "swpc":
        stage_swpc(args.start, args.end, workers=args.workers)
    elif st == "goes":
        stage_goes()
    elif st == "swansf":
        stage_swansf()
    elif st == "sharp":
        stage_sharp()
    elif st == "euv-pilot":
        stage_euv("pilot", email=args.email)
    elif st == "euv-cad":
        stage_euv("cad", email=args.email)
    elif st == "euv-full":
        stage_euv("full", email=args.email)
    elif st == "euv-test":
        stage_euv("test", email=args.email)
    elif st == "euv-confirm":
        stage_euv("confirm", email=args.email)
    elif st == "euv-extra":
        stage_euv("extra", email=args.email)
    elif st == "all-catalogues":
        stage_swpc(args.start, args.end, workers=args.workers)
        stage_goes()
        stage_swansf()
    elif st == "all-sharp":
        stage_swpc(args.start, args.end, workers=args.workers)
        stage_goes()
        stage_sharp()
    elif st == "all-euv":
        stage_euv("all", email=args.email)
    elif st == "derived":
        stage_derived()
    elif st == "all":
        log("Executing FULL DATASET DOWNLOAD (all stages)...")
        stage_swpc(args.start, args.end, workers=args.workers)
        stage_goes()
        stage_swansf()
        stage_sharp()
        stage_euv("all", email=args.email)
        stage_derived()
        log("ALL STAGES COMPLETED. Running final status check:")
        check_status()


if __name__ == "__main__":
    main()
