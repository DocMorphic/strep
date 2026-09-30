# Paired corrections in the Studio authoring workflow

The [refreshed partner comparison](coupled-refreshed-pair-v1.md) is now available in Studio as two saved scenes, rather than only as standalone research GLBs. Reload Studio, open **Scene interactions**, and select **Partner correction: preserved clearance · Before** or **After**. The original 150-frame duration, both actor placements, authored contact intent, body correction and finger layer are retained.

The scenes include actor downloads, sampled geometry and a ZIP containing both actors on the shared Godot playback clock. They use the existing source-bound developer-note workflow. This creates no human ratings or cleanup-time evidence. Neither version is approved: both still fail the 5 mm partner-clearance screen at 24 of 57 inspected times.

## Exact assets and continued editing

The publisher requires matching completed study, complete sampled geometry and all-frame engine evidence for each actor. Changed placement, assets or evidence are rejected. The two input GLBs and two corrected GLBs are copied exactly. Native SOMA77 arrays are reconstructed from those exports, including the authored finger rotations, so later edits do not reopen an older motion source.

Independent canonical-skin reconstruction checks all **600 actor-frames** against the actual GLB skin. Maximum component error is **0.330 micrometres**. Original foot-contact channels remain inherited model predictions, not new stance annotations. This publisher currently handles actor-only A/B SOMA77 scenes; it does not qualify arbitrary rigs or add a general paired-motion solver.

Collision summaries keep their exact fractional sample times and declared coverage, frames 63–77. Failed samples remain visible. The partial-interval audit is not presented as a full-clip, continuous-collision or naturalness certificate. Known floor defects remain unresolved.

## Timing edits and actual engine playback

A real Studio production job retimes the corrected pair from 150 to 225 frames, then a second job trims frames 50–160 to 111 frames. Both actor placements remain unchanged. The contact's exact time becomes frame **62.751677852**, with native solver enclosure [62, 63]; it is not silently rounded to one key. Original scenes and job snapshots remain intact.

Four paired versions—before, after, retimed and trimmed—pass **1,455 shared-scene pose observations** in headless Godot. Each observation contains both actors. Tests cover all bone transforms, shared seeking, automatic forward/reverse playback, ordered event notifications, terminal behavior and rejection of mutation during callbacks. Maximum actor-matrix discrepancy is below 1.08e-6. Authored events are notifications, not verified successful contacts.

The retime/trim workers recompute contact and motion diagnostics. They retain floor depths of about 8.27 mm and 10.66 mm for actors A/B. Old collision evidence is not reused as an approval of the edited animation, and changing playback speed does not re-simulate gravity or forces.

The first workflow probe stopped after the retime job succeeded because the probe assumed a `candidate.json` filename. It now resolves the published file from the job manifest. The completed retime was reused only after matching its exact request and immutable input hashes; no replacement was silently launched. The earlier probe and completed job remain preserved.

## Fractional-frame preview repair

The integration exposed a real preview bug: jumping to a worst-overlap sample such as frame 66.75 indexed a native contact-marker array with a fractional key. Actor animation uses the exact GLB curve, while marker positions now interpolate between native samples. Their displayed gap is explicitly labeled approximate between frames; interpolation is not collision evidence.

Integer-only editing controls floor the selected start/release sample and ceil the trim end. “Note here” encloses fractional times with an integer review range. Integer samples and endpoints retain their original values. Offline tests execute the actual contact-point function at frame 66.75 with both actors, as well as the editor handlers and note capture.

## Evidence and reproduction

**33 Python tests and four offline Node checks pass.** New summary and fractional-preview checks join public Windows/Linux CI. Collection discovery was tested by invoking the actual Studio handler directly, and ten download/scene routes resolve correctly. No socket, browser rendering or human review was used for these checks.

Local outputs are `reports/scene-region-jobs/paired-refreshed-review-v1`, `reports/scene-trim-jobs/paired-studio-workflow-v1-retime`, `reports/scene-trim-jobs/paired-studio-workflow-v2-trim` and `reports/paired-studio-workflow-v2`. They remain excluded from GitHub with licensed assets and model weights.

```powershell
.venv\Scripts\python.exe scripts/package_paired_correction.py reports/paired-pose-posture-v1/body_fit_posture-seed-1301.json reports/coupled-pair-continuation-v1 reports/coupled-pair-continuation-geometry-v1 reports/coupled-pair-continuation-engine-v1 reports/coupled-pair-refreshed-v1 reports/coupled-pair-refreshed-geometry-v1 reports/coupled-pair-refreshed-engine-v1 reports/scene-region-jobs/<new-review> --label "Partner correction comparison"
.venv\Scripts\python.exe scripts/verify_paired_studio_workflow.py reports/scene-region-jobs/<new-review> reports/<new-workflow>
```

Use fresh output names and the separately acquired local dependencies. This connects a measured correction to editable scene assets; it does not make the current one-pair research solver a reusable Studio fitting tool. That request/solver integration and broader partner/action coverage remain next work. All fourteen release capabilities remain unapproved.
