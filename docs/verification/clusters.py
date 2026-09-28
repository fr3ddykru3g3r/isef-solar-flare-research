# Inspect the linked-HARP cluster structure of the stored twin pairs
import pandas as pd, collections
import os
D=os.path.join(os.environ.get("ISEF_REPO") or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","..")),"data")
for nm,p in [("2025-26",f"{D}/euv_confirm/twins_le2.csv"),("test",f"{D}/euv_test/f2_replication/twins_test_primary.csv"),("dev",f"{D}/euv_full/step6/twins_PRIMARY.csv")]:
    s=pd.read_csv(p); th=s.true_eid.str.split("_").str[0]; fh=s.false_eid.str.split("_").str[0]
    par={}
    def f(a):
        while par.setdefault(a,a)!=a: a=par[a]
        return a
    for a,b in zip(th,fh): par[f(a)]=f(b)
    sz=collections.Counter(th.map(f)).most_common()
    print(f"{nm}: {len(s)} pairs, {th.nunique()} true HARPs, {fh.nunique()} false HARPs, {len(sz)} clusters; largest cluster sizes (pairs): {[n for _,n in sz[:5]]}")
