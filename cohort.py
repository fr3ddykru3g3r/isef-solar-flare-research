"""Alarm cohort construction (STAGE 3 on dev; the SAME functions are used for test in STAGE 5).

  alarm      gate score >= frozen threshold, primary subset (single-region rows), scorable rows only
  episode    alarm hours of one HARP that are consecutive in time (exactly 1 h apart); any gap ends it
  t          episode onset (first alarm hour)
  eligible   onset row labelled (label-missing rows are absent from the labelled file by construction),
             history_incomplete == False, and >= 18 of 24 hourly points in (t-24h, t] with both USFLUX and
             TOTUSJH present.  One episode per HARP: the FIRST eligible one.
  true       M1+ in (t, t+24h]  (= flared_M1_next_24h of the onset row); false = none
  history    n_C, n_M, n_X in [t-48h, t) -- identical to (t-48h, t] here: t is always hh:59:2x UTC and
             flare starts are on whole minutes, so no flare can sit on either boundary
  trends     least-squares slope of USFLUX and TOTUSJH vs time (hours) over (t-24h, t], divided by the
             window mean -> relative slope, per hour
  delayed    (exploratory) false alarm with >= 1 M1+ in (t+24h, t+48h] from the HARP's region, and complete
             follow-up: (t+24h, t+48h] overlaps no label-missing day
"""
import numpy as np, pandas as pd
import swpc

MIN_POINTS = 18


def episodes(d, thr):
    """Alarm episodes per HARP from hourly scored rows d (harpnum, t_rec_utc, score)."""
    a = d[d["score"] >= thr].sort_values(["harpnum", "t_rec_utc"]).copy()
    new = (a["harpnum"] != a["harpnum"].shift()) | (a["t_rec_utc"].diff() != pd.Timedelta(hours=1))
    a["episode"] = new.cumsum()
    return a.groupby("episode").agg(harpnum=("harpnum", "first"), t=("t_rec_utc", "first"),
                                    hours=("t_rec_utc", "size")).reset_index(drop=True)


def rel_slope(times, values, t):
    """Relative slope per hour over (t-24h, t]; NaN if fewer than MIN_POINTS usable points."""
    m = values.notna().to_numpy()
    if m.sum() < MIN_POINTS:
        return np.nan
    x = ((times[m] - t) / pd.Timedelta(hours=1)).to_numpy(float)
    v = values[m].to_numpy(float)
    return float(np.polyfit(x, v, 1)[0] / v.mean())


def build(scored, lab, thr, missing_days):
    """scored: hourly primary-subset rows with a score.  lab: the full labelled file for the same HARPs
    (all subsets; the trend window uses every labelled row of the HARP).  Returns (cohort, exclusions)."""
    eps = episodes(scored, thr)
    score_at = scored.set_index(["harpnum", "t_rec_utc"])["score"]
    lab = lab.sort_values(["harpnum", "t_rec_utc"])
    by_harp = {h: g for h, g in lab.groupby("harpnum")}
    fl, _ = swpc.fetch(scored["t_rec_utc"].min(), scored["t_rec_utc"].max() + pd.Timedelta(hours=48), verbose=False)
    m1 = fl[fl["flux"] >= 1e-5]
    missing = [pd.Timestamp(d) for d in missing_days]
    rows, excl = [], []
    for h, E in eps.groupby("harpnum"):
        g = by_harp[h]
        chosen = None
        for _, e in E.sort_values("t").iterrows():
            t = e["t"]
            on = g[g["t_rec_utc"] == t].iloc[0]
            if bool(on["history_incomplete"]):
                excl.append((h, t, "history_incomplete")); continue
            w = g[(g["t_rec_utc"] > t - pd.Timedelta(hours=24)) & (g["t_rec_utc"] <= t)]
            su, sj = rel_slope(w["t_rec_utc"], w["usflux"], t), rel_slope(w["t_rec_utc"], w["totusjh"], t)
            if np.isnan(su) or np.isnan(sj):
                excl.append((h, t, f"trend window < {MIN_POINTS} points")); continue
            chosen = (e, on, su, sj); break
        if chosen is None:
            continue
        e, on, su, sj = chosen
        t = e["t"]
        ars = {int(x) for x in str(on["noaa_ars"]).split(",") if x.strip().isdigit()}
        later = m1[m1["noaa_ar"].isin(ars) & (m1["start"] > t + pd.Timedelta(hours=24))
                   & (m1["start"] <= t + pd.Timedelta(hours=48))]
        follow_ok = not any((D < t + pd.Timedelta(hours=48)) and (D + pd.Timedelta(days=1) > t + pd.Timedelta(hours=24))
                            for D in missing)
        true = int(on["flared_M1_next_24h"])
        rows.append({"harpnum": h, "t": t, "episode_hours": int(e["hours"]), "score": float(score_at[(h, t)]),
                     "true_alarm": true, "n_C": int(on["n_C_prev_48h"]), "n_M": int(on["n_M_prev_48h"]),
                     "n_X": int(on["n_X_prev_48h"]), "rel_slope_usflux": su, "rel_slope_totusjh": sj,
                     "delayed": int(true == 0 and len(later) > 0 and follow_ok),
                     "delayed_followup_incomplete": int(true == 0 and len(later) > 0 and not follow_ok),
                     "noaa_ars": on["noaa_ars"]})
    return pd.DataFrame(rows), pd.DataFrame(excl, columns=["harpnum", "t", "reason"]), eps
