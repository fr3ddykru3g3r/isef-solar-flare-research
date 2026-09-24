"""ESTIMATE ONLY (no export, no download) for the pre-registered held-out EUV test (decisions.md 2026-09-24, item h).
Cohort data/stage5/cohort_test_primary.csv; same per-HARP export plan as euv_full.py. Prep model per export (user):
72 s + 0.2 s/file (fitted from data/euv_full/exports.csv). Bytes/file and download s/file from the dev run."""
import numpy as np, pandas as pd

c = pd.read_csv("data/stage5/cohort_test_primary.csv", parse_dates=["t"])
x = pd.read_csv("data/euv_full/exports.csv").query("error != error")          # successful exports only
kb = x.groupby("kind").apply(lambda g: pd.Series({"bytes_per_file": g.bytes.sum() / g.files.sum(),
                                                  "dl_s_per_file": g.download_s.sum() / g.files.sum(),
                                                  "prep_s": g.prep_s.sum(), "files": g.files.sum(), "n": len(g)}),
                             include_groups=False)
prep = lambda n_exp, files: 72 * n_exp + 0.2 * files
dev_wall_h = 12.8 + 0.4                                                           # decisions.md: pass 1 + resume pass
ratio = dev_wall_h / (x.prep_s.sum() / 3600)
# AIA: one export per HARP, (earliest t) - 24h + 12m .. (latest t) @12m (euv_full.expected_frames)
aia_files = sum(len(pd.date_range(g.t.min() - pd.Timedelta("24h") + pd.Timedelta("12min"), g.t.max(), freq="12min"))
                for _, g in c.groupby("harpnum"))
H, hmi_files = c.harpnum.nunique(), 2 * len(c)
rows = []
for plan, n_hmi in [("per-HARP HMI exports", H), ("one combined HMI export", 1)]:
    p = (prep(H, aia_files) + prep(n_hmi, hmi_files)) / 3600
    rows.append(dict(plan=plan, HARPs=H, episodes=len(c), exports=H + n_hmi, AIA_files=aia_files, HMI_files=hmi_files,
                     GB=(aia_files * kb.loc["aia", "bytes_per_file"] + hmi_files * kb.loc["hmi", "bytes_per_file"]) / 1e9,
                     prep_h=p, download_h_serial=(aia_files * kb.loc["aia", "dl_s_per_file"] + hmi_files * kb.loc["hmi", "dl_s_per_file"]) / 3600,
                     wall_h_dev_ratio=p * ratio))
pd.set_option("display.width", 250)
print(f"dev check of the prep model: logged {x.prep_s.sum() / 3600:.2f} h vs model "
      f"{(prep(kb.n.sum(), kb.files.sum())) / 3600:.2f} h; dev wall / dev prep = {ratio:.2f}")
print(kb.round(3).to_string())
print(pd.DataFrame(rows).round(2).to_string(index=False))
