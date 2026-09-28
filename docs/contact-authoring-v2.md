# Contact authoring and hard limits — development status

2026-09-26. This work belongs to the active project-wide goal in `docs/project-goal.md`; it is not a completed product or a separate completed goal.

Implemented a versioned contact specification, independently evaluated targets, and a new solver in `scripts/support_contact_v2.py`. The original support solver and frozen studies remain unchanged. The new solver bounds root lift to 0–22 cm and each edited local joint's rotation-vector change to 40 degrees **relative to the input body candidate**, not relative to the original model pose. These are edit budgets, not anatomical joint limits. Smooth parameter maps enforce them during optimization; independent checks account for float32 export rounding. Contact/collision objectives remain soft and may fail.

Contact specifications use schema 1, 30 fps, an exact source frame count and per-region modes: inferred, disabled, or explicit. Explicit intervals include both endpoints, must be ordered/disjoint/in-range, and accept either an original surface trajectory raised to 2 mm floor clearance or a fixed world-space point. Each explicit interval pins a fixed surface vertex; it does not silently change vertices when the character rotates. Invalid coordinates, region/vertex mismatches and overlapping intervals are rejected before optimization. World points are in metres, Y-up and currently constrained to the floor-support domain. Objects/partner frames are not yet represented.

The example in `benchmarks/contact-authoring-example-v1.json` disables the inferred head support and authors two left-hand intervals for get-up seed 11. These choices are an engineering workflow fixture, **not independent animator annotations** or a claimed better contact plan. All other regions retain their inferred constraints. Source geometry and previous measurements remain available.

Run an edit into a fresh directory:

```powershell
.venv\Scripts\python.exe scripts/run_contact_edit.py reports/body-contact-v1/takes/get-up-seed-11 benchmarks/contact-authoring-example-v1.json --output reports/my-contact-edit
.venv\Scripts\python.exe scripts/evaluate_contact_spec.py reports/my-contact-edit/takes/get-up-seed-11
node scripts/validate_body_exports.mjs reports/my-contact-edit
```

The first result is retained in `reports/contact-authoring-v2`. Root lift stays between 0.022 mm and 13.13 cm. Independent full-skin evaluation finds maximum requested-point errors of 6.10 mm (frames 55–58) and 2.05 mm (frames 85–92), both inside the pre-existing provisional 3 cm contact target. This checks those point targets only. Five broader regression flags remain: left-hand gap, left-foot sliding, torso/head/right-elbow gaps. The disabled head hypothesis intentionally differs from the old geometric audit, which remains visible rather than being silently removed.

The candidate and copied limb GLBs validate with no errors/warnings; every candidate GLB frame and all eight weights, BVH roundtrip, source/artifact/ZIP hashes, unchanged root XZ and predicted contacts, and actual exported root track are verified. A full 90-test suite passed, followed by all 11 focused contact-spec tests after adding two independent measurement checks. No fresh seeds, new training, new rig validation or animator review were performed.

## Studio integration (2026-09-26)

Inspector now provides a contact editor for body-corrected takes: select a region, automatic/disabled/source-following/world-pin mode, inclusive start/end frames and world coordinates. Save multiple disjoint intervals, edit/remove rules and apply the plan. Drafts persist per collection/take. Jobs use the same local worker lock as generation, retain source/raw/limb/previous versions and open a new result collection. Invalid/overlapping intervals and malformed requests are rejected. Results include independent target error measurements and preserve other regression flags; missing targets are flagged. The editor is currently available on body-corrected collections, not arbitrary newly generated raw clips.

A real browser-submitted crawl-seed-22 edit pinned the left-hand surface vertex at [0.401077384, 0.002, 1.177305514] metres for frames 33–40. The result is in `reports/contact-jobs/20260926-150000-bfa9171e/result`: maximum target error 3.7 mm, zero out-of-tolerance frames (8 tested), zero current numerical regression flags. This is an engineering workflow test, not independent naturalness/physics validation. Both exported candidate and copied baseline GLBs validate; hashes, ZIPs, unchanged inputs, hard budgets and root/contact tracks are verified. Browser checks covered submission, automatic result opening, draft persistence, target measurements and rejection of reversed intervals.

Contact workers record process identity. A confirmed missing/reused process fails an unfinished job instead of leaving it indefinitely marked running; terminal results remain available after server restarts. Same-origin loopback submission and artifact path restrictions remain in force.

Early contact exports inherited source sequence diagnostics. `scripts/finalize_contact_metadata.py` recomputed those diagnostics from edited poses for the original example and browser job, preserving prior evidence under `metadata-original` and recording the amendment. No motion arrays changed. Future runs compute these metrics directly. Original implementation snapshots for these runs are retained in `source-snapshot`.

The suite now has 108 passing tests (four upstream Torch JIT deprecation warnings). Scene-target groundwork is documented in `docs/scene-constraints-v1.md`; the next implementation is visual scene authoring and calibrated grip/palm targets, then scene-targeted correction/constrained generation.
