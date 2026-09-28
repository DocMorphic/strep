# Audit-derived collision sampling

The completed screen-preserving trial left a 23.9373 mm full-clock penetration peak at frame 66.5 and introduced a failure at frame 69.5. Neither frame was in its fitting clock. The new development trial derives extra samples from the retained full audits instead of assuming that improvement on sparse samples protects the exported motion.

`contact_witness_clock.py` retains every original fitting sample, collects every sample exceeding the unchanged 5 mm collision screen from the raw, strict and screen-preserving curves, and includes each witness's adjacent half-frames inside the editable window. It reports failures outside that window explicitly. Missing, duplicate, reordered, nonfinite or negative data is rejected rather than silently filtered.

For the existing first seed, this expands 17 samples to **30**, adding frames 64.5, 65.5, 66.5, 67.5, 68, 68.5, 69, 69.5, 72, 72.5, 73, 73.5 and 74. No observed body-collision failure lies outside the fixed editable window in these inputs. This says nothing about the unchanged floor failures.

`run_enriched_surface_path.py` verifies both completed audits and their matched comparison before deriving and freezing this plan. It preserves the original initializer, raw body motion, authored fingers, five-control basis, joint/root edit limits, contact-region/orientation thresholds, three outer iterations and 60-iteration inner budget. It starts from the original initializer, not the preceding trial's final candidate. More samples mean more work and a larger set of surface constraints; equal iteration counts do not imply equal runtime.

The study is running in `reports/enriched-surface-path-v1`; its 22 implementation dependencies are frozen. `reports/enriched-surface-path-completion-v1` waits for its exact owner and then uses the existing export, decoded edit-budget, 600 actor-frame Godot and complete 299-sample-per-scene geometry audit. The outcome is not known yet. All attempted steps and failures remain in the study.

Seven focused sampling tests pass in 0.09 s. They cover use of every retained method, neighboring half-frames, preservation of the original clock, explicit uneditable failures, and invalid/incomplete data. Code compilation passes. These tests do not establish animation quality.

This is development refinement informed by prior failures, not held-out evaluation. New failures can still arise elsewhere or between samples, so the full exported audit remains mandatory. No quality threshold is relaxed, no floor repair is implied by the arm-only method, and no release or animator approval is claimed.
# Automatic full-clock comparison

The follow-up comparison is queued in `reports/enriched-partner-comparison-v1`. It waits for the exact enriched export/geometry worker to exit successfully, then independently reloads all three completed audits. It retains raw, strict, original-screen and enriched curves over all 299 integer/half-frame samples, verifies the unchanged initializer, raw assets, edit limits, selection thresholds and iteration budgets, and regenerates the sampling plan from the retained predecessor failures.

The report separates new failures inside the fitting clock from new failures outside it, lists cleared and worsened frames, and records the unchanged or changed floor curve. A lower peak cannot conceal a new collision. Nine targeted tests pass, including omitted witnesses, changed budgets/thresholds/inputs and an improved peak with a new off-clock failure. The actual 17-to-30-sample protocol preflight passes; candidate results remain pending. See `reports/enriched-partner-comparison-tests-v1.json`.

The larger clock takes more work under the same iteration budget. This comparison does not claim equal wall time, held-out evidence, continuous collision coverage or human quality approval.
