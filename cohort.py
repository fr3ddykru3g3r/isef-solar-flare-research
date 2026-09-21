"""Alarm cohort construction (STAGE 3 on dev; the SAME functions are used for test in STAGE 5).

  alarm      gate score >= frozen threshold, primary subset (single-region rows), scorable rows only
  episode    decision T1: alarm hours of one HARP, merged across up to 3 consecutive missing/unscorable hours;
             ends only at a scored hour below threshold or a gap of > 3 missing hours
  t          episode onset (first alarm hour)
  eligible   onset row labelled (label-missing rows are absent from the labelled file by construction),
             history_incomplete == False, and >= 18 of 24 hourly points in (t-24h, t] with both USFLUX and
             TOTUSJH present.  Decision T2: EVERY eligible episode is kept, weighted 1 / (eligible episodes in
             its HARP); first_eligible marks the per-region sensitivity cohort.
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


MAX_MISSING = 3      # T1: an episode survives up to 3 consecutive missing/unscorable hours


def episodes(d, thr):
    """Alarm episodes per HARP (decision T1).  d = every SCORED primary-subset hour (alarm or not).
    An alarm hour starts a new episode if the HARP's previous scored hour was below threshold, or lies
    more than MAX_MISSING + 1 hours earlier (i.e. > 3 missing hours in between).  A missing/unscorable hour
    never ends an episode by itself."""
    d = d.sort_values(["harpnum", "t_rec_utc"]).copy()
    d["alarm"] = d["score"] >= thr
    same = d["harpnum"] == d["harpnum"].shift()
    gap_h = (d["t_rec_utc"] - d["t_rec_utc"].shift()) / pd.Timedelta(hours=1)
    cont = same & d["alarm"].shift(fill_value=False) & (gap_h <= MAX_MISSING + 1)
    a = d[d["alarm"]].copy()
    a["episode"] = (~cont[d["alarm"]]).cumsum()
    return a.groupby("episode").agg(harpnum=("harpnum", "first"), t=("t_rec_utc", "first"),
                                    end=("t_rec_utc", "last"), alarm_hours=("t_rec_utc", "size")).reset_index(drop=True)


def rel_slope(times, values, t):
    """Relative slope per hour over (t-24h, t]; NaN if fewer than MIN_POINTS usable points."""
    m = values.notna().to_numpy()
    if m.sum() < MIN_POINTS:
        return np.nan
    x = ((times[m] - t) / pd.Timedelta(hours=1)).to_numpy(float)
    v = values[m].to_numpy(float)
    return float(np.polyfit(x, v, 1)[0] / v.mean())


def build(scored, lab, thr, missing_days):
    """scored: every scored primary-subset hour (harpnum, t_rec_utc, score).  lab: the labelled file for the same
    HARPs (all subsets; the trend window uses every labelled row of the HARP).
    Returns (cohort, exclusions, episodes).  cohort = EVERY eligible episode (decision T2) with
    weight = 1 / eligible episodes in its HARP, and first_eligible = the HARP's earliest eligible episode
    (the first-episode-per-region sensitivity analysis)."""
    eps = episodes(scored, thr)
    score_at = scored.set_index(["harpnum", "t_rec_utc"])["score"]
    lab = lab.sort_values(["harpnum", "t_rec_utc"])
    by_harp = {h: g for h, g in lab.groupby("harpnum")}
    fl, _ = swpc.fetch(scored["t_rec_utc"].min(), scored["t_rec_utc"].max() + pd.Timedelta(hours=48), verbose=False)
    m1 = fl[fl["flux"] >= 1e-5]
    missing = [pd.Timestamp(d) for d in missing_days]
    rows, excl = [], []
    for _, e in eps.iterrows():
        h, t = e["harpnum"], e["t"]
        g = by_harp[h]
        on = g[g["t_rec_utc"] == t].iloc[0]
        if bool(on["history_incomplete"]):
            excl.append((h, t, "history_incomplete")); continue
        w = g[(g["t_rec_utc"] > t - pd.Timedelta(hours=24)) & (g["t_rec_utc"] <= t)]
        su, sj = rel_slope(w["t_rec_utc"], w["usflux"], t), rel_slope(w["t_rec_utc"], w["totusjh"], t)
        if np.isnan(su) or np.isnan(sj):
            excl.append((h, t, f"trend window < {MIN_POINTS} points")); continue
        ars = {int(x) for x in str(on["noaa_ars"]).split(",") if x.strip().isdigit()}
        later = m1[m1["noaa_ar"].isin(ars) & (m1["start"] > t + pd.Timedelta(hours=24))
                   & (m1["start"] <= t + pd.Timedelta(hours=48))]
        follow_ok = not any((D < t + pd.Timedelta(hours=48)) and (D + pd.Timedelta(days=1) > t + pd.Timedelta(hours=24))
                            for D in missing)
        true = int(on["flared_M1_next_24h"])
        rows.append({"harpnum": h, "t": t, "episode_end": e["end"], "alarm_hours": int(e["alarm_hours"]),
                     "score": float(score_at[(h, t)]), "true_alarm": true,
                     "n_C": int(on["n_C_prev_48h"]), "n_M": int(on["n_M_prev_48h"]), "n_X": int(on["n_X_prev_48h"]),
                     "rel_slope_usflux": su, "rel_slope_totusjh": sj,
                     "delayed": int(true == 0 and len(later) > 0 and follow_ok),
                     "delayed_followup_incomplete": int(true == 0 and len(later) > 0 and not follow_ok),
                     "noaa_ars": on["noaa_ars"]})
    c = pd.DataFrame(rows)
    if len(c):
        c["weight"] = 1.0 / c.groupby("harpnum")["t"].transform("size")          # T2: each region sums to 1
        c["first_eligible"] = c["t"] == c.groupby("harpnum")["t"].transform("min")
    return c, pd.DataFrame(excl, columns=["harpnum", "t", "reason"]), eps
