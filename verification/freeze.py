"""Fit comparators chronologically, select thresholds, and FREEZE predictions.

Nothing downstream may refit. The evaluation script reads only the frozen
probabilities and thresholds, so any score difference it reports is caused by
the evaluation question, not by the model.

Usage: python verification/freeze.py
Writes: verification/out/frozen.csv
"""
import glob, os, re, sys
from datetime import date
import numpy as np, pandas as pd
from xgboost import XGBClassifier

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT  = os.path.join(ROOT, "verification", "out")
SEEDS = [0, 1, 2, 3, 4]

# chronological roles -- fixed before any score is looked at
FIT_END   = "2014-07-01"   # fit   : start .. FIT_END
THR_END   = "2015-04-01"   # thresh: FIT_END .. THR_END
                           # score : THR_END .. end

SHARP = ["usflux","totusjh","totpot","meanshr","r_value","absnjzh","savncpp","area_acr"]
GEOM  = ["lat_fwt","lon_fwt"]
HIST  = ["n_flares_prev_48h","n_C_prev_48h","n_M_prev_48h","n_X_prev_48h"]


def monthly_files():
    out = []
    for p in sorted(glob.glob(DATA + "/labelled_*.csv")):
        m = re.search(r"labelled_(\d{8})_(\d{8})\.csv$", p)
        if not m:
            continue
        a, b = m.group(1), m.group(2)
        ad = date(int(a[:4]), int(a[4:6]), int(a[6:]))
        bd = date(int(b[:4]), int(b[4:6]), int(b[6:]))
        if ad.day == 1 and bd == date(ad.year + ad.month // 12, ad.month % 12 + 1, 1):
            out.append(p)
    return out


def load():
    f = monthly_files()
    df = pd.concat([pd.read_csv(p, parse_dates=["t_rec_utc"], low_memory=False) for p in f],
                   ignore_index=True)
    df = (df.drop_duplicates(subset=["harpnum", "t_rec_tai"])
            .sort_values(["harpnum", "t_rec_utc"])
            .reset_index(drop=True))
    print(f"{len(f)} monthly files -> {len(df)} rows, "
          f"{df.t_rec_utc.min():%Y-%m-%d} .. {df.t_rec_utc.max():%Y-%m-%d}")
    return df


def episodes(df):
    """Label each positive row with an episode id.

    A physical episode is a contiguous run of positive hours within one HARP.
    A gap over 90 min (one missing hourly slot) starts a new episode.
    Negative rows get episode id -1.
    """
    ep = np.full(len(df), -1, dtype=np.int64)
    nxt = 0
    for h, g in df[df.flared_M1_next_24h == 1].groupby("harpnum", sort=False):
        idx = g.index.to_numpy()
        t = g["t_rec_utc"].to_numpy()
        brk = np.r_[0, np.cumsum(np.diff(t).astype("timedelta64[m]").astype(float) > 90)]
        ep[idx] = nxt + brk
        nxt += brk[-1] + 1
    return ep


def assign_role(df):
    """Assign each HARP wholly to one chronological role by its FIRST row.

    Splitting a HARP across roles would put near-identical hourly rows from the
    same region on both sides of the boundary.
    """
    first = df.groupby("harpnum")["t_rec_utc"].min()
    role = pd.Series("score", index=first.index)
    role[first < pd.Timestamp(THR_END)] = "thr"
    role[first < pd.Timestamp(FIT_END)] = "fit"
    return df.harpnum.map(role).to_numpy()


def tss_at(p, y, thr):
    a = p >= thr
    tp = np.sum(a & (y == 1)); fn = np.sum(~a & (y == 1))
    fp = np.sum(a & (y == 0)); tn = np.sum(~a & (y == 0))
    pod = tp / (tp + fn) if tp + fn else 0.0
    fpr = fp / (fp + tn) if fp + tn else 0.0
    return pod - fpr


def pick_threshold(p, y):
    """Max-TSS threshold on the threshold-selection block only."""
    cand = np.unique(np.quantile(p, np.linspace(0.50, 0.9995, 400)))
    return float(max(cand, key=lambda t: tss_at(p, y, t)))


def fit_xgb(Xf, yf, Xall, feats):
    acc = np.zeros(len(Xall))
    for s in SEEDS:
        m = XGBClassifier(n_estimators=300, max_depth=4, learning_rate=0.05,
                          subsample=0.8, colsample_bytree=0.8,
                          reg_lambda=1.0, eval_metric="logloss",
                          random_state=s, n_jobs=4)
        m.fit(Xf[feats], yf)
        acc += m.predict_proba(Xall[feats])[:, 1]
    return acc / len(SEEDS)


def main():
    os.makedirs(OUT, exist_ok=True)
    df = load()
    df["episode"] = episodes(df)
    df["role"] = assign_role(df)
    y = df.flared_M1_next_24h.astype(int).to_numpy()
    print(df.role.value_counts().to_dict())

    fit = df.role == "fit"
    thr = df.role == "thr"
    Xf, yf = df[fit], y[fit]

    models = {
        "xgb_joint":   SHARP + GEOM + HIST,     # full feature interface
        "xgb_nohist":  SHARP + GEOM,            # no recent-flare context
    }
    frozen = {}
    for name, feats in models.items():
        p = fit_xgb(Xf, yf, df, feats)
        t = pick_threshold(p[thr], y[thr])
        frozen[name] = (p, t)
        print(f"{name:12s} threshold {t:.4f}  (fit n={fit.sum()}, thr n={thr.sum()})")

    # past-flare proxy: a rule, not a fit. Recent M-class activity in this region.
    p = (df.n_M_prev_48h.to_numpy() + df.n_X_prev_48h.to_numpy() > 0).astype(float)
    frozen["proxy_pastflare"] = (p, 0.5)
    print(f"{'proxy_pastflare':12s} threshold 0.5000  (rule: any M/X flare in prev 48h)")

    # climatology: constant probability -> never varies, a zero-skill anchor
    frozen["climatology"] = (np.full(len(df), yf.mean()), yf.mean() - 1e-9)
    print(f"{'climatology':12s} constant p={yf.mean():.5f}")

    out = df[["harpnum", "t_rec_utc", "episode", "role", "flared_M1_next_24h"]].copy()
    for name, (p, t) in frozen.items():
        out[f"p_{name}"] = p
        out[f"thr_{name}"] = t
    path = os.path.join(OUT, "frozen.csv")
    out.to_csv(path, index=False)
    print(f"\nwrote {path}  ({len(out)} rows)")
    sc = out.role == "score"
    print(f"score cohort: {sc.sum()} rows, {int(out.loc[sc,'flared_M1_next_24h'].sum())} positive rows, "
          f"{out.loc[sc & (out.episode>=0),'episode'].nunique()} positive episodes")


if __name__ == "__main__":
    main()
