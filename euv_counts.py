"""Step 4 COUNT-FIRST fill threshold (decisions.md 2026-09-23 amendment). ELIGIBILITY COUNTS ONLY - reads no dCV value.
Denominator = all 547 dev episodes; episodes without a result (no data) count as not valid."""
import glob, json
import numpy as np, pandas as pd

R = "data/euv_full"
c = pd.read_csv("data/stage3/cohort_dev.csv", parse_dates=["t"])
c["eid"] = [f"{h}_{t:%Y%m%dT%H%M}" for h, t in zip(c.harpnum, c.t)]
KEEP = ["eid", "frames", "primary_fill", "sens_fill", "excl_quality", "excl_exposure", "excl_flare", "sat_flagged_frames",
        "frames_no_satrot", "max_frac_outside_valid"]                      # no dCV column is read
res = pd.DataFrame([{k: json.load(open(p)).get(k) for k in KEEP} for p in glob.glob(f"{R}/results/*.json")])
for k in KEEP[1:]:
    res[k] = pd.to_numeric(res[k], errors="coerce")
d = c[["eid", "harpnum", "true_alarm"]].merge(res, on="eid", how="left")
d["has_result"] = d.frames.notna()
rows = []
for thr in (0.90, 0.80, 0.70):
    for ver in ("primary", "sens"):
        v = d[f"{ver}_fill"].fillna(0) >= thr
        ft, ff = v[d.true_alarm == 1].mean(), v[d.true_alarm == 0].mean()
        rows.append(dict(threshold=f"{int(thr * 100)}%", version=ver, valid_all=int(v.sum()), of_all=len(d),
                         valid_true=int(v[d.true_alarm == 1].sum()), of_true=int((d.true_alarm == 1).sum()),
                         valid_false=int(v[d.true_alarm == 0].sum()), of_false=int((d.true_alarm == 0).sum()),
                         frac_true=round(ft, 4), frac_false=round(ff, 4), gap_pp=round(100 * abs(ft - ff), 2)))
t = pd.DataFrame(rows)
ok = t.groupby("threshold").gap_pp.max() <= 10
chosen = next((th for th in ("90%", "80%", "70%") if ok[th]), None)
t.to_csv(f"{R}/results/step4_counts.csv", index=False)
pd.set_option("display.width", 250); print(t.to_string(index=False))
print(f"\nthresholds with gap <= 10 pp in BOTH versions: {[th for th in ('90%', '80%', '70%') if ok[th]]}")
print(f"CHOSEN: {chosen if chosen else '70% (no threshold passes; imbalance reported as a limitation)'}")
miss = d[~d.has_result]
print(f"\nepisodes without result: {len(miss)}"); print(miss[["eid", "harpnum"]].to_string(index=False))
r = d[d.has_result]
print(f"\nframes (episodes with results, n={len(r)}): total {int(r.frames.sum())}; QUALITY != 0 {int(r.excl_quality.sum())}; "
      f"exposure rule {int(r.excl_exposure.sum())}; flare-in-progress (removed in SENSITIVITY only) {int(r.excl_flare.sum())}; "
      f"saturation-flagged frames (not removed) {int(r.sat_flagged_frames.sum())}; missing SAT_ROT {int(r.frames_no_satrot.fillna(0).sum())}; "
      f"episodes with any HMI pixel outside the cutout on a valid frame {int((r.max_frac_outside_valid > 0).sum())}")
json.dump(dict(chosen=chosen or "70%", fallback=chosen is None), open(f"{R}/results/step4_choice.json", "w"))
