"""D7 vector-segment cost estimate (diagnostic; metadata only, no downloads).
Segment dims for every D7 sample record via jsoc_info rs_list; exact file sizes for a random sample via HTTP HEAD."""
import json, os, time, urllib.parse, urllib.request
import numpy as np, pandas as pd

SEGS = ["Br", "Bp", "Bt", "bitmap", "conf_disambig"]
URL = "http://jsoc.stanford.edu/cgi-bin/ajax/jsoc_info?op=rs_list&ds={ds}&key=T_REC&seg=" + ",".join(SEGS)
s = pd.read_csv("data/diag/d7_sample_records.csv").drop_duplicates(["harpnum", "t_rec"])


def get(url, method="GET"):
    for k in range(6):                                  # JSOC metadata calls time out now and then
        try:
            return urllib.request.urlopen(urllib.request.Request(url, method=method), timeout=120)
        except (TimeoutError, OSError) as err:
            print(f"retry {k + 1}: {err!r}", flush=True); time.sleep(20)
    raise RuntimeError(url)


CACHE = "data/diag/d7_vector_dims_cache.jsonl"          # resumable: one JSON line per HARP
done = {json.loads(L)["h"]: json.loads(L)["d"] for L in open(CACHE)} if os.path.exists(CACHE) else {}
rows = []
for h, g in s.groupby("harpnum"):
    ds = f"hmi.sharp_cea_720s[{h}][{','.join(g.t_rec)}]"
    if h not in done:
        done[h] = json.load(get(URL.format(ds=urllib.parse.quote(ds, safe=""))))
        with open(CACHE, "a") as f:
            f.write(json.dumps({"h": int(h), "d": done[h]}) + "\n")
    d = done[h]
    for i, t in enumerate(d["keywords"][0]["values"]):
        rows.append(dict(harpnum=h, t_rec=t, **{f"{sg['name']}_path": sg["values"][i] for sg in d["segments"]},
                         dims=d["segments"][0]["dims"][i]))
r = pd.DataFrame(rows)
r["npix"] = r.dims.map(lambda x: int(x.split("x")[0]) * int(x.split("x")[1]) if "x" in str(x) else np.nan)
r.to_csv("data/diag/d7_vector_dims.csv", index=False)

rng = np.random.RandomState(20260922)
samp = r.dropna(subset=["npix"]).iloc[rng.choice(r.npix.notna().sum(), 40, replace=False)]
bpp = {}
for sg in SEGS:
    v = []
    for _, x in samp.iterrows():
        v.append(int(get("http://jsoc.stanford.edu" + x[f"{sg}_path"], "HEAD").headers["Content-Length"]) / x.npix)
    bpp[sg] = (np.median(v), np.min(v), np.max(v))
print(f"requested {len(s)} distinct records; returned {len(r)}; with dims {int(r.npix.notna().sum())}; "
      f"HARPs {s.harpnum.nunique()}")
print("pixels per record: median", int(r.npix.median()), "p90", int(r.npix.quantile(.9)), "total", int(r.npix.sum()))
for sg, (m, lo, hi) in bpp.items():
    print(f"{sg:14s} bytes/px median {m:.3f} (range {lo:.3f}-{hi:.3f}) -> total {m * r.npix.sum() / 1e9:.2f} GB")
tot = sum(v[0] for v in bpp.values()) * r.npix.sum() / 1e9
print(f"all 5 segments: {tot:.2f} GB; files {len(r) * 5}")
