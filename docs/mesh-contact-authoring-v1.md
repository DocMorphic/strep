# Editable target-mesh contacts

The full-project goal remains active. This adds contact authoring for the supported imported humanoid GLB subset; it does not establish general action correctness, physical support or release readiness.

In Studio Characters, select a completed motion and choose **Edit mesh contacts**. Add a named patch, pick visible mesh vertices (nearest vertex on the hit triangle), capture or enter a world target and add an inclusive frame interval. A patch can have several non-overlapping intervals. Select editable bones and hard root/rotation/edit-step limits, then **Fit authored contacts**. Fixed world targets are supported here; moving objects and partners use the separate scene workflow.

The editor verifies primitive topology and sample world positions against the exact exported GLB before accepting picks. Browser drafts are bound to its SHA256 and survive reload. Four- and eight-weight CPU picking are implemented, but this browser study exercised four-weight rigs only. The server independently validates all indices, intervals, joint ancestry, limits, frame counts and source hashes. Every job snapshots its exact input variant, original source, profile, authored spec and implementation. Editing an already corrected clip preserves that selected GLB as the new input. Source generation is never repeated by a contact edit.

## Measurements

All cases reuse previously examined seed-77 clips. These are engineering regressions, not held-out or animator-annotated trials. Thresholds stayed at 5 mm sampled floor penetration and 20 mm authored patch-centroid error, with the original root and joint edit budgets.

| Case | Floor before → after | Max target error after | Max coarse foot hover after | Outcome |
|---|---:|---:|---:|---|
| Quaternius female wave, six curved-sole points | 10.2 → 3.0 mm | 0.76 mm | 0 mm | Provisional numerical pass |
| Cesium get-up, head-clearance target with spine/neck/head edits | 167.0 → 3.7 mm | 13.7 mm | 92.6 mm | Limited screen passes; support regression |
| Same get-up, head plus predicted foot/toe contacts | 167.0 → 22.5 mm | 51.2 mm | 0 mm | Rejected: floor and target screens fail |

Wave patches are explicit single vertices selected by a recorded reference-geometry rule: lowest point in each weighted foot/toe heel/forefoot partition. This avoids assuming a flat sole but is not independently reviewed anatomy. Head clearance is a seven-frame diagnostic target around the worst penetrating head vertex, not a weight-bearing contact claim. The head-only candidate raises the root by up to 55.5 mm and changes Spine2 by up to 16.3 degrees. Coarse hover worsens from 43.0 to 92.6 mm. Adding predicted sole constraints removes that measured hover but causes other failures; the unchanged source predictions may themselves be incorrect. No candidate is approved for production.

A matched lower-body-only preflight, computed after the upper-body experiment, proves at least 47.0 mm of penetration unavoidable under the original root cap. This explains why additional editable upper-body joints were needed, without proving that the resulting motion is realistic.

## Reproduction and evidence

- Frozen initial requests and selection rules: `reports/mesh-contact-authoring-v1/request-manifest.json`, `*-selection.json`. Generator: `scripts/prepare_mesh_contact_study.py`.
- Initial actual jobs: `20260926-195412-bf0e8a1d` (wave, submitted through UI) and `20260926-195612-5047106e` (head clearance, local API).
- Adaptive follow-up: `20260926-195952-76bed1e3`, frozen in `upper-body-and-feet-get-up.json` with `followup-request.json`. Prepared after observing the head-only support regression; not a holdout.
- `comparison.json` retains all three outcomes. Initial and follow-up export verification are in `reports/mesh-contact-authoring-v1/verification.json` and `reports/mesh-contact-support-v1/verification.json`.
- All six served GLBs and all three ZIPs match saved hashes; every archived source/output entry checked. Reloaded GLBs reproduce metrics and edit limits, preserve unedited local rotations/nonroot translations, and match root tracks.
- Actual Godot import: 960 clip-frames across six files, 19/65 bones and every skinned surface. Maximum joint position difference is 4.33e-7 m. Evidence: `reports/godot-mesh-contact-authoring-v1/verification.json` and `reports/godot-mesh-contact-support-v1/verification.json`.
- All six GLBs have zero format errors; existing warnings remain (six for Quaternius, one for Cesium, concerning skinned-mesh ancestry and generated tangents).
- Full suite: 252 passed, four upstream Torch deprecation warnings. A test had initially contended with the real worker lock; it now uses an isolated temporary lock and exercises the same locking implementation. After the final worker metadata changes, the affected 23 tests pass. JS syntax checks pass.
- Real browser: visible vertex pick, captured world target, six-patch submission, corrected-variant binding, split intervals, per-joint changes, reload persistence and restored test drafts; worst-floor/hover navigation and rejected-result display verified. Evidence: `ui-verification.json`.

Open the results in Studio:

- [Curved-sole wave](http://127.0.0.1:8768/studio?character=6af075944be5d9d1881e8eb6722f275dbe4ea2ad46c71b0aa7d99b96b32e6523&rig_job=20260926-195412-bf0e8a1d)
- [Head clearance get-up](http://127.0.0.1:8768/studio?character=b7001eaeea8254bd44773bcd247e78696d94169388fbb2a1800fc69434e777d9&rig_job=20260926-195612-5047106e)
- [Combined-support failure](http://127.0.0.1:8768/studio?character=b7001eaeea8254bd44773bcd247e78696d94169388fbb2a1800fc69434e777d9&rig_job=20260926-195952-76bed1e3)

## Remaining work

Whole-body support needs a reviewed sequence of active surfaces and feasible targets; contradictory predicted foot contacts cannot simply be enforced harder. Add per-contact/worst-frame diagnostics, broaden hands/knees/torso support and independent rigs/actions, and evaluate continuous/self/object collision and naturalness. Also continue rough-clip editing, sequence/style controls, scene/partner correctness and clean offline installation. Independent animator ratings and cleanup-time trials remain required. No training, model changes or release approval occurred in this study.
