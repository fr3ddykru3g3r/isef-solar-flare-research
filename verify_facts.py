"""READ-ONLY fact check (2026-09-23). Loads result artefacts / recomputes counts; no fitting, no frozen-file changes.
Prints key = value lines used to fill VERIFIED_FACTS.md."""
import glob, hashlib, json, re
import numpy as np, pandas as pd

H = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
out = {}


def put(k, v):
    out[k] = v; print(f"{k} = {v}")


# ---------------------------------------------------------------- data
SPEC = json.load(open("frozen/frozen_spec.json"))
put("sha.frozen_spec", H("frozen/frozen_spec.json")[:8]); put("sha.split", H("frozen/split.csv")[:8])
LAB = "data/labelled_20100501_20250101.csv"; put("sha.labelled", H(LAB)[:8])
lab = pd.read_csv(LAB, parse_dates=["t_rec_utc"], low_memory=False)
put("lab.rows", len(lab)); put("lab.first", lab.t_rec_utc.min()); put("lab.last", lab.t_rec_utc.max())
put("lab.dups", int(lab.duplicated(["harpnum", "t_rec_tai"]).sum()))
put("lab.rows_2020", int((lab.t_rec_utc.dt.year == 2020).sum()))
chunks = [f for f in glob.glob("data/labelled_20*.csv") if f != LAB and re.search(r"labelled_\d{8}_\d{8}\.csv$", f)
          and not f.endswith("20250101_20260817.csv")]
put("lab.chunk_files", len(chunks)); put("lab.chunk_rows_sum", sum(sum(1 for _ in open(f)) - 1 for f in chunks))
sp = pd.read_csv("frozen/split.csv"); put("split.counts", sp.set.value_counts().to_dict())
put("spec.gate", {k: SPEC["gate"][k] for k in SPEC["gate"] if k in ("features", "threshold", "svm", "scaling", "training_rows", "thinning")})
put("spec.excluded_years", SPEC["data"]["excluded_years"]); put("spec.primary_test_years", SPEC["data"]["primary_test_years"])
p24 = lab[(lab.t_rec_utc.dt.year == 2024) & (lab.flared_M1_next_24h == 1)]
put("k2.2024_pos_rows", len(p24)); put("k2.2024_pos_multi_share", round((p24.noaa_ar_count > 1).mean(), 4))
jr = pd.read_csv("data/join_report_swpc.csv"); put("join_report_swpc.cols", list(jr.columns))
print(jr.to_string(index=False))
ge = pd.read_csv("data/goes_empty_days.csv"); put("goes_empty.cols", list(ge.columns)); put("goes_empty.rows", len(ge))
for c in ge.columns:
    if ge[c].dtype == object and ge[c].nunique() < 10:
        put(f"goes_empty.{c}", ge[c].value_counts().to_dict())
cc = pd.read_csv("data/completeness_check.csv"); print(cc.to_string(index=False))
ng = [L for L in open("data/ngdc/xrs_2011.txt") if L.startswith("31777")]
put("ngdc.2011_rows", len(ng)); put("ngdc.2011_with_loc", sum(bool(re.match(r"[NS]\d\d[EW]\d\d", L[28:34])) for L in ng))

# ---------------------------------------------------------------- gate / stage 2-5
s2 = pd.read_csv("data/stage2/stage2_metrics.csv"); print(s2.to_string(index=False))
put("s2.threshold", json.load(open("data/stage2/stage2_result.json")).get("threshold"))
g5 = pd.read_csv("data/stage5/gate_gate.csv"); print(g5.to_string(index=False))
m5 = pd.read_csv("data/stage5/models_b.csv"); print(m5.to_string(index=False))
print(pd.read_csv("data/stage5/cohort_sizes.csv").to_string(index=False))
print(pd.read_csv("data/stage5/pairs_summary.csv").to_string(index=False))
print(pd.read_csv("data/stage4/stepA_dev.csv").to_string(index=False))
c3 = pd.read_csv("data/stage3/cohort_dev.csv"); put("s3.episodes", len(c3)); put("s3.true", int(c3.true_alarm.sum()))
put("s3.delayed", int(c3.delayed.sum())); put("s3.harps", c3.harpnum.nunique()); put("s3.true_harps", c3.loc[c3.true_alarm == 1, "harpnum"].nunique())
put("s3.true_episode_rate", round(c3.true_alarm.mean(), 4)); put("s3.true_weighted_rate", round((c3.weight * c3.true_alarm).sum() / c3.weight.sum(), 4))
s4 = json.load(open("data/stage4/stage4_result.json")); put("s4.keys", list(s4)[:20])
for k in ("delta", "delta_ci", "caliper", "pooled"):
    if k in s4: put(f"s4.{k}", s4[k])

# ---------------------------------------------------------------- diagnostics
print(pd.read_csv("data/diag/ablation.csv").to_string(index=False))
us = pd.read_csv("data/diag/uncertainty_seeds.csv"); print(us.groupby(us.columns[0]).agg(["mean", "std", "min", "max"]).round(4).to_string() if us.shape[1] <= 3 else us.describe().round(4).to_string())
for f, k in [("data/diag/d7_repeats.csv", "D7"), ("data/diag/d7t_repeats.csv", "D7t")]:
    x = pd.read_csv(f).TSS; put(f"{k}.TSS", f"{x.mean():.4f} ± {x.std(ddof=1):.4f} (n {len(x)})")
d8 = pd.read_csv("data/diag/d8_counts.csv"); put("D8.TSS", f"{d8.TSS.mean():.4f} ± {d8.TSS.std(ddof=1):.4f}")
print(pd.read_csv("data/diag/d7_d8_comparison.csv").to_string(index=False))
print(pd.read_csv("data/diag/r_runs.csv")[["run", "C1/C2", "P", "N", "TSS", "TSS in target"]].to_string(index=False))
print(pd.read_csv("data/diag/swansf_validation.csv").to_string(index=False))
lc = pd.read_csv("data/diag/d7_location_proxy_catalogue.csv"); put("ngdc.loss_rows", len(lc)); put("ngdc.loss_lon_le68", int((lc.lon.abs() <= 68).sum()))
put("rruns.R2_admissions", re.search(r"NCEI-location admissions (\d+)", open("data/diag/r_runs.log").read()).group(1))
sm = pd.read_csv("data/diag/d7_sample_records.csv"); put("d7.sample", f"P {int(sm.y.sum())} N {int((sm.y == 0).sum())} distinct {sm.drop_duplicates(['harpnum','t_rec']).shape[0]} HARPs {sm.harpnum.nunique()}")
# region count 2010-05-01..2014-05-31 from raw chunk files (hourly cache)
from chunks import months
raw = pd.concat([pd.read_csv(f"data/raw_sharp_{a}_{b}.csv".replace("-", ""), usecols=["HARPNUM", "T_REC", "NOAA_ARS"],
                 dtype={"NOAA_ARS": str, "T_REC": str}) for a, b in months("2010-05-01", "2014-07-01")]).drop_duplicates(["HARPNUM", "T_REC"])
raw = raw[(raw.T_REC.str[:10] >= "2010.05.01") & (raw.T_REC.str[:10] <= "2014.05.31")]
nz = raw.NOAA_ARS.fillna("").str.strip()
put("regions.HARPs", raw.HARPNUM.nunique()); put("regions.HARPs_with_NOAA", raw[nz.str.match(r"\d")].HARPNUM.nunique())
put("regions.NOAA_ARs", len({int(x) for v in nz for x in v.split(",") if x.strip().isdigit()}))

# ---------------------------------------------------------------- QUALITY at 06/18 TAI (raw, all years)
q = pd.read_csv("data/raw_sharp_20100501_20250101.csv", usecols=["T_REC", "QUALITY"], dtype={"T_REC": str})
hr = q.T_REC.str[11:13]; ok = q.QUALITY == 0
for h_ in ("06", "18", "00", "12"):
    put(f"quality.hour{h_}_pass", f"{int(ok[hr == h_].sum())}/{int((hr == h_).sum())} = {ok[hr == h_].mean():.4f}")

# ---------------------------------------------------------------- EUV
print(pd.read_csv("data/euv_pilot/check.csv").to_string(index=False))
dl = pd.read_csv("data/euv_pilot/download_log.csv"); print(dl[dl["item"] == 4].to_string(index=False))
for f in ["dctrl_cutout", "dctrl_synoptic", "dctrl_cadence", "dctrl_cutout_preexp", "dctrl_synoptic_preexp", "dctrl_cadence_preexp"]:
    d = pd.read_csv(f"data/euv_pilot/{f}.csv"); print(f, d[["harpnum", "tag", "frames", "valid", "dCV"]].round(4).to_string(index=False))
print(pd.read_csv("data/euv_pilot/offset_test_12s_94.csv").groupby("harpnum").dCV.agg(["mean", "std", "min", "max", "first"]).round(4).to_string())
for f in ["agreement_synoptic", "agreement_cutout", "source_decision", "cost_full_study", "validity_summary", "verify_crop"]:
    print(f); print(pd.read_csv(f"data/euv_cad/{f}.csv").to_string(index=False))
ct = pd.read_csv("data/euv_cad/cutout_timing_131_12min.csv"); put("euv.131_exports", len(ct))
c = pd.read_csv("data/stage3/cohort_dev.csv", parse_dates=["t"]); sl = set()
for t in c.t:
    sl.update(pd.date_range(t - pd.Timedelta("24h") + pd.Timedelta("12min"), t, freq="12min").round("12min"))
put("euv.unique_12min_slots", len(sl))

# ---------------------------------------------------------------- Path A
print(pd.read_csv("data/diag/patha_gate.csv").round(4).to_string(index=False))
for f in glob.glob("data/diag/patha_phantom_*.csv"):
    print(f); print(pd.read_csv(f).tail(1).to_string(index=False))
ph = pd.read_csv("data/pathA/phantoms_2021_24.csv")
put("pathA.phantoms", len(ph)); put("pathA.phantom_harps", ph.harpnum.nunique()); put("pathA.per_year", ph.year.value_counts().sort_index().to_dict())
put("pathA.obs", ph.first_swpc_obs.value_counts().to_dict()); put("pathA.hek_ar", ph.hek_ar_noaanum.fillna("none").value_counts().to_dict())
m = ph[ph.hek_events_within_10min > 0]
put("pathA.hek_class_contains_swpc_class", int(sum(str(a) in str(b).split(";") for a, b in zip(m.first_swpc_class_K2, m.hek_class))))
put("pathA.hek_class_equals_swpc_exact", int(sum(str(a) == str(b) for a, b in zip(m.first_swpc_class_K2, m.hek_class))))
print(pd.read_csv("data/pathA/far_precision_ci_2021_24.csv").to_string(index=False))
print(pd.read_csv("data/pathA/far_precision_ci_by_years.csv").to_string(index=False))
print(pd.read_csv("data/pathA/region_flips_2021_24.csv").reason.value_counts().to_string())
print(pd.read_csv("data/pathA/hek_ar_zero_by_year.csv").to_string(index=False))
json.dump({k: str(v) for k, v in out.items()}, open("/tmp/verify_facts.json", "w"), indent=1)
