"""READ-ONLY checks on the finished test results (decisions.md 2026-09-23). Test 2021/2023/2024, single-region, K2.
No fitting: gate scores = mean of the 5 frozen fold models (as Stage 5); cohort = data/stage5/cohort_test_primary.csv.
Onset = episode_onset (first alarm hour, T1); the label time t is the T4 first evaluable hour (>= onset)."""
import hashlib, json
import numpy as np, pandas as pd, joblib
import swpc

OUT = "data/stage5"
SPEC = json.load(open("frozen/frozen_spec.json")); H = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
assert H("frozen/frozen_spec.json").startswith("1d205068") and H(SPEC["data"]["labelled_file"]) == SPEC["data"]["labelled_sha256"]
F, THR = SPEC["gate"]["features"], SPEC["gate"]["threshold"]
ars = lambda v: {int(x) for x in str(v).split(",") if x.strip().isdigit()}
fl, _ = swpc.load(pd.Timestamp("2020-12-01"), pd.Timestamp("2025-01-02"))
m1 = fl[fl.flux >= 1e-5].dropna(subset=["noaa_ar"]).copy(); m1["noaa_ar"] = m1.noaa_ar.astype(int)
m1_all = fl[fl.flux >= 1e-5].copy()
CAT_END = fl.start.max()

# ---------------------------------------------------------------- 1. lead time
c = pd.read_csv(f"{OUT}/cohort_test_primary.csv", parse_dates=["t", "episode_onset"])
rows = []
for e in c.itertuples():
    f = m1[m1.noaa_ar.isin(ars(e.noaa_ars)) & (m1.start > e.episode_onset)].sort_values("start")
    lead = (f.start.iloc[0] - e.episode_onset).total_seconds() / 3600 if len(f) else np.nan
    rows.append(dict(harpnum=e.harpnum, onset=e.episode_onset, t=e.t, true_alarm=e.true_alarm, delayed=e.delayed,
                     first_flare=f.start.iloc[0] if len(f) else pd.NaT, lead_h=lead,
                     group="true" if e.true_alarm else ("delayed" if e.delayed else "other false")))
L = pd.DataFrame(rows); L.to_csv(f"{OUT}/lead_time_test_primary.csv", index=False)
fl_ = L.dropna(subset=["lead_h"]); x = fl_.lead_h
print(f"1. episodes {len(L)}: true {int(L.true_alarm.sum())}, delayed {int(L.delayed.sum())}, "
      f"other false {int(((L.true_alarm == 0) & (L.delayed == 0)).sum())}; catalogue ends {CAT_END}")
print(f"   region produced an M1+ after onset: {len(fl_)}; never (to catalogue end): {len(L) - len(fl_)}")
print(f"   lead (h): median {x.median():.1f}, Q1 {x.quantile(.25):.1f}, Q3 {x.quantile(.75):.1f}, min {x.min():.1f}, max {x.max():.1f}; "
      f"within 24 h {100 * (x <= 24).mean():.1f}%, 48 h {100 * (x <= 48).mean():.1f}%, 72 h {100 * (x <= 72).mean():.1f}%")
print("   by group:", fl_.groupby("group").lead_h.agg(["count", "median"]).round(1).to_dict(),
      "| never-flared by group:", L[L.lead_h.isna()].group.value_counts().to_dict())

# ---------------------------------------------------------------- 2. time-linked region metric (frozen gate re-score)
split = pd.read_csv("frozen/split.csv")
lab = pd.read_csv(SPEC["data"]["labelled_file"], parse_dates=["t_rec_utc"], low_memory=False)
d = lab[lab.harpnum.isin(split.loc[split.set == "test", "harpnum"]) & lab.t_rec_utc.dt.year.isin([2021, 2023, 2024])
        & (lab.noaa_ar_count == 1)]
d = d[~d[F].isna().any(axis=1)].reset_index(drop=True)
X = d[F].to_numpy(float); dv = np.zeros(len(d))
for v in SPEC["gate"]["fold_models"].values():
    assert H(v["path"]) == v["sha256"]; g = joblib.load(v["path"]); dv += g["model"].decision_function((X - g["median"]) / g["sd"])
d["alarm"] = dv / 5 >= THR
r = d.groupby("harpnum").apply(lambda g: pd.Series({"alarmed": g.alarm.any(), "any_pos": g.flared_M1_next_24h.max() == 1,
                                                     "alarm_pos": (g.alarm & (g.flared_M1_next_24h == 1)).any()}), include_groups=False)
al = r[r.alarmed]
print(f"\n2. alarmed regions {len(al)}: existing definition (any labelled hour positive) {int(al.any_pos.sum())}/{len(al)}; "
      f"time-linked (M1+ within 24 h after an ALARMED hour) {int(al.alarm_pos.sum())}/{len(al)}; "
      f"regions positive only outside alarmed hours {int((al.any_pos & ~al.alarm_pos).sum())}")
r.to_csv(f"{OUT}/region_timelinked_test_primary.csv")

# ---------------------------------------------------------------- 3. label spot-check, 15 false episodes (seed 0)
raw = pd.read_csv("data/raw_sharp_20100501_20250101.csv", usecols=["HARPNUM", "T_REC", "NOAA_ARS", "LAT_FWT", "LON_FWT"],
                  dtype={"NOAA_ARS": str, "T_REC": str}, low_memory=False)
raw = raw[raw.T_REC.str[:4].isin(["2021", "2022", "2023", "2024"])].copy()
raw["t"] = pd.to_datetime(raw.T_REC.str[:19], format="%Y.%m.%d_%H:%M:%S") - pd.Timedelta("37s")   # TAI -> UTC (37 s, 2017+)
raw = raw.dropna(subset=["LAT_FWT", "LON_FWT"])
raw["ars"] = raw.NOAA_ARS.apply(ars)


def pos(h=None, ar=None, when=None):
    g = raw[raw.HARPNUM == h] if h is not None else raw[raw.ars.apply(lambda s: ar in s)]
    g = g[(g.t - when).abs() <= pd.Timedelta("1h")]
    if not len(g):
        return None
    j = (g.t - when).abs().idxmin(); return float(g.at[j, "LAT_FWT"]), float(g.at[j, "LON_FWT"]), int(g.at[j, "HARPNUM"])


def gc(a, b):
    la1, lo1, la2, lo2 = map(np.radians, (a[0], a[1], b[0], b[1]))
    return float(np.degrees(np.arccos(np.clip(np.sin(la1) * np.sin(la2) + np.cos(la1) * np.cos(la2) * np.cos(lo1 - lo2), -1, 1))))


S = c[c.true_alarm == 0].sample(15, random_state=0)
out = []
for e in S.itertuples():
    mine = ars(e.noaa_ars)
    w = m1_all[(m1_all.start > e.episode_onset) & (m1_all.start <= e.episode_onset + pd.Timedelta("24h"))]
    if not len(w):
        out.append(dict(harpnum=e.harpnum, onset=e.episode_onset, t=e.t, harp_noaa=sorted(mine), flare_start=pd.NaT, cls="",
                        flare_region="", dist_deg=np.nan, flag="no M1+ on disk in window"))
    for f in w.itertuples():
        hp = pos(h=e.harpnum, when=f.start)
        reg = int(f.noaa_ar) if pd.notna(f.noaa_ar) else None
        fp = pos(ar=reg, when=f.start) if reg is not None else None
        dist = gc(hp[:2], fp[:2]) if hp and fp else np.nan
        if reg is None:
            flag = "no region in SWPC"
        elif reg in mine:
            flag = "OWN REGION (in window after onset)"
        elif fp is None or hp is None:
            flag = "position unavailable"
        else:
            flag = "POSSIBLE MISLABEL (<15 deg)" if dist < 15 else "other region"
        out.append(dict(harpnum=e.harpnum, onset=e.episode_onset, t=e.t, harp_noaa=sorted(mine), flare_start=f.start,
                        cls=f.goes_class, flare_region=reg, region_harp=fp[2] if fp else None,
                        dist_deg=round(dist, 1) if dist == dist else np.nan, flag=flag))
O = pd.DataFrame(out); O.to_csv(f"{OUT}/false_alarm_spotcheck.csv", index=False)
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 200)
print(f"\n3. 15 false episodes (seed 0); M1+ flares on disk in (onset, onset+24h]: {int(O.flare_start.notna().sum())}")
print(O.to_string(index=False)); print("flags:", O.flag.value_counts().to_dict())

# ---------------------------------------------------------------- 4. hourly base rate
b = d.groupby(d.t_rec_utc.dt.year).flared_M1_next_24h.agg(["size", "sum", "mean"])
print(f"\n4. hourly base rate, all scorable rows: {int(d.flared_M1_next_24h.sum())}/{len(d)} = {d.flared_M1_next_24h.mean():.4f}")
print(b.round(4).to_string())
