"""Validity count test (decisions.md 2026-09-23). Counts only: no dCV computed. Re-derives per-frame flags from each
alarm's stored series and reproduces the test's `valid` column exactly (asserted)."""
import numpy as np, pandas as pd
import swpc
from euv_pilot import flare_excluded

R = "data/euv_cad"; CADS = [2, 3, 6, 12]; THR = [0.90, 0.80, 0.70]
A = pd.read_csv(f"{R}/alarms.csv", parse_dates=["t"])
slot_rows, reasons_rows = [], []
for src, sub, ids in [("synoptic", "syn94", A.index), ("cutout", "cut94", A.index[:10])]:
    for e in A.loc[ids].itertuples():
        s = pd.read_csv(f"{R}/{e.harpnum}_{e.t:%Y%m%dT%H%M}/series_{sub}.csv", parse_dates=["t_obs"])
        ev, _ = swpc.load(e.t - pd.Timedelta("2D"), e.t)
        regions = {int(x) for x in str(e.noaa_ars).split(",") if x.strip()}
        flare = flare_excluded(s.t_obs, ev, regions)[0]
        med = s.loc[(s.quality == 0) & (s.exptime > 0), "exptime"].median()
        expo = ~(s.exptime >= 0.5 * med)
        qual = s.quality != 0
        other = s.box.isna()
        valid = ~flare & ~qual & ~other & ~expo
        assert (valid.to_numpy() == s.valid.to_numpy()).all(), (src, e.harpnum)
        why = np.where(expo, "b_exposure", np.where(flare, "c_flare", np.where(qual, "d_quality", np.where(other, "d_other", "ok"))))
        tt = s.t_obs.to_numpy(); tv = tt[valid.to_numpy()]
        for cad in CADS:
            slots = pd.date_range(e.t - pd.Timedelta("24h") + pd.Timedelta(f"{cad}min"), e.t, freq=f"{cad}min").to_numpy()
            half = np.timedelta64(int(cad * 30), "s"); n_fill = 0; cnt = {"a_no_file": 0, "b_exposure": 0, "c_flare": 0, "d_quality": 0, "d_other": 0}
            for sl in slots:
                if len(tv) and np.abs(tv - sl).min() <= half:
                    n_fill += 1; continue
                d = np.abs(tt - sl)
                if not len(tt) or d.min() > half:
                    cnt["a_no_file"] += 1
                else:
                    cnt[why[int(np.argmin(d))]] += 1
            f = n_fill / len(slots)
            slot_rows.append(dict(source=src, order=e.order, harpnum=e.harpnum, t=e.t, label="true" if e.true_alarm else "false",
                                  cad_min=cad, slots=len(slots), filled=n_fill, pct_filled=round(100 * f, 1),
                                  **{f"valid_{int(100 * th)}": f >= th for th in THR}, **cnt))
d = pd.DataFrame(slot_rows); d.to_csv(f"{R}/validity_counts.csv", index=False)
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 200)
print(d.drop(columns=["t"]).to_string(index=False))

# summary: valid alarms per source x cadence x threshold, overall and by label
S = []
for (src, cad), g in d.groupby(["source", "cad_min"]):
    for th in THR:
        c = f"valid_{int(100 * th)}"
        S.append(dict(source=src, cad_min=cad, threshold=f"{int(100 * th)}%", valid=int(g[c].sum()), of=len(g),
                      valid_true=int(g.loc[g.label == "true", c].sum()), of_true=int((g.label == "true").sum()),
                      valid_false=int(g.loc[g.label == "false", c].sum()), of_false=int((g.label == "false").sum())))
S = pd.DataFrame(S); S.to_csv(f"{R}/validity_summary.csv", index=False); print("\n" + S.to_string(index=False))

# per-alarm list: % filled at 2 and 12 min, main empty-slot reason (over all cadences, per source)
L = []
for (src, o), g in d.groupby(["source", "order"]):
    rs = g[["a_no_file", "b_exposure", "c_flare", "d_quality", "d_other"]].sum()
    L.append(dict(source=src, order=o, harpnum=g.harpnum.iloc[0], alarm_t=g.t.iloc[0], label=g.label.iloc[0],
                  pct_2min=g.loc[g.cad_min == 2, "pct_filled"].item(), pct_12min=g.loc[g.cad_min == 12, "pct_filled"].item(),
                  main_reason=rs.idxmax() if rs.sum() else "none", empty_slots_all_cads=int(rs.sum())))
L = pd.DataFrame(L); L.to_csv(f"{R}/validity_per_alarm.csv", index=False); print("\n" + L.to_string(index=False))
