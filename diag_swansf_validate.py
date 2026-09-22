"""Validation (pre-registered, decisions.md 2026-09-22): cgem.lorentz (masked R4a, all-pixel R4b) vs SWAN-SF for the
D7 records, matched on HARPNUM + T_REC. PASS per parameter: Spearman rho >= 0.95 AND median |rel diff| <= 10%.
rel diff = (cgem - swan) / |swan|; cgem TOTFZ is in 1e20 dyne -> converted to dyne (SWAN-SF units)."""
import glob, tarfile, sys
import numpy as np, pandas as pd
from scipy.stats import spearmanr

TAR = "data/swansf/SWAN.tar.gz"
cg = pd.read_csv("data/diag/d7_cgem_lorentz.csv").dropna(subset=["T_REC"])
cg["key"] = cg.T_REC.str.replace("_TAI", "").str.replace("_", " ").str.replace(".", "-", n=2, regex=False)
want = set(cg.HARPNUM.astype(int))
rows = []
with tarfile.open(TAR) as tf:
    for m in tf:
        name = m.name.rsplit("/", 1)[-1]
        if m.isfile() and name.endswith(".csv") and name[:-4].isdigit() and int(name[:-4]) in want:
            d = pd.read_csv(tf.extractfile(m), sep="\t", usecols=["Timestamp", "TOTBSQ", "TOTFZ", "EPSZ"])
            rows.append(d.assign(HARPNUM=int(name[:-4]), part=m.name.split("/")[-2]))
sw = pd.concat(rows, ignore_index=True).drop_duplicates(["HARPNUM", "Timestamp"])
m = cg.merge(sw, left_on=["HARPNUM", "key"], right_on=["HARPNUM", "Timestamp"], suffixes=("", "_swan"))
print(f"D7 records with cgem values {len(cg)}; HARPs found in SWAN-SF {sw.HARPNUM.nunique()} of {len(want)}; matched records {len(m)}")
out = []
for var, sfx in [("R4a masked", "1"), ("R4b all-pixel", "")]:
    for p in ["TOTBSQ", "TOTFZ", "EPSZ"]:
        a = m[p + sfx] * (1e20 if p == "TOTFZ" else 1.0); b = m[p + "_swan"]
        ok = a.notna() & b.notna() & (b != 0)
        rho = spearmanr(a[ok], b[ok]).statistic
        rel = np.median(np.abs((a[ok] - b[ok]) / b[ok].abs()))
        out.append(dict(variant=var, param=p, n=int(ok.sum()), spearman=round(rho, 4), median_abs_rel_diff=round(rel, 4),
                        median_ratio_cgem_over_swan=round(float(np.median(a[ok] / b[ok])), 4),
                        PASS=bool(rho >= 0.95 and rel <= 0.10)))
t = pd.DataFrame(out); t.to_csv("data/diag/swansf_validation.csv", index=False)
print(t.to_string(index=False))
