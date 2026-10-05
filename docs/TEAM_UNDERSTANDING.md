# Team understanding guide: Same Magnetic Field, Different Fate

For Kyros Goyal and Lokesh Chaudhary. Use it as a quiz: one of you asks, the other answers aloud without notes, then check the model answer. Tick a section only when **both** of you can explain it. Numbers match the revised reference paper and docs/RESULTS_SUMMARY.md (28 Sep 2026).

| section | Kyros | Lokesh |
|---|---|---|
| The whole project in one minute | ☐ | ☐ |
| Introduction: question, hypotheses, what is new | ☐ | ☐ |
| Data: magnetic records, flare labels, EUV images | ☐ | ☐ |
| Methods: gate, alarms, restlessness, twins, tests | ☐ | ☐ |
| Results: what passed, what did not, what it means | ☐ | ☐ |
| Discussion: physics, limits, the hard questions | ☐ | ☐ |
| Conclusion, AI use, next steps | ☐ | ☐ |

## 1. The whole project in one minute

**Key points**

- Problem: our magnetic forecaster (the “gate”) catches 87% of flaring regions on years it never saw, but 6 of every 7 alarm episodes are false (268 of 313).
- Idea: pair each true alarm with a false alarm the gate scored almost the same, a “magnetic twin”, and compare how much the hot corona (AIA 94 Å) flickered in the 24 h before: “restlessness”, CV_box.
- Main result: in the test whose rules were logged in advance and run once on 2025–26 data, the flaring twin was the more restless in 39 of 50 pairs; median ratio 3.26 (pre-registered 95% CI 1.30–9.49).
- Caveat you must be able to explain: regions repeat across pairs; resampling both sides gives 0.86–12.2, so it is a clear pattern, not proof.
- Use: restlessness cannot delete alarms (1 in 4 true alarms was calm) but can grade them: WARNING 26–32% vs WATCH 2–8% followed by a big flare (descriptive).
- Also: a known catalogue defect (reported by Hu et al.) makes 34 true alarm episodes look false; a prospective test of the C+ rule is registered (Look 1 not before 10 Nov 2026, Look 2 not before 15 Mar 2027).

**Questions a judge may ask**

1. **Explain your project in two sentences.**
   <br>*Model answer:* Magnetic flare forecasts raise many false alarms, so we compared true and false alarms that the magnetic model scored as equally dangerous. In a test with rules fixed in advance, the region that went on to flare had the more restless hot corona in 39 of 50 pairs, which suggests coronal flicker carries information the magnetic score misses.

2. **What exactly is your main result, with its uncertainty?**
   <br>*Model answer:* 39 of 50 twin pairs; median restlessness ratio 3.26 with a pre-registered 95% CI of 1.30–9.49 (pairs resampled by flaring region). Because some regions appear in several pairs, a post-hoc interval that resamples both flaring and non-flaring regions is 0.86–12.2. The direction is consistent (14 of the 18 flaring regions were more restless than their twins in most of their pairs), but the statistical margin is modest.

3. **Which parts did each of you do?**
   <br>*Model answer:* Answer this yourselves, specifically and truthfully (who proposed which idea, who ran or checked which step, who wrote which section). Judges score both team members’ understanding and contribution. docs/AI_USE_LOG.md lists the ideas the diary records as yours.

## 2. Introduction: question, hypotheses, what is new

**Key points**

- TSS = hit rate − false-alarm rate. It ignores how rare flares are, so a high TSS can hide many false alarms. That is why we also report precision and false-alarm ratio.
- The useful comparison for forecasters is alarm vs alarm (dangerous vs dangerous), not flaring vs quiet regions.
- H1 twins ratio > 1 with CI lower bound > 1; H2 flare recency improves log-loss with CI above 0; H3 a filter that keeps true-alarm losses within 10 points (three reading levels).
- Not new: EUV precursors, flare-imminent vs flare-quiet comparisons (Leka et al.), two-stage false-alarm removal (Deshmukh et al.). New: testing 94 Å variability conditionally among alarms matched on a frozen magnetic score, on later years, with rules fixed in advance and an explicit veto test.

**Questions a judge may ask**

1. **Why doesn’t a TSS of 0.73 mean your forecast is good?**
   <br>*Model answer:* TSS does not depend on the base rate. Flares are rare, so even a small false-positive rate produces many false alarms compared with true ones. Our gate’s region-level TSS was 0.73, yet 6 of 7 alarm episodes were false. Camporeale & Berger make the same warning about operational forecasts.

2. **Leka et al. already compared flare-imminent and flare-quiet regions in AIA. What is new in your work?**
   <br>*Model answer:* Their flare-quiet epochs are simply not followed by a flare, like our false alarms, so the idea of comparing is not new. What we add is the conditioning: we compare only alarms that a frozen magnetic model scored almost identically, test on later years under rules logged before the test, and check whether the signal can veto alarms (it cannot).

3. **Is your 3.3× comparable with Kniezewski et al.’s effect size?**
   <br>*Model answer:* Not directly. They studied variability in other AIA channels with a different measure and design, so the direction agrees but the numbers cannot be compared one to one.

4. **State H3’s three reading levels.**
   <br>*Model answer:* Confirmed safe: the lower CI bound of true alarms lost is at least −10 points. Meets the operating criterion: only the point estimate is at least −10. Loses too many true alarms: the point estimate is below −10.

## 3. Data: magnetic records, flare labels, EUV images

**Key points**

- SHARP hourly keywords, QUALITY = 0, within ±45° of central meridian; 254,899 labelled rows for 2010–2024.
- Flare labels from NOAA SWPC daily reports (they keep the region number); GOES-13/14/15 fluxes ÷ 0.7 to the true-flux scale (changed 4,170 of 27,219 classes); four validation checks.
- The HEK copy loses region numbers (AR = 0) for many recent flares. Hu et al. reported this first; we measured its effect: region FAR 0.543 → 0.724, and 34 of 386 alarm episodes in 2021–24 look false.
- AIA 94 Å (Fe XVIII, ≈ 6–7 MK) cutouts every 12 min for the 24 h before each alarm; ≥ 80% valid frames; ≈ 186,000 images, ≈ 90 GB.

**Questions a judge may ask**

1. **Why did you use SWPC reports and not the HEK flare list?**
   <br>*Model answer:* Our labels need the region that flared. The HEK copy has region = 0 for many recent flares (for example 173 of 195 M1+ flares in 2022). SWPC keeps the region. Scoring the same frozen alarms with HEK labels raises the region false-alarm ratio from 0.543 to 0.724 and turns 34 true alarm episodes into apparent false alarms.

2. **Why divide GOES-13 to -15 fluxes by 0.7?**
   <br>*Model answer:* NOAA/NCEI recommend the true-flux scale; the older satellites’ operational fluxes were scaled by 0.7. Without the correction, classes near a boundary would be mislabelled across satellite generations. It changed the class of 4,170 of 27,219 events.

3. **Why is 2020 excluded and 2022 only a sensitivity set?**
   <br>*Model answer:* 2020 had no M1+ flare with a usable region. 2022 fell just below the pre-set 90% region-completeness rule (89.7%), so it is reported but never used as a main test.

4. **Why the 94 Å channel, and why 12-minute cadence?**
   <br>*Model answer:* 94 Å is dominated by very hot plasma (about 6–7 MK) in active-region cores, which responds to small heating events, and earlier studies found it informative. The 12-minute cadence was fixed on development data before labels were used: it agreed with 2-minute cadence (ρ = 0.95, but n = 8, CI 0.62–1.00) and kept the download feasible.

## 4. Methods: gate, alarms, restlessness, twins, tests

**Key points**

- Gate: RBF support vector machine on 10 SHARP features (Bobra & Couvidat style), threshold −0.9925 chosen by max out-of-fold TSS on 2010–19, then frozen and hash-checked.
- Alarm episode: consecutive alarm hours of one region (gaps ≤ 3 h), judged at time t; true only if the same NOAA region gives an M1+ flare in (t, t + 24 h]. Weighted 1/n per region.
- CV_box = SD(brightness − straight-line trend) ÷ mean brightness over 24 h of 12-min frames.
- Twin = false alarm from another region with gate score within 0.0747 (0.2 SD); order fixed by seed 20260921. It controls the model’s danger score, not every magnetic feature.
- All tests on later years, region bootstrap CIs, rules committed to an append-only git log before each test; the final tests were run once.

**Questions a judge may ask**

1. **What is a magnetic twin, and what does it control for?**
   <br>*Model answer:* For each true alarm we take the false alarm from a different region whose gate score is closest, within 0.0747. Because both got nearly the same magnetic danger score, a difference between them cannot come from that score. It does not make the two magnetic fields identical; individual SHARP features can still differ. “Same magnetic field” in the title is shorthand.

2. **Why weight each episode by 1/n for its region, and why bootstrap regions?**
   <br>*Model answer:* Long-lived regions produce many episodes that are correlated with each other. Weighting stops them dominating, and resampling whole regions gives honest intervals. Resampling single episodes would pretend they were independent.

3. **Why fix the matching order with a seed?**
   <br>*Model answer:* Greedy one-to-one matching depends on the order in which true alarms pick their twins. Fixing it in advance removes a choice we could otherwise tune. We later re-ran 300 random orders: the pre-registered order gave the lowest ratio (median 3.55), and the lower CI bound stayed above 1 in 81% of orders.

4. **What does “pre-registered” mean here, and why run a test only once?**
   <br>*Model answer:* The hypothesis, data set, statistic and pass rule were committed with a timestamp to an append-only, version-controlled log before the result was computed. Running once stops us from trying variations until one passes.

5. **Why test on later years instead of a random split?**
   <br>*Model answer:* A forecast has to work on the future. Random row splits put hours of the same region in both training and test sets, which inflates skill: in our ablation, development TSS rose from 0.679 to 0.790.

6. **What is log-loss, and what does Δ mean?**
   <br>*Model answer:* Log-loss punishes confident wrong probabilities; lower is better. Δ = LL(base) − LL(new), so a positive Δ favours the new model.

## 5. Results: what passed, what did not, what it means

**Key points**

- Starting point: gate region TSS 0.728; 6 of 7 alarm episodes false; magnetic 24-h trends added nothing (Δ −0.0051, CI −0.0201 to +0.0094).
- Main result: 39/50 pairs, 3.26 [1.30, 9.49]; first held-out test 2021/23/24 only 1.31 [0.94, 2.22] (direction consistent, not confirmed).
- Robustness (post-hoc): flare history matched and flare frames removed 2.73 [1.10, 6.20]; noise ≈ 1% of CV_box; weaker on the unseen set and 2022.
- Flare recency (Model C): Δ +0.0173 [+0.0016, +0.0350]; a more recent C flare raises flare probability (odds ratio 0.74 per SD of log(1 + R)).
- Veto fails (−14 and −16 points of true alarms); grading works descriptively; the C+ rule is exploratory until its prospective test.

**Questions a judge may ask**

1. **Why are 39 of 50 pairs not 39 independent successes?**
   <br>*Model answer:* The 50 pairs reuse 18 flaring regions (up to 7 pairs each) and 41 non-flaring regions (up to 4 each), and 8 regions appear on both sides at different times; 47 pairs are linked into one group. The pre-registered interval resamples only the flaring side (1.30–9.49). A post-hoc interval resampling both sides is 0.86–12.2 and includes 1. So we say: direction consistent, statistical strength modest. A sign test on 50 pairs would overstate it.

2. **Your first held-out test did not confirm. Why believe 2025–26?**
   <br>*Model answer:* We don’t hide it: 2021/23/24 gave 1.31 [0.94, 2.22], “direction consistent, not confirmed”. The 2025–26 test passed its pre-stated rule, and the ratio was above 1 in every set, but the range 1.31–3.26 across sets is a real limitation. We did not prove why it differs (set size, solar-cycle phase and region mix are possibilities).

3. **Couldn’t restless regions simply be ones that just flared?**
   <br>*Model answer:* We matched twins on flare history and removed every frame during a recorded flare: 2.73 [1.10, 6.20], 34 of 47 pairs. Instrument noise is about 1% of CV_box. But the strict version was weaker on the unseen set (1.34) and 2022 (2.78), both CIs including 1, and restlessness correlates with recent C flares (ρ = 0.57). So flare activity is part of the story, not all of it.

4. **What does Model C show?**
   <br>*Model answer:* Adding log(1 + hours since the last C1+ flare) improved 2025–26 log-loss by 0.0173 (CI 0.0016 to 0.0350). The coefficient was negative in all five folds: the more recent the last flare, the higher the chance of another. It is real but small: the development estimate was slightly negative and the single-region subset’s CI includes 0.

5. **Why can’t you just delete calm alarms?**
   <br>*Model answer:* About 1 in 4 true alarms was calm beforehand (27%, 19%, 25% in the three EUV test sets). Both pre-registered filter tests lost more than 10 points of true alarms (−16.2 and −14.0), and thresholds frozen on 2010–19 do not transfer across the solar cycle.

6. **Are WARNING and WATCH a proven improvement?**
   <br>*Model answer:* No. They were defined after the filter results, so the 26–32% vs 2–8% split is descriptive. A proper claim would need its own pre-registered test on new data.

7. **What is the C+ rule and why is it not a result?**
   <br>*Model answer:* Keep an alarm if the restlessness model keeps it or if the region had a C1.0+ flare in the previous 24 h. We designed it after looking at the data, so its good numbers (for example +7.9 points more false alarms removed on 2025–26) are exploratory. The confirmatory test uses flares from 2026–27 and cannot be read before 15 March 2027.

## 6. Discussion: physics, limits, the hard questions

**Key points**

- Physical idea (a hypothesis, not tested): regions heading for a big flare release energy in many small heating events that make hot plasma flicker.
- Region-wide, not concentrated at the polarity inversion line; control pixels did at least as well as the whole box.
- Biggest limits: region reuse and small samples; many ideas tried; archival not prospective; several 2025–26 tests without multiplicity correction; operational value unproven.

**Questions a judge may ask**

1. **What might cause the extra flicker physically?**
   <br>*Model answer:* Our hypothesis is many small energy releases (pre-flare brightenings) heating coronal loops before the main flare, consistent with Leka et al. and Dissauer et al. We measured only brightness variation, so the mechanism is untested.

2. **Random control pixels separated twins better than CV_box. Why keep CV_box?**
   <br>*Model answer:* CV_box was fixed before the test years were used and needs no magnetic mask or random draws. Switching to the better-looking measure after seeing results would be a post-hoc choice and would weaken the pre-registration.

3. **Name your three biggest limitations.**
   <br>*Model answer:* 1) The pairs reuse regions, so the statistical margin is modest (0.86–12.2 when both sides are resampled). 2) Many ideas were tried and the 2025–26 test used archival data; only the C+ test is truly prospective. 3) No method beat Model C with a log-loss CI excluding zero, and thresholds drift across the solar cycle.

4. **Did you correct for multiple comparisons?**
   <br>*Model answer:* No formal correction across H1, H2 and the filter re-test on 2025–26. Each had its own pass rule fixed in advance, and we list the missing correction as a limitation.

5. **Why is a three-times ratio not enough to veto alarms?**
   <br>*Model answer:* It compares medians of two groups whose distributions overlap. The calm true alarms sit right in the false-alarm range (median 0.069 vs 0.072 in 2025–26), so any cutoff that removes many false alarms also removes them.

## 7. Conclusion, AI use, next steps

**Key points**

- Conclusion in one line: among equally dangerous alarms, the ones that flare tend to have a more restless hot corona, but not reliably enough to delete alarms.
- AI wrote nearly all code and drafted pre-registration wording; an independent script re-derived the headline numbers from raw flare reports and saved light curves (not raw FITS images).
- Next: the prospective C+ test, a pre-registered test of the grading, higher cadence and spatially resolved EUV, thresholds that adapt to the solar cycle.

**Questions a judge may ask**

1. **What exactly did the AI do, and how did you check it?**
   <br>*Model answer:* Claude Code wrote and ran nearly all analysis code and drafted the wording of the pre-registrations, which we reviewed and adopted. Claude chat proposed some candidate ideas and post-hoc checks and drafted a reference version of the paper. We checked the code with an independent script that shares no code with the pipeline and re-derived the headline numbers. Then say precisely what you two did: which ideas were yours, which decisions you made, what you checked by hand.

2. **If you had six more months, what would you do?**
   <br>*Model answer:* Run the prospective C+ test (Look 2 after 15 March 2027); pre-register a test of the WARNING/WATCH grading; measure variability at 12-second cadence and in smaller areas; recalibrate thresholds as the cycle changes. Testing a similar signal with Aditya-L1 data is an idea, not a claim.

3. **What was the hardest decision in the project?**
   <br>*Model answer:* Answer from your own experience. Honest examples judges like: keeping CV_box after the control pixels looked better, reporting the ambiguous 2021–24 test, and deciding not to delete calm alarms.
