"""cgem.lorentz keywords for the D7 sample records (keyword queries only; resumable per HARP).
Fetched for SWAN-SF validation; used in models only after the user's OK (R4a masked primary, R4b all-pixel)."""
import os, time
from concurrent.futures import ThreadPoolExecutor
import pandas as pd, drms

KEYS = "HARPNUM,T_REC,TOTBSQ,TOTFZ,EPSZ,TOTBSQ1,TOTFZ1,EPSZ1,MASKNAME,MASKTHRS"
OUT = "data/diag/d7_cgem_lorentz.csv"
s = pd.read_csv("data/diag/d7_sample_records.csv").drop_duplicates(["harpnum", "t_rec"])
have = set(pd.read_csv(OUT).HARPNUM) if os.path.exists(OUT) else set()


def one(hg):
    h, g = hg
    for k in range(6):
        try:
            r = drms.Client().query(f"cgem.lorentz[{h}][{','.join(g.t_rec)}]", key=KEYS)
            return r if len(r) else pd.DataFrame([{"HARPNUM": h}])  # marks HARP as queried even if no rows
        except Exception as err:
            print(f"HARP {h} retry {k + 1}: {err!r}", flush=True); time.sleep(20)
    raise RuntimeError(h)


todo = [(h, g) for h, g in s.groupby("harpnum") if h not in have]
with ThreadPoolExecutor(6) as ex:                      # keyword queries: not subject to the 1-pending-export limit
    for r in ex.map(one, todo):                        # only this thread writes the CSV
        r.to_csv(OUT, mode="a", header=not os.path.exists(OUT), index=False)
d = pd.read_csv(OUT).dropna(subset=["T_REC"])
m = s.merge(d, left_on=["harpnum", "t_rec"], right_on=["HARPNUM", "T_REC"], how="left")
print(f"D7 distinct records {len(s)}; found in cgem.lorentz {m.T_REC.notna().sum()}; "
      f"all 6 values present {m[['TOTBSQ','TOTFZ','EPSZ','TOTBSQ1','TOTFZ1','EPSZ1']].notna().all(axis=1).sum()}")
print("MASKTHRS values:", d.MASKTHRS.value_counts().to_dict(), "MASKNAME:", d.MASKNAME.value_counts().to_dict())
