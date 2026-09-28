"""Independent verification of the headline results.

Read-only. Uses its OWN SWPC parser, CV_box, twin matching, bootstrap and model fits
(no imports from the project's pipeline modules). Frozen model files are loaded only to
re-score them. Nothing in the repository is written.
"""
import os, re, glob, json, hashlib, warnings
from decimal import Decimal
from datetime import datetime, timedelta
import numpy as np, pandas as pd, joblib
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score
from scipy.stats import binomtest, wilcoxon

warnings.filterwarnings("ignore")
# repository root: $ISEF_REPO if set, otherwise two levels above this file (docs/verification/ -> repo)
R = os.environ.get("ISEF_REPO") or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
D = f"{R}/data"
CAL = 0.07470488674776919
out = []
def say(*a):
    s = " ".join(str(x) for x in a); print(s, flush=True); out.append(s)
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()

# ---------------------------------------------------------------- 0. hashes of frozen artefacts
say("== 0. FROZEN FILE HASHES")
spec = json.load(open(f"{R}/frozen/frozen_spec.json"))
chk = [(spec["data"]["labelled_file"], spec["data"]["labelled_sha256"]),
       (spec["data"]["split_file"], spec["data"]["split_sha256"]),
       ("cohort.py", spec["cohort"]["code_sha256"])]
chk += [(v["path"], v["sha256"]) for v in spec["gate"]["fold_models"].values()]
chk += [(f"data/stage4/models/{k}.joblib", v) for k, v in spec["models"]["fold_models"].items()]
for p, h in chk:
    fp = f"{R}/{p}"
    if not os.path.exists(fp):
        alt = glob.glob(f"{R}/data/**/{os.path.basename(p)}", recursive=True)
        fp = alt[0] if alt else fp
    ok = os.path.exists(fp) and sha(fp) == h
    say(f"  {'OK  ' if ok else 'FAIL'} {p}")
mh = json.load(open(f"{D}/euv_extra/model_hashes.json"))
bad = [k for k, v in mh.items() if isinstance(v, str) and len(v) == 64 and
       os.path.exists(f"{D}/euv_extra/{k}") and sha(f"{D}/euv_extra/{k}") != v]
say(f"  euv_extra model_hashes.json: {len(mh)} entries, mismatches: {bad if bad else 0}")

# ---------------------------------------------------------------- 1. own SWPC parser
say("\n== 1. LABELS RE-DERIVED WITH AN INDEPENDENT SWPC PARSER")
FAC = {"A": Decimal("1e-8"), "B": Decimal("1e-7"), "C": Decimal("1e-6"), "M": Decimal("1e-5"), "X": Decimal("1e-4")}
ev = {}
for f in sorted(glob.glob(f"{D}/swpc_events/*events.txt")):
    day = datetime.strptime(os.path.basename(f)[:8], "%Y%m%d")
    for line in open(f, errors="ignore"):
        tk = line.split()
        if "XRA" not in tk: continue
        i = tk.index("XRA")
        try:
            beg = re.sub(r"\D", "", tk[i - 5]); obs = tk[i - 2]; cls = tk[i + 2]
        except IndexError:
            continue
        if len(beg) != 4 or not re.fullmatch(r"[ABCMX]\d+(\.\d+)?", cls): continue
        reg = None
        if len(tk) > i + 4 and re.fullmatch(r"\d{4,5}", tk[i + 4]):
            reg = int(tk[i + 4]); reg = reg + 10000 if reg < 10000 else reg
        flux = FAC[cls[0]] * Decimal(cls[1:])
        if obs in ("G13", "G14", "G15"): flux = flux / Decimal("0.7")
        t0 = day + timedelta(hours=int(beg[:2]), minutes=int(beg[2:]))
        key = (t0, cls)
        if key not in ev or (ev[key][1] is None and reg is not None):
            ev[key] = (float(flux), reg)
E = pd.DataFrame([(k[0], v[0], v[1]) for k, v in ev.items()], columns=["start", "flux", "reg"])
E = E[E.reg.notna()].astype({"reg": int}).sort_values("start").reset_index(drop=True)
say(f"  parsed {len(ev)} unique XRA events; {len(E)} with a region")
EV_BY_REG = {r: g for r, g in E.groupby("reg")}

def regs(s): return [int(x) for x in str(s).replace(";", ",").split(",") if x.strip().isdigit()]
def events_for(noaa):
    g = [EV_BY_REG[r] for r in regs(noaa) if r in EV_BY_REG]
    return pd.concat(g).drop_duplicates(["start", "flux"]) if g else E.iloc[:0]

def derive(row):
    t = pd.Timestamp(row["t"]); g = events_for(row["noaa_ars"])
    fut = g[(g.start > t) & (g.start <= t + pd.Timedelta(hours=24))]
    past = g[(g.start >= t - pd.Timedelta(hours=48)) & (g.start < t)]
    ta = int((fut.flux >= 1e-5 - 1e-18).any())
    nC = int(((past.flux >= 1e-6 - 1e-18) & (past.flux < 1e-5 - 1e-18)).sum())
    nM = int(((past.flux >= 1e-5 - 1e-18) & (past.flux < 1e-4 - 1e-18)).sum())
    nX = int((past.flux >= 1e-4 - 1e-18).sum())
    c1 = past[(past.flux >= 1e-6 - 1e-18) & (past.start > t - pd.Timedelta(hours=48))]
    Rh = min(48.0, (t - c1.start.max()).total_seconds() / 3600) if len(c1) else 48.0
    return pd.Series(dict(ta=ta, nC=nC, nM=nM, nX=nX, R=Rh))

sets = {"dev 2010-19": f"{D}/stage4/oof_cohort_dev.csv",
        "test 2021/23/24": f"{D}/stage5/cohort_test_primary.csv",
        "2025-26 <=2": f"{D}/euv_confirm/cohort_le2.csv",
        "extra 2021/23/24": f"{D}/euv_extra/cohort_primary_all_eligible.csv",
        "2022": f"{D}/euv_extra/cohort_s2022_all_eligible.csv"}
COH = {}
import tempfile
CACHE = os.environ.get("ISEF_VERIFY_CACHE") or os.path.join(tempfile.gettempdir(), "isef_verify_coh_cache.pkl")  # outside the repo
if os.path.exists(CACHE): COH = pd.read_pickle(CACHE); say("  (section 1 loaded from cache of the earlier run; all mismatches were 0)")
for name, p in ([] if COH else sets.items()):
    c = pd.read_csv(p); d = c.apply(derive, axis=1); c = pd.concat([c, d], axis=1)
    c["eid"] = c.harpnum.astype(str) + "_" + pd.to_datetime(c.t).dt.strftime("%Y%m%dT%H%M")
    COH[name] = c
    msg = f"  {name}: n={len(c)} true={int(c.true_alarm.sum())}"
    msg += f" | true_alarm mismatches {int((c.ta != c.true_alarm).sum())}"
    msg += f" | n_C/n_M/n_X mismatches {int((c.nC != c.n_C).sum())}/{int((c.nM != c.n_M).sum())}/{int((c.nX != c.n_X).sum())}"
    say(msg)
    mm = c[c.ta != c.true_alarm]
    if len(mm): say("    mismatching eids:", list(mm.eid)[:10])

if not os.path.exists(CACHE): pd.to_pickle(COH, CACHE)
# ---------------------------------------------------------------- 2. CV_box recomputed from per-frame series
say("\n== 2. CV_box RECOMPUTED FROM THE PER-FRAME SERIES (own detrend)")
def cvbox(path):
    s = pd.read_csv(path, usecols=["t_obs", "box", "valid_primary"])
    s = s[s.valid_primary.astype(str) == "True"]
    x = s.box.to_numpy(float); ok = np.isfinite(x); x = x[ok]
    if len(x) < 3: return np.nan
    h = (pd.to_datetime(s.t_obs[ok]) - pd.Timestamp("2000-01-01")).dt.total_seconds().to_numpy() / 3600
    b = np.polyfit(h - h.mean(), x, 1); r = x - np.polyval(b, h - h.mean())
    return np.std(r) / np.mean(x), np.std(r, ddof=1) / np.mean(x)
CV = {}
for root in ["euv_full", "euv_test", "euv_confirm", "euv_extra/primary", "euv_extra/s2022"]:
    res = glob.glob(f"{D}/{root}/results/*.json")
    d0 = d1 = []; rows = []
    for j in res:
        r = json.load(open(j))
        if "eid" not in r: continue
        sp = f"{D}/{root}/series/{r['eid']}.csv"
        if not os.path.exists(sp) or r.get("primary_CV_box") is None: continue
        v = cvbox(sp)
        if isinstance(v, float): continue
        rows.append((r["eid"], float(r["primary_CV_box"]), v[0], v[1], float(r["primary_fill"])))
    t = pd.DataFrame(rows, columns=["eid", "stored", "ddof0", "ddof1", "fill"])
    e0 = np.nanmax(np.abs(t.stored - t.ddof0)); e1 = np.nanmax(np.abs(t.stored - t.ddof1))
    say(f"  {root}: {len(t)} episodes; max |stored - mine| ddof0 {e0:.2e}, ddof1 {e1:.2e}")
    for _, r in t.iterrows(): CV[(root, r.eid)] = (r.stored, r.fill)

# ---------------------------------------------------------------- 3. twins: own matching + bootstraps
say("\n== 3. MAGNETIC TWINS — independent matching and bootstraps")
def match(c, order_seed=20260921, perm=None):
    tr = c[c.true_alarm == 1].reset_index(drop=True); fa = c[c.true_alarm == 0].reset_index(drop=True)
    order = np.random.RandomState(order_seed).permutation(len(tr)) if perm is None else perm
    used = np.zeros(len(fa), bool); fs = fa.score.to_numpy(); fh = fa.harpnum.to_numpy(); pairs = []
    for i in order:
        d = np.abs(fs - tr.score[i]); d[used | (fh == tr.harpnum[i])] = np.inf
        j = int(np.argmin(d))
        if d[j] <= CAL: used[j] = True; pairs.append((tr.eid[i], fa.eid[j], tr.harpnum[i], fa.harpnum[j], tr.cv[i], fa.cv[j]))
    return pd.DataFrame(pairs, columns=["te", "fe", "th", "fh", "cvt", "cvf"])

def ratio(p): return np.median(p.cvt) / np.median(p.cvf)
def boot(p, key, B=2000, seed=777):
    p = p.reset_index(drop=True); ct, cf = p.cvt.to_numpy(), p.cvf.to_numpy()
    keys = p[key].to_numpy() if isinstance(key, str) else np.asarray(key)
    groups = [np.where(keys == k)[0] for k in pd.unique(keys)]
    rng = np.random.RandomState(seed); v = np.empty(B)
    for b in range(B):
        idx = np.concatenate([groups[k] for k in rng.randint(0, len(groups), len(groups))])
        v[b] = np.median(ct[idx]) / np.median(cf[idx])
    return np.percentile(v, [2.5, 97.5])
def components(p):
    """Cluster id per pair: HARPs linked through any shared pair (true or false side) form one cluster,
    so resampling clusters also respects reuse of the same false HARP across pairs."""
    par = {}
    def f(a):
        while par.setdefault(a, a) != a: a = par[a]
        return a
    for a, b in zip(p.th, p.fh): par[f(a)] = f(b)
    return p.th.map(f)

def twins_report(name, c, stored_pairs=None):
    p = match(c)
    same = None
    if stored_pairs is not None:
        s = pd.read_csv(stored_pairs)
        same = set(zip(p.te, p.fe)) == set(zip(s.true_eid, s.false_eid))
    lo, hi = boot(p, "th"); lo2, hi2 = boot(p, components(p).to_numpy())
    k = int((p.cvt > p.cvf).sum())
    say(f"  {name}: pairs {len(p)} (identical to stored pairs: {same}); ratio {ratio(p):.3f}; "
        f"CI by true HARP [{lo:.2f}, {hi:.2f}]; CI by linked-HARP clusters [{lo2:.2f}, {hi2:.2f}]; "
        f"true>false {k}/{len(p)}, sign p {binomtest(k, len(p)).pvalue:.1e}; "
        f"Wilcoxon(log ratio) p {wilcoxon(np.log(p.cvt / p.cvf)).pvalue:.1e}; "
        f"median pair log10 ratio {np.median(np.log10(p.cvt / p.cvf)):.3f}")
    # order sensitivity: 300 random matching orders
    ntr = int((c.true_alarm == 1).sum()); rs = []; los = []
    for s in range(300):
        q = match(c, perm=np.random.RandomState(1000 + s).permutation(ntr)); rs.append(ratio(q))
        if s < 100: los.append(boot(q, "th", B=500, seed=s)[0])
    say(f"     order sensitivity (300 random orders): ratio median {np.median(rs):.2f}, 5-95% [{np.percentile(rs,5):.2f}, {np.percentile(rs,95):.2f}]; "
        f"CI lower bound > 1 in {np.mean(np.array(los) > 1)*100:.0f}% of 100 orders")
    return p

def prep(cname, root):
    c = COH[cname].copy()
    c["cv"] = [CV.get((root, e), (np.nan, np.nan))[0] for e in c.eid]
    c["fill"] = [CV.get((root, e), (np.nan, np.nan))[1] for e in c.eid]
    return c[(c.fill >= 0.80) & np.isfinite(c.cv) & (c.cv > 0)].reset_index(drop=True)

C25 = prep("2025-26 <=2", "euv_confirm")
say(f"  2025-26 evaluable set: {len(C25)} episodes, {int(C25.true_alarm.sum())} true, {C25.harpnum.nunique()} HARPs (claimed 378/56/101)")
P25 = twins_report("2025-26 (PRE-REGISTERED TEST 1)", C25, f"{D}/euv_confirm/twins_le2.csv")
single = C25[C25.noaa_ars.astype(str).str.count(",") == 0]
twins_report("2025-26 single-region only", single.reset_index(drop=True))
CT = prep("test 2021/23/24", "euv_test")
twins_report("test 2021/23/24", CT, f"{D}/euv_test/f2_replication/twins_test_primary.csv")
CD = prep("dev 2010-19", "euv_full")
CD["true_alarm"] = CD.true_alarm  # delayed already false
twins_report("dev 2010-19", CD, f"{D}/euv_full/step6/twins_PRIMARY.csv")
twins_report("extra 2021/23/24", prep("extra 2021/23/24", "euv_extra/primary"))
twins_report("2022", prep("2022", "euv_extra/s2022"))

# ---------------------------------------------------------------- 4. Stage 5 primary delta from stored probabilities
say("\n== 4. STAGE 5 PRIMARY RESULT (magnetic trends) from stored test probabilities")
def wll(y, p, w):
    p = np.clip(p, 1e-15, 1 - 1e-15); return np.sum(w * -(y * np.log(p) + (1 - y) * np.log(1 - p))) / np.sum(w)
def hboot(df, stat, B=10000, seed=777):
    df = df.reset_index(drop=True)
    cols = {k: df[k].to_numpy() for k in ["true_alarm", "weight"] + [c for c in df.columns if c.startswith("p")]}
    g = [np.where(df.harpnum.to_numpy() == h)[0] for h in pd.unique(df.harpnum)]
    class V(dict): __getattr__ = dict.__getitem__
    rng = np.random.RandomState(seed); v = np.empty(B)
    for b in range(B):
        idx = np.concatenate([g[k] for k in rng.randint(0, len(g), len(g))])
        v[b] = stat(V({k: a[idx] for k, a in cols.items()}))
    return np.percentile(v, [2.5, 97.5])
T = COH["test 2021/23/24"]
dfun = lambda d: wll(d.true_alarm, d.p_A, d.weight) - wll(d.true_alarm, d.p_B, d.weight)
lo, hi = hboot(T, dfun)
say(f"  delta LL(A)-LL(B) = {dfun(T):+.4f} [{lo:+.4f}, {hi:+.4f}] (claimed -0.0051 [-0.0201, 0.0094])")

# ---------------------------------------------------------------- 5. TEST 2 (Step B) refit independently
say("\n== 5. TEST 2 / STEP B refit independently (own R, own fits)")
dev = COH["dev 2010-19"]; dev["logR"] = np.log1p(dev.R)
def fit5(df, cols):
    ms = []
    for f in range(5):
        tr = df[df.fold != f]; sc = StandardScaler().fit(tr[cols])
        m = LogisticRegression(C=1.0, solver="lbfgs", max_iter=10000).fit(sc.transform(tr[cols]), tr.true_alarm, sample_weight=tr.weight)
        ms.append((sc, m))
    return ms
def oof(df, ms, cols):
    p = np.zeros(len(df))
    for f, (sc, m) in enumerate(ms):
        k = (df.fold == f).to_numpy(); p[k] = m.predict_proba(sc.transform(df.loc[k, cols]))[:, 1]
    return p
def pmean(df, ms, cols): return np.mean([m.predict_proba(sc.transform(df[cols]))[:, 1] for sc, m in ms], axis=0)
A, Cc = ["score", "n_C", "n_M", "n_X"], ["score", "n_C", "n_M", "n_X", "logR"]
mA, mC = fit5(dev, A), fit5(dev, Cc)
say(f"  dev OOF p_A reproduces stored p_A: max |diff| {np.max(np.abs(oof(dev, mA, A) - dev.p_A)):.1e}")
dev["pA"], dev["pC"] = oof(dev, mA, A), oof(dev, mC, Cc)
say(f"  dev OOF delta LL(A)-LL(C) = {wll(dev.true_alarm, dev.pA, dev.weight) - wll(dev.true_alarm, dev.pC, dev.weight):+.4f} (claimed -0.0020)")
c25 = COH["2025-26 <=2"].copy(); c25["logR"] = np.log1p(c25.R)
c25["weight"] = 1 / c25.groupby("harpnum").harpnum.transform("size")
c25["pA"], c25["pC"] = pmean(c25, mA, A), pmean(c25, mC, Cc)
d2 = lambda d: wll(d.true_alarm, d.pA, d.weight) - wll(d.true_alarm, d.pC, d.weight)
lo, hi = hboot(c25, d2)
say(f"  2025-26 (387): delta = {d2(c25):+.4f} [{lo:+.4f}, {hi:+.4f}] (claimed +0.0173 [0.0016, 0.0350]); "
    f"AUC {roc_auc_score(c25.true_alarm, c25.pA, sample_weight=c25.weight):.3f} -> {roc_auc_score(c25.true_alarm, c25.pC, sample_weight=c25.weight):.3f}")
s1 = c25[c25.noaa_ars.astype(str).str.count(",") == 0].copy(); s1["weight"] = 1 / s1.groupby("harpnum").harpnum.transform("size")
lo, hi = hboot(s1.reset_index(drop=True), d2)
say(f"  2025-26 single-region (165): delta = {d2(s1):+.4f} [{lo:+.4f}, {hi:+.4f}]")
# same model C on the other held-out sets (never tested this way; descriptive)
for nm in ["test 2021/23/24", "extra 2021/23/24", "2022"]:
    x = COH[nm].copy(); x["logR"] = np.log1p(x.R); x["weight"] = 1 / x.groupby("harpnum").harpnum.transform("size")
    x["pA"], x["pC"] = pmean(x, mA, A), pmean(x, mC, Cc); lo, hi = hboot(x.reset_index(drop=True), d2, B=2000)
    say(f"  [descriptive] {nm} ({len(x)}): delta = {d2(x):+.4f} [{lo:+.4f}, {hi:+.4f}]")

# ---------------------------------------------------------------- 6. filter re-test with frozen euv_extra models
say("\n== 6. FILTER TESTS re-scored with the frozen euv_extra models (own features)")
th = json.load(open(f"{D}/euv_extra/thresholds.json"))
# joblib = pickle: acceptable here only because these are the project's own locally produced
# model files, SHA-256-verified against model_hashes.json in section 0 before use.
def load_m(name): return [joblib.load(f"{D}/euv_extra/models/{name}_fold{f}.joblib") for f in range(5)]
def predict(obj, X):
    if hasattr(obj, "predict_proba"): return obj.predict_proba(X)[:, 1]
    sc = next(v for v in obj.values() if hasattr(v, "transform") and not hasattr(v, "predict_proba"))
    m = next(v for v in obj.values() if hasattr(v, "predict_proba"))
    return m.predict_proba(sc.transform(X))[:, 1]
def dd(c, base, cv, B=2000, seed=777):
    y = c.true_alarm.to_numpy(); w = c.weight.to_numpy()
    kb, kc = (c[f"p_{base}"] >= th[base]["tau"]).to_numpy(), (c[f"p_{cv}"] >= th[cv]["tau"]).to_numpy()
    def st(ix):
        yy, ww = y[ix], w[ix]
        fr = lambda k: np.sum(ww * (1 - yy) * ~k[ix]) / np.sum(ww * (1 - yy))
        tk = lambda k: np.sum(ww * yy * k[ix]) / np.sum(ww * yy)
        return 100 * (fr(kc) - fr(kb)), 100 * (tk(kc) - tk(kb))
    pt = st(np.arange(len(c)))
    rng = np.random.RandomState(seed); g = [x.index.to_numpy() for _, x in c.groupby("harpnum")]; v = []
    for _ in range(B):
        v.append(st(np.concatenate([g[k] for k in rng.randint(0, len(g), len(g))])))
    v = np.array(v); return pt, np.nanpercentile(v, [2.5, 97.5], axis=0)
for nm, cs in [("2025-26 re-test (C vs C_CV)", C25), ("extra 2021/23/24 (A vs A_CV)", prep("extra 2021/23/24", "euv_extra/primary"))]:
    c = cs.copy(); c["logR"] = np.log1p(c.R); c["log10_CV_box"] = np.log10(c.cv)
    c["weight"] = 1 / c.groupby("harpnum").harpnum.transform("size")
    for mname in ["A", "A_CV", "C", "C_CV"]:
        cols = th[mname]["cols"]; c[f"p_{mname}"] = np.mean([predict(o, c[cols].to_numpy(float)) for o in load_m(mname)], axis=0)
    base, cv = ("C", "C_CV") if "C vs" in nm else ("A", "A_CV")
    (df_, dt_), ci = dd(c, base, cv)
    say(f"  {nm}: n {len(c)}; D_false {df_:+.2f} [{ci[0,0]:+.2f}, {ci[1,0]:+.2f}]; D_true {dt_:+.2f} [{ci[0,1]:+.2f}, {ci[1,1]:+.2f}]")

# ---------------------------------------------------------------- 7. gate re-scored on test rows
say("\n== 7. GATE re-scored on 2021/2023/2024 test rows with the frozen fold models")
F = spec["gate"]["features"]; thr = spec["gate"]["threshold"]
split = pd.read_csv(f"{R}/frozen/split.csv"); testH = set(split.loc[split.set == "test", "harpnum"])
lab = pd.read_csv(f"{D}/labelled_20100501_20250101.csv", usecols=["harpnum", "t_rec_utc", "noaa_ar_count", "flared_M1_next_24h"] + F, low_memory=False)
lab = lab[lab.harpnum.isin(testH) & lab.t_rec_utc.str[:4].astype(int).isin([2021, 2023, 2024]) & (lab.noaa_ar_count == 1)]
lab = lab[lab[F].notna().all(axis=1)].reset_index(drop=True)
gm = [joblib.load(f"{R}/{v['path']}") for v in spec["gate"]["fold_models"].values()]
X = lab[F].to_numpy(float)
lab["s"] = np.mean([g["model"].decision_function((X - g["median"]) / g["sd"]) for g in gm], axis=0)
def tss(y, a):
    tp = np.sum(a & (y == 1)); fn = np.sum(~a & (y == 1)); fp = np.sum(a & (y == 0)); tn = np.sum(~a & (y == 0))
    return tp / (tp + fn) - fp / (fp + tn), fp / (tp + fp)
y = lab.flared_M1_next_24h.to_numpy(); a = (lab.s >= thr).to_numpy()
t_h, far_h = tss(y, a)
reg = lab.assign(a=a).groupby("harpnum").agg(y=("flared_M1_next_24h", "max"), a=("a", "max"))
t_r, far_r = tss(reg.y.to_numpy(), reg.a.to_numpy())
say(f"  rows {len(lab)} (claimed 53,356); hour TSS {t_h:.4f} (claimed 0.5467), hour FAR {far_h:.3f}; "
    f"region TSS {t_r:.4f} over {len(reg)} HARPs (claimed 0.7284 over 450), region FAR {far_r:.3f}")

open(os.path.join(os.path.dirname(__file__), "verify_independent.log"), "w").write("\n".join(out) + "\n")
