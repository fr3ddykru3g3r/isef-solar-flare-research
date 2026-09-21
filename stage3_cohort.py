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
alarm_harps = eps["harpnum"].nunique()
print(f"threshold {thr:.6f}")
print(f"alarm hours (primary subset): {int((scored['score'] >= thr).sum())}; "
      f"episodes: {len(eps)} in {alarm_harps} HARPs (regions)")
print(f"\nexclusions (episodes skipped while searching for each HARP's first eligible episode):")
print(x["reason"].value_counts().to_string() if len(x) else "  none")
no_elig = alarm_harps - len(c)
print(f"HARPs with an alarm but NO eligible episode: {no_elig}")
if no_elig:
    last = x[~x["harpnum"].isin(c["harpnum"])].groupby("harpnum")["reason"].agg(lambda r: r.value_counts().idxmax())
    print("  by dominant reason:", last.value_counts().to_dict())
print(f"\nCOHORT (one episode per region): {len(c)} regions")
print(f"  true alarms  : {int(c['true_alarm'].sum())}")
print(f"  false alarms : {int((c['true_alarm'] == 0).sum())}")
print(f"  delayed (exploratory, subset of false, complete follow-up): {int(c['delayed'].sum())}")
print(f"  false alarms with a flare in (t+24h, t+48h] but follow-up incomplete: {int(c['delayed_followup_incomplete'].sum())}")
print(f"  episode onset used: first eligible = first episode for {int((~c['harpnum'].isin(x['harpnum'])).sum())} regions")
c.to_csv("data/stage3/cohort_dev.csv", index=False)
x.to_csv("data/stage3/exclusions_dev.csv", index=False)
eps.to_csv("data/stage3/episodes_dev.csv", index=False)
