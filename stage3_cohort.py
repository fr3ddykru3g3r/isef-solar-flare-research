"""STAGE 3 -- dev alarm cohort (2010-2019), from the STAGE 2 out-of-fold scores and frozen threshold."""
import json
import pandas as pd
import cohort, swpc

thr = json.load(open("data/stage2/stage2_result.json"))["threshold"]
oof = pd.read_csv("data/stage2/oof_scores_dev.csv", parse_dates=["t_rec_utc"])
split = pd.read_csv("frozen/split.csv")
dev = set(split.loc[split["set"].isin(["train", "val"]), "harpnum"])
lab = pd.read_csv("data/labelled_20100501_20250101.csv", parse_dates=["t_rec_utc"], low_memory=False)
lab = lab[lab["harpnum"].isin(dev) & (lab["t_rec_utc"].dt.year <= 2019)]
assert oof["t_rec_utc"].dt.year.max() <= 2019 and set(oof["harpnum"]) <= dev
scored = oof[oof["noaa_ar_count"] == 1][["harpnum", "t_rec_utc", "score"]]
scored = scored.merge(lab, on=["harpnum", "t_rec_utc"], how="left", validate="one_to_one")
assert scored["flared_M1_next_24h"].notna().all()

c, x, eps = cohort.build(scored, lab, thr, swpc.label_missing_days())
print(f"threshold {thr:.6f}")
print(f"alarm hours (primary subset): {int((scored['score'] >= thr).sum())}; "
      f"episodes (T1 merging): {len(eps)} in {eps['harpnum'].nunique()} HARPs; "
      f"length median {eps['alarm_hours'].median():.0f} h, max {eps['alarm_hours'].max()} h (alarm hours)")
print("\nexclusions (episodes):")
print(x["reason"].value_counts().to_string() if len(x) else "  none")
print(f"HARPs with an alarm but NO eligible episode: {eps['harpnum'].nunique() - c['harpnum'].nunique()}")


def summary(d, label):
    reg = d.groupby("harpnum").agg(any_true=("true_alarm", "max"), any_delayed=("delayed", "max"))
    w = d["weight"] if "weight" in d else 1.0
    f = d["true_alarm"] == 0
    print(f"\n{label}")
    print(f"  episodes: {len(d)}  true {int(d['true_alarm'].sum())}  false {int(f.sum())}  delayed {int(d['delayed'].sum())}")
    print(f"  regions : {len(reg)}  with >=1 true episode {int(reg['any_true'].sum())}  "
          f"with only false {int((reg['any_true'] == 0).sum())}  with >=1 delayed {int(reg['any_delayed'].sum())}")
    print(f"  region-weighted (effective) counts: true {(w * d['true_alarm']).sum():.2f}  "
          f"false {(w * f).sum():.2f}  delayed {(w * d['delayed']).sum():.2f}  (total = {w.sum():.2f} regions)")


summary(c, "PRIMARY COHORT (T2: all eligible episodes, weight 1/episodes-in-HARP)")
first = c[c["first_eligible"]].drop(columns="weight").assign(weight=1.0)
summary(first, "SENSITIVITY: first eligible episode per region")
c.to_csv("data/stage3/cohort_dev.csv", index=False)
x.to_csv("data/stage3/exclusions_dev.csv", index=False)
eps.to_csv("data/stage3/episodes_dev.csv", index=False)

# the flaring regions: HARPs with >= 1 detected positive hour (out-of-fold, primary subset)
o = scored
flaring = set(o.loc[(o["flared_M1_next_24h"] == 1) & (o["score"] >= thr), "harpnum"])
true_regions = set(c.loc[c["true_alarm"] == 1, "harpnum"])
print(f"\nregions with >= 1 detected positive hour: {len(flaring)}; in the cohort: {len(flaring & set(c['harpnum']))}; "
      f"contributing >= 1 TRUE-alarm episode: {len(flaring & true_regions)}")
