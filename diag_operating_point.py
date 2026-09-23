"""DESCRIPTIVE operating point (decisions.md 2026-09-23); not a pre-registered test. No refit."""
import numpy as np, pandas as pd
dev = pd.read_csv("data/stage4/oof_cohort_dev.csv"); te = pd.read_csv("data/stage5/cohort_test_primary.csv")
assert len(dev) == 547 and len(te) == 313


def tau_keep(df, p, keep=0.88):
    t = df[df.true_alarm == 1].sort_values(p, ascending=False)
    cum = t.weight.cumsum() / t.weight.sum()
    return float(t[p].iloc[int(np.argmax(cum.to_numpy() >= keep))])


def stats(df, kept):
    w, y = df.weight.to_numpy(), df.true_alarm.to_numpy(); k = kept
    return dict(true_kept=(w * y * k).sum() / (w * y).sum(), false_removed=(w * (1 - y) * ~k).sum() / (w * (1 - y)).sum(),
                prec_before=(w * y).sum() / w.sum(), prec_after=(w * y * k).sum() / (w * k).sum() if k.any() else np.nan)


rows, keys = [], te.harpnum.unique()
grp = {h: np.where(te.harpnum.to_numpy() == h)[0] for h in keys}
for name, p in [("gate only (all kept)", None), ("gate + history (A)", "p_A"), ("A + trends (B)", "p_B")]:
    tau = tau_keep(dev, p) if p else np.nan
    kept = (te[p] >= tau).to_numpy() if p else np.ones(len(te), bool)
    s = stats(te, kept); rng = np.random.RandomState(20260921); B = []
    for _ in range(10000):
        ix = np.concatenate([grp[k] for k in rng.choice(keys, len(keys), replace=True)])
        b = te.iloc[ix]; B.append(list(stats(b, kept[ix]).values()))
    B = np.array(B, float)
    ci = {k: np.nanpercentile(B[:, j], [2.5, 97.5]) for j, k in enumerate(s)}
    dk = dev[p] >= tau if p else pd.Series(True, index=dev.index)
    rows.append(dict(model=name, tau=tau, dev_true_kept_w=stats(dev, dk.to_numpy())["true_kept"],
                     test_kept=int(kept.sum()), test_true_kept=int((kept & (te.true_alarm == 1)).sum()), test_true=int(te.true_alarm.sum()),
                     test_false_removed=int((~kept & (te.true_alarm == 0)).sum()), test_false=int((te.true_alarm == 0).sum()),
                     **{f"{k}": s[k] for k in s}, **{f"{k}_lo": ci[k][0] for k in s}, **{f"{k}_hi": ci[k][1] for k in s}))
r = pd.DataFrame(rows); r.to_csv("data/stage5/operating_point_descriptive.csv", index=False)
pd.set_option("display.width", 250); print(r.round(4).T.to_string())
