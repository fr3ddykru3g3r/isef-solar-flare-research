"""Score the FROZEN predictions under three evaluation questions.

This script never fits anything. It reads verification/out/frozen.csv and only
changes what counts as a positive forecasting success:

  mapped    every positive hourly row has weight 1        (row-based, the usual way)
  episode   every physical flare episode has total weight 1
  first     only each episode's EARLIEST positive row     (maximum warning lead)

The negative population is identical in all three, so FPR is fixed within a
model and every TSS difference comes from the positive side.

Usage: python verification/evaluate.py
"""
import os
import numpy as np, pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT  = os.path.join(ROOT, "verification", "out")
DRAWS, SEED = 10000, 20260921
MODELS = ["xgb_joint", "xgb_nohist", "proxy_pastflare", "climatology"]


def per_episode(df, p, thr):
    """(n_i, tp_i, a_i) per positive episode, in stable episode order."""
    alert = p >= thr
    pos = df.episode.to_numpy() >= 0
    ep  = df.episode.to_numpy()[pos]
    al  = alert[pos]
    order = np.argsort(ep, kind="stable")           # rows already time-sorted within HARP
    ep, al = ep[order], al[order]
    uniq, start = np.unique(ep, return_index=True)
    n  = np.diff(np.r_[start, len(ep)])
    tp = np.add.reduceat(al.astype(np.int64), start)
    a  = al[start].astype(np.int64)                 # earliest row of each episode
    return n.astype(float), tp.astype(float), a.astype(float)


def neg_groups(df, p, thr):
    """(fp_j, n_j) per negative resampling unit (one HARP = one correlated block)."""
    neg = df.episode.to_numpy() < 0
    h  = df.harpnum.to_numpy()[neg]
    al = (p >= thr)[neg].astype(np.int64)
    o = np.argsort(h, kind="stable")
    h, al = h[o], al[o]
    _, start = np.unique(h, return_index=True)
    return (np.add.reduceat(al, start).astype(float),
            np.diff(np.r_[start, len(h)]).astype(float))


def views(n, tp, a, fp, nn):
    fpr = fp.sum() / nn.sum()
    pod = {"mapped": tp.sum() / n.sum(),
           "episode": np.mean(tp / n),
           "first":   np.mean(a)}
    return {k: {"POD": v, "FPR": fpr, "TSS": v - fpr} for k, v in pod.items()}


def main():
    df = pd.read_csv(os.path.join(OUT, "frozen.csv"), parse_dates=["t_rec_utc"])
    df = df[df.role == "score"].sort_values(["harpnum", "t_rec_utc"]).reset_index(drop=True)
    nep = df.loc[df.episode >= 0, "episode"].nunique()
    print(f"score cohort: {len(df)} rows | {int(df.flared_M1_next_24h.sum())} positive rows "
          f"| {nep} episodes | {int((df.episode<0).sum())} negative rows")

    rows, store = [], {}
    for m in MODELS:
        p, thr = df[f"p_{m}"].to_numpy(), df[f"thr_{m}"].iloc[0]
        n, tp, a = per_episode(df, p, thr)
        fp, nn = neg_groups(df, p, thr)
        store[m] = (n, tp, a, fp, nn)
        v = views(n, tp, a, fp, nn)
        for k in ("mapped", "episode", "first"):
            rows.append(dict(model=m, view=k, **{x: round(v[k][x], 4) for x in ("POD","FPR","TSS")}))
    tab = pd.DataFrame(rows)
    print("\n" + "=" * 64 + "\nTABLE 1  three evaluation views, frozen predictions\n" + "=" * 64)
    print(tab.pivot(index="model", columns="view", values="TSS")[["mapped","episode","first"]]
            .reindex(MODELS).to_string())
    print("\nfull:\n" + tab.to_string(index=False))

    # ---- exact decomposition: POD_row - POD_episode = Cov(n, r) / E[n]
    print("\n" + "=" * 64 + "\nTABLE 2  exact decomposition of mapped -> first-alert\n" + "=" * 64)
    dec = []
    for m in MODELS:
        n, tp, a, fp, nn = store[m]
        r = tp / n
        mult = np.cov(n, r, bias=True)[0, 1] / n.mean()          # mapped - episode
        pers = r.mean() - a.mean()                                # episode - first
        dec.append(dict(model=m, multiplicity=round(mult, 6), lead_time=round(pers, 6),
                        total=round(mult + pers, 6),
                        check=round((tp.sum()/n.sum()) - a.mean(), 6)))
    print(pd.DataFrame(dec).to_string(index=False))
    print("(total and check agree to floating-point rounding -> the split is exact)")

    # ---- paired episode/HARP bootstrap
    print("\n" + "=" * 64 + f"\nTABLE 3  paired bootstrap, {DRAWS} draws, episodes + HARP blocks\n" + "=" * 64)
    rng = np.random.default_rng(SEED)
    npos = len(store[MODELS[0]][0]); nneg = len(store[MODELS[0]][3])
    pi = rng.integers(0, npos, size=(DRAWS, npos))
    ni = rng.integers(0, nneg, size=(DRAWS, nneg))
    res = []
    for m in MODELS:
        n, tp, a, fp, nn = store[m]
        N, TP, A = n[pi], tp[pi], a[pi]
        FP, NN = fp[ni], nn[ni]
        fpr = FP.sum(1) / NN.sum(1)
        mapped  = TP.sum(1) / N.sum(1) - fpr
        episode = (TP / N).mean(1) - fpr
        first   = A.mean(1) - fpr
        for label, d in (("episode - mapped", episode - mapped),
                         ("first - episode",  first - episode),
                         ("first - mapped",   first - mapped)):
            lo, hi = np.percentile(d, [2.5, 97.5])
            res.append(dict(model=m, contrast=label, median=round(np.median(d), 4),
                            lo95=round(lo, 4), hi95=round(hi, 4),
                            excl_zero="yes" if lo * hi > 0 else "NO"))
    print(pd.DataFrame(res).to_string(index=False))

    # ---- ranking reversal check
    print("\n" + "=" * 64 + "\nTABLE 4  does the model ranking change with the question?\n" + "=" * 64)
    piv = tab.pivot(index="model", columns="view", values="TSS")
    for v in ("mapped", "episode", "first"):
        print(f"  {v:8s} ranking: " + " > ".join(piv[v].sort_values(ascending=False).index))

    # ---- detection as a function of warning lead time
    print("\n" + "=" * 64 + "\nTABLE 5  detection rate by warning lead time (hours before flare)\n" + "=" * 64)
    d = df[df.episode >= 0].copy()
    d["lead"] = d.groupby("episode")["t_rec_utc"].transform("max") - d["t_rec_utc"]
    d["leadh"] = (d.lead.dt.total_seconds() / 3600).round().astype(int)
    b = pd.cut(d.leadh, [-1, 2, 5, 8, 11, 14, 17, 25],
               labels=["0-2h","3-5h","6-8h","9-11h","12-14h","15-17h","18h+"])
    for m in ("xgb_joint", "proxy_pastflare"):
        det = (d[f"p_{m}"] >= d[f"thr_{m}"]).groupby(b, observed=False).agg(["mean", "size"])
        print(f"\n  {m}:")
        for k, r in det.iterrows():
            print(f"    {str(k):7s} POD {r['mean']:.3f}   (n={int(r['size'])})")

    tab.to_csv(os.path.join(OUT, "table1_views.csv"), index=False)
    pd.DataFrame(dec).to_csv(os.path.join(OUT, "table2_decomposition.csv"), index=False)
    pd.DataFrame(res).to_csv(os.path.join(OUT, "table3_bootstrap.csv"), index=False)
    print(f"\nwrote tables to {OUT}")


if __name__ == "__main__":
    main()
