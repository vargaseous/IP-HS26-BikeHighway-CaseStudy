# End-to-end rerun summary — 2026-11-19/20 (Windows machine, uv environment)

Continuation of `IP_HS26_Reinvestigation/STATE.md` (reinvestigation handoff, macOS).
All Python executed via `uv run` (uv 0.13.1, Python 3.11.17 in `.venv`), never system Python.
Reports compiled with **tectonic 0.17.0** installed on this machine
(`C:\Users\joshu\AppData\Local\tectonic\tectonic.exe`, added to user PATH).

## What was done

1. **State inspection** (`cache/inspect_state.py`): NB02/NB03 artifacts were already fresh
   (surrogate rebuilt 2026-11-19 18:00, network cache `data/processed/bike_highway_detailed_network.pkl` present);
   NB04/NB05 notebooks still contained the pre-fix run. Overpass UA fix present in
   `transport_model_interface.py` lines 3395–3397; `validate_case_study.py` → **PASS**
   (surrogate_status=ready, response_table_status=ready, artifacts_ready=true).
2. **NB04 re-run #1** (2 requirements: `bike_share_trips > 0.20`, `bike_dist_km > 150_000`, yr 20):
   **109 s**, 36/36 cells, 0 errors.
3. **NB05 re-run #1**: **83 s**, 27/27 cells, 0 errors.
4. **Three-requirement rerun**: added `bike_share > 0.12 (yr 20)` back to NB04 cell 6
   (`cache/patch_nb04_reqs.py`) so NB05 receives all three active requirements, then re-ran
   **NB04 (75 s, 36/36, 0 errors) → NB05 (86 s, 27/27, 0 errors)** at 22:29–22:32 CET 2026-11-19.
5. **Distance threshold relaxed to 100k** (`cache/patch_nb04_100k.py`, git archaeology in
   `cache/git_arch*.py` showed it was only ever 150k/200k): **NB04 (68 s, 36/36, 0 errors) →
   NB05 (75 s, 27/27, 0 errors)** at 07:18–07:20 CET 2026-11-20. At 100k, req3 fails in
   99.3% (mean 15.5 yrs, was 100%/21 yrs at 150k), build plans meet ALL three requirements
   in 2/200 scenarios each, acceptable years 59–62.5%, and PRIM CSVs populate again.
6. **Verification** (`cache/verify_rerun.py`, `cache/verify_3req.py`, `cache/verify_100k*.py`,
   `cache/anomaly_scan.py`, `cache/audit2.py`).
7. **Report expanded + compiled here**: `reports/bug_report.tex` → `reports/bug_report.pdf`
   (71 KB) with tectonic 0.17.0; now includes the full git threshold-history table (§5) and
   the 100k results (§7–§8).

## Bug-fix verification (STATE.md acceptance criteria)

| Check | Before | After final 3-requirement rerun (22:29–22:32 CET) |
|---|---|---|
| `05_performance_requirements.csv` | 3 requirements but outcomes ignored `start_year` | **All three active**: `bike_share > 0.12 yr20`, `bike_share_trips > 0.2 yr20`, `bike_dist_km > 100000 yr20` (100k since 2026-11-20 07:19; was 150k) |
| `*_first_failure_year == 1` bug | present (failure from year 1) | **GONE** — every requirement's `first_failure_year` is exactly **20** (no `==1` anywhere in 1200 rows) |
| failure window | up to 40 failing years | max 21 = Years 20–40 only |
| stale figures in `figures/04|05` | several from pre-fix run | regenerated 22:30–22:32; only 3 intentionally not rewritten (degenerate PRIM sections) |

The start_year handover bug documented in `reports/bug_report.pdf` is confirmed fixed in the fresh outputs.

## Fresh headline results (final 3-requirement run: NB04 + NB05, 200 scenarios × 6 plans)

- **Req 1** `bike_share > 0.12, years 20–40`: failed in **82.2%**, mean 10.55 failing years, first failure always year 20.
- **Req 2** `bike_share_trips > 0.20, years 20–40`: failed in **34.8%** (418/1200), mean 5.27 failing years.
- **Req 3** `bike_dist_km > 100,000, years 20–40` (final, since 2026-11-20 07:20): failed in **99.3%**, mean 15.5 failing years (612/1200 rows fail all 21 years; 8 rows pass). Build plans fail it in 198/200 scenarios vs 200/200 for baseline/flexible; 26.1% of Year≥20 rows exceed 100k. At the previous 150k it failed 100% for 21 years (only 0.07% of rows ever exceeded 150k; model max 156,947, median ≈76k, p99 ≈133k bike-km/peak hour).
- **NPV (MCHF vs baseline)**: Static2 **+860**, Staged2 +650, Staged1 +648, Static1 +576 (all 100% positive); Flexible **−2.0** (0% positive); Baseline 0. Joint "positive NPV and requirements met": **1% for each build plan**, 0% for baseline/flexible (was 0% everywhere at 150k).
- **Waiting value** (`05_waiting_summary.csv`, now populated): flexible saves ≈41–50 MCHF discounted expenditure vs staged1/static2 but has NPV lower by ≈650–862 MCHF and +1.32 extra failure years on average — waiting is not worth it under these requirements.
- **PRIM un-degenerated**: 10/10 NB04 + 9/10 NB05 PRIM peeling/bounds CSVs freshly written at 100k (all skipped at 150k).

## Anomalies in the fresh outputs (audited)

1. **`bike_dist_km > 150,000` fails 100%** — not a bug: `bike_dist_km` is *bike-km per peak hour* (unit from `04_indicator_catalog.csv`), median ≈76k, max ≈157k. The 150k target is at the 99.9th percentile of modeled output. Consistent with the archived sweep (config D) where even 150k failed early in ~all scenarios. If a satisfiable distance requirement is wanted, threshold should be ≲100k.
2. **`congestion_delay_hours` up to 3.7e6** — this column is *person-hours/year* (catalog), not minutes/link; the earlier "2,900 min" artifact note applies to OD-delay surrogate errors, not this aggregate. No action.
3. **GP surrogate validation `passed = False`** (`results/03_uncertainty_modeling/03_surrogate_validation.json`, Oct 20 — unchanged by this rerun, NB03 was not re-executed here): OD `weighted_mae_min` = 1.06 min vs limit 0.1; `weighted_rmse_min` = 3.78 vs limit 0.2. Advisory warning only; `paired_appraisal.passed = True` and all appraisal-level checks pass (mode-share errors < 0.3 pp). Known BPR-clip artifact under extreme v/c, documented in the bug report.
4. **Empty `05_waiting_selected_*.csv` / `05_waiting_matching_scenarios.csv`** — still empty after the fix. Root cause: the "waiting value" filter needs scenarios where the adaptive plan's package openings differ from the reference build plans *and* the coupled comparison is material; with `bike_dist_km` failing in every scenario the requirement side saturates, so no scenario qualifies. Knock-on of anomaly 1, not a code bug (`passed=NaN` = "not material" sentinel by design).
5. **12 result CSVs not rewritten by the rerun** (8 in 04, 4 in 05 — all `*_prim_requirement_2_*_peeling/bounds.csv`, `05_6_value_and_price_of_waiting_*.csv`): these sections short-circuit when requirement 2 fails in 100% of cases (degenerate PRIM regime, no meaningful boxes), so the notebook skips writing them. 2 figures likewise not regenerated. Expected behavior for a saturated requirement, not staleness.
6. NB03 results/figures are from 2026-10-20 (not re-run in this session): per STATE.md the surrogate artifacts themselves were rebuilt 2026-11-19 18:00 (`data/processed/transport_surrogate/*`), and NB03 loads them with `REBUILD/REFRESH = False`, so its outputs are consistent with the current artifacts. A full NB03 re-execution would refresh only the analysis tables, not the model.

## Reproduce

```
uv run python code/validate_case_study.py
uv run jupyter nbconvert --to notebook --execute --inplace notebooks/04_adaptive_planning.ipynb --ExecutePreprocessor.timeout=10800
uv run jupyter nbconvert --to notebook --execute --inplace notebooks/05_appraisal.ipynb      --ExecutePreprocessor.timeout=10800
uv run python cache/verify_100k.py   # acceptance checks (final 3-req/100k state)
tectonic reports/bug_report.tex      # tectonic 0.17.0 at C:\Users\joshu\AppData\Local\tectonic
```
