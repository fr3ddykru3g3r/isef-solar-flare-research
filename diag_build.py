"""DIAGNOSTIC ABLATION ONLY: build labelled variants for dev months (2010-05 .. 2019-12) into data/diag_<name>/,
from cached raw files.  Never writes to the primary data files (build_dataset.py asserts this)."""
import os, subprocess, sys
import pandas as pd
from chunks import months

VARIANTS = {"K_lon45": {"FLARE_SCALE": "K", "LON_LIMIT": "45"},       # validation: must reproduce the K file
            "K2_lon68": {"FLARE_SCALE": "K2", "LON_LIMIT": "68"},     # D3
            "K_lon68": {"FLARE_SCALE": "K", "LON_LIMIT": "68"}}       # D6
for name, env in VARIANTS.items():
    d = f"data/diag_{name}"; os.makedirs(d, exist_ok=True)
    parts = []
    for a, b in months("2010-05-01", "2020-01-01"):
        tag = f"{a}_{b}".replace("-", "")
        out = f"{d}/labelled_{tag}.csv"
        if not os.path.exists(out):
            r = subprocess.run([sys.executable, "build_dataset.py", a, b], capture_output=True, text=True,
                               env={**os.environ, **env, "DIAG_DIR": d})
            assert r.returncode == 0, r.stderr[-1500:]
        p = pd.read_csv(out, low_memory=False)
        if len(p):
            parts.append(p)
    lab = pd.concat(parts, ignore_index=True)
    n = int(lab.duplicated(["harpnum", "t_rec_tai"]).sum())
    lab = lab.drop_duplicates(["harpnum", "t_rec_tai"])                 # month-boundary duplicates (see decisions.md)
    lab.to_csv(f"{d}/labelled_dev.csv", index=False)
    print(f"{name}: {len(lab)} rows ({n} boundary duplicates dropped), positives {int(lab['flared_M1_next_24h'].sum())}")
