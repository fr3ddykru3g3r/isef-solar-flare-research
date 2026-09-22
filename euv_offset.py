"""Phase 1.2 offset test (decisions.md 2026-09-23): 12-min subsamples of the 12-s 94 A series over (t-6h, t] at all
60 offsets (0 s .. 11:48 in 12-s steps). dCV (D-CTRL, 20 draws) per offset; the current 12-min value = offset 0
(slots t-6h+12min*k). Reads data/euv_pilot/<h>/series_dctrl_12s_94.csv (exposure rule applied)."""
import numpy as np, pandas as pd
from scipy.stats import percentileofscore
from euv_dctrl import summarise
from euv_download import EP

out = []
for e in EP.itertuples():
    s = pd.read_csv(f"data/euv_pilot/{e.harpnum}/series_dctrl_12s_94.csv", parse_dates=["t_obs"])
    w0 = e.t - pd.Timedelta("6h")
    ph = ((s.t_obs - w0).dt.total_seconds() % 720).to_numpy()
    vals = []
    for o in range(60):
        d = np.abs(ph - 12 * o); d = np.minimum(d, 720 - d)
        sub = s[d <= 6].reset_index(drop=True)
        r = summarise(sub, None, False, 0, f"offset {12 * o}s")
        vals.append(dict(harpnum=e.harpnum, offset_s=12 * o, frames=len(sub), valid=r["valid"], dCV=r["dCV"]))
    v = pd.DataFrame(vals); out.append(v)
    x = v.dCV.to_numpy(); cur = x[0]
    print(f"HARP {e.harpnum}: offsets 60, frames/offset {v.frames.min()}-{v.frames.max()}, "
          f"dCV mean {x.mean():.4f} SD {x.std(ddof=1):.4f} min {x.min():.4f} max {x.max():.4f}; "
          f"current (offset 0) {cur:.4f} = percentile {percentileofscore(x, cur, kind='mean'):.1f}")
pd.concat(out).to_csv("data/euv_pilot/offset_test_12s_94.csv", index=False)
