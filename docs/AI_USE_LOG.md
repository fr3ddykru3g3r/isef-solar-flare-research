# AI-use and provenance record (factual)

PART 4 of the documentation update (decisions.md 8aa1797). Compiled 2026-09-28 by Claude (chat session) from git and decisions.md. This is a factual record for the students' own AI-use disclosure; it is not disclosure text.

## 1. From git

Counts are up to and including 4a0eb43 (PART 1, 2026-09-28 01:11 +0530), i.e. before this documentation session.

| item | value |
|---|---|
| commits | 223 |
| date range | 2026-09-21 00:34 → 2026-09-28 01:11 (+0530) |
| git author | all 223 under one local machine account (`93i5`); git does not record which student typed or approved each commit |
| trailer `Co-Authored-By: Claude Opus 5` | 90 commits |
| trailer `Co-Authored-By: Claude Opus 5.5` | 117 commits |
| no AI trailer | 16 commits, all on 2026-09-21 (mostly decisions.md entries); authorship not recorded in git |
| commits mentioning Codex | 1 (0ff1757: the `verification/` folder recorded as a pre-registration exploratory run by Codex) |

Commits made by this documentation session (all with trailer `Claude Opus 5.5`): 0117647 (PART 2), f060c86 (verification scripts + post-hoc region-reuse check), 39a4f20 (PART 3), and the PART 4 / PART 5 commits.

**Scripts added in commits carrying a Claude trailer (78):** `audit_2018_2020.py`, `audit_2024.py`, `build_dataset.py`, `checks.py`, `chunks.py`, `cohort.py`, `combo_t.py`, `completeness_check.py`, `descriptive_aia94.py`, `diag_ablation.py`, `diag_build.py`, `diag_d7.py`, `diag_d7_catalogue.py`, `diag_d7_cgem.py`, `diag_d7_vector_cost.py`, `diag_flare_rate.py`, `diag_operating_point.py`, `diag_patha.py`, `diag_patha2.py`, `diag_patha3.py`, `diag_persistence.py`, `diag_r.py`, `diag_rsplit.py`, `diag_swansf_validate.py`, `diag_testchecks.py`, `diag_uncertainty.py`, `empty_days_check.py`, `euv_cad.py`, `euv_check.py`, `euv_confirm.py`, `euv_confirm_retest.py`, `euv_confirm_tests.py`, `euv_counts.py`, `euv_dctrl.py`, `euv_descriptive_after.py`, `euv_dots.py`, `euv_explore.py`, `euv_extra.py`, `euv_f2_replication.py`, `euv_full.py`, `euv_heldout.py`, `euv_k3.py`, `euv_lnr4a.py`, `euv_masks.py`, `euv_novelty.py`, `euv_offset.py`, `euv_r4a_oppoint.py`, `euv_recharge.py`, `euv_run.py`, `euv_spatial.py`, `euv_step6.py`, `euv_test_download.py`, `euv_test_estimate.py`, `euv_validity.py`, `fetch_extra.py`, `flares.py`, `goes_xrs.py`, `join_report.py`, `make_split.py`, `nb_r4a_reanalysis.py`, `phase_f.py`, `posthoc_2026_09_28.py`, `prospective_measures.py`, `quality_report.py`, `run_all.py`, `sensitivity_combined.py`, `split_report.py`, `stage2_gate.py`, `stage3_cohort.py`, `stage4_models.py`, `stage5_test.py`, `stepA_dev.py`, `swpc.py`, `swpc_check.py`, `validate_swpc.py`, `verification/evaluate.py`, `verification/freeze.py`, `verify_facts.py`.

Note: `verification/evaluate.py` and `verification/freeze.py` were added in a commit with a Claude trailer, but decisions.md (0ff1757) describes `verification/` as an exploratory run by Codex.

**Scripts added in commits without an AI trailer (2):** `euv_download.py` (33fc1bd), `euv_pilot.py` (52c8c1f). Authorship is not recorded in git.

**Other AI-produced material outside the pipeline:**
- `docs/verification/` (independent re-derivation and region-reuse check): Claude chat, 2026-09-28.
- `docs/MODEL_REPORT.md`, `docs/PAPER_WRITING_KIT.md`, `Claude outputs/…REFERENCE_PAPER.*`, `video/` (plan and cards): Claude chat. These are not committed.
- Most figures in `figures/` dated 2026-09-27 were made by Claude chat scripts outside the repo (see docs/file_inventory.md).

## 2. decisions.md entries marked as drafted by AI

| date | entry heading | commit |
|---|---|---|
| 2026-09-26 | HELD-OUT REPLICATION OF F2: hypothesis ("wording drafted by Claude AI, reviewed and adopted by Lokesh") | 8420876 |
| 2026-09-26 | EXPLORATORY: THREE LOCALISED 94 Å AREAS (design drafted by Claude AI, adopted by the student) | bebbfe6 |
| 2026-09-26 | EXPLORATORY: TEMPORAL CONTRAST K3 (design drafted by AI, adopted by the student) | ae24e98 |
| 2026-09-26 | EXPLORATORY ROBUSTNESS CHECK: log R4a (design drafted by AI, adopted by the student) | 0043520 |
| 2026-09-26 | PRE-REGISTRATION — 2025–26 CONFIRMATION (TEST 1, TEST 2) | 749208e |
| 2026-09-26 | EUV-UNSEEN FOLLOW-UP VALIDATION — CV_box AS A FALSE-ALARM FILTER | 338c0aa |
| 2026-09-27 | EXPLORATORY — RECHARGE vs CLUSTERING TEST (design drafted by Claude AI) | 1d7d117 |
| 2026-09-27 | EXPLORATORY — PARASITIC-POLARITY "DOTS" NEAR THE PIL (design drafted by Claude AI) | dc080a8 |
| 2026-09-27 | EXPLORATORY — "NEW vs REPEAT" BRIGHTENING LOCATIONS (idea by the student; prompt drafted by Claude AI) | 912ac93 |
| 2026-09-27 | 2025–26 RE-TEST: CV_box AS A FILTER ON TOP OF MODEL C | 25fcd66 |
| 2026-09-27 | DESCRIPTIVE AIA 94 Å FOLLOW-UPS: alert tiers, noise/exposure/saturation check, calm-flarer profile | 947e4c0 |
| 2026-09-27 | SENSITIVITY: CV_box twins with magnetic + flare-history matching AND flare frames removed; image-only spike removal | 92027fa |
| 2026-09-27 | POST-HOC RE-ANALYSIS: B-class flare count + R4a | 68e57b1 |
| 2026-09-27 | PROSPECTIVE PRE-REGISTRATION: bursty fraction (BF) and late-window restlessness (CV6) | 2f62f88 |
| 2026-09-28 | PRE-REGISTRATION: C+ protection rule = the ONLY confirmatory false-alarm system | 8aa1797 |

Every other entry records who decided ("decided by: user" or "(me)" = Claude Code for implementation details). The phrase "reviewed and adopted by Lokesh" appears in the AI-drafted pre-registrations above.

## 3. Idea provenance

### 3a. Ideas stated by the user (recorded as stated by the user, PART 4 instruction)

| # | idea |
|---|---|
| 1 | Research topic and research question |
| 2 | PIL flicker hypothesis (the original EUV idea) |
| 3 | Extending the data to 2026 (the 2025–26 confirmation set) |
| 4 | Strong-gradient PIL / brightest core / sunspot masks (M1–M3) |
| 5 | Magnetic dots count |
| 6 | Overlay / new-pixel brightenings (new vs repeat, #24) |
| 7 | Background brightness |
| 8 | Area under the brightness curve |
| 9 | Removing flare frames |
| 10 | An AIA measure independent of flare counts and magnetics (the combined control) |
| 11 | "Are we testing too harshly?" |
| 12 | Checking prior small flares in missed true alarms |
| 13 | The C-flare protection rule and its C1.0+ (incl. M/X) version |
| 14 | Turning signals into a flare-probability ("chance") model |
| 15 | Removing the 12-h / C2 settings |

### 3b. Other measures and tests: proposer as shown in decisions.md

"Not recorded" means decisions.md records who *decided* (usually the user) but not who *proposed* the idea. No guess is made.

| measure or test | proposer as recorded | entry / commit |
|---|---|---|
| 24-h magnetic trends (Model B) and Stage 4/5 design | not recorded (Stage 4 details pre-registered; decided by: user) | b7f5ac0 |
| Control-pixel design fix CV_PIL − CV_ctrl | user ("from method reasoning"); control-mask rule: Claude Code | d164496 |
| Spatial measures R1–R4 (Phase X), incl. R4a "spikiness" | not recorded (decided by: user) | 85c8285 |
| Phase F items F2–F7, incl. the literature ratios in which CV_box twins first appeared | not recorded (requested by: user) | 5aaa8a3 |
| CV_box twins replication on the test years | hypothesis wording drafted by Claude AI; adopted by the student | 8420876 |
| Flare recency log(1 + R) (Step B, Model C) | not recorded (Step B pre-registered; decided by: user) | 9745de2 |
| K3 temporal contrast; log R4a | design drafted by AI, adopted by the student | ae24e98, 0043520 |
| Recharge vs clustering (#22) | design drafted by Claude AI, adopted by the student | 1d7d117 |
| CV_box as a false-alarm filter (unseen set; 2025–26 re-test) | wording drafted by Claude AI, reviewed and adopted by Lokesh | 338c0aa, 25fcd66 |
| Alert tiers, noise check, calm-flarer profile | wording drafted by Claude AI, reviewed and adopted by Lokesh | 947e4c0 |
| Bursty fraction BF and late-window CV6 (prospective) | wording drafted by Claude AI, reviewed and adopted by Lokesh | 2f62f88 |
| COMBO-T secondary model | not recorded (decided by: user) | 9a88d70 |
| HEK vs SWPC label comparison (Path A) | not recorded (decided by: user); prior work Hu et al. recorded | 2306cb3, 50c5895 |
| B&C reproduction diagnostics D1–D8, R1–R4 (reproduction) | not recorded (decided by: user) | e5305f7, 471021e, 3e04525 |
| Independent verification script; region-reuse sensitivity (post-hoc) | Claude AI (chat), 2026-09-28 | f060c86 |

## 4. Who did what, and what git cannot show

- Git and decisions.md record decisions and AI trailers. They do **not** record which of the two students (Kyros Goyal, Lokesh Chaudhary) proposed, ran or approved each step, except where an entry says "reviewed and adopted by Lokesh".
- The students' AI-use statement should therefore be written by them from their own knowledge, using this record for dates and counts.
