# Region editing and fitting in Studio

The Scene interactions window now includes **Fit hand contacts**. Choose a saved native scene, an actor and one or more hand-to-object contacts. Edit inclusive start/end frames, the object-local grip coordinates, and the contact precision. Use an existing authored region or request a geometric palm-patch suggestion with a radius and selection angle.

Changing the patch, anchor mapping or limits creates a new authored condition. Suggested patches are not anatomical approvals. The saved preview stays unchanged while editing; a completed fit adds separate input and candidate scenes. Unsaved placement changes block submission so the worker cannot silently fit a different scene from the one displayed.

Drafts and the active job ID are retained locally when browser storage is available. Unavailable storage does not disable the editor. Job polling resumes after reload without automatically starting a replacement. Controls disable while a request is running.

## Job and result handling

New endpoints are `/api/scene-region-source`, `/api/scene-region-fits` and `/api/scene-region-jobs`. They use the existing Studio origin/host checks and single-worker dispatch. Sources must be registered saved scenes. Region requests may snapshot native motions under the project's `runs/` or `reports/`; neither arbitrary filesystem access nor a new public `runs/` route is added. Declared actor hashes, scene revisions, mesh identity, safe asset paths and contact schemas are checked before preparation.

Each job copies its actors, authored scene and implementation files before fitting. The worker rejects changed inputs or code, runs the [V14 fitter](scene-region-fitting-v14.md), then invokes the independent decoded export audit. It saves native measurements, source/candidate previews, GLB downloads, the audit and an assessment. The scene manifest is published only after the audit completes.

`complete` means the worker finished. `contact_geometry_passed` separately records whether selected-contact samples, full-skin object/floor samples and edit bounds pass. Speed and acceleration regressions remain separate warnings, and `quality_approved` stays false. The scene view also displays all saved contacts' native measurements, including contacts not selected for fitting. Naturalness and partner collision remain unevaluated.

## Verification

- 52 relevant Python tests pass; four unrelated full release-physics worker cases were excluded. Tests cover valid snapshots from original `runs/` sources, invalid revisions, path traversal, actor/contact mismatches, invalid intervals/surfaces/limits, changed snapshots and truthful failed-result summaries, plus existing authoring/audit and release-validation regressions.
- A Node test exercises the actual editor module with a minimal DOM and mocked transport: control IDs, unit conversions, draft capture, unsaved-placement rejection, submission, failed-result presentation and denied local storage. JavaScript and embedded Studio module syntax are checked.
- Two real worker runs exercise preparation through fitting, independent audit and saved scene packaging. The sphere fixture passes 34 contact and 17 geometry samples while retaining an acceleration-regression warning. The box fixture fails all 34 contact and 17 geometry samples, retaining speed/acceleration warnings. Both remain unreviewed candidates.

The real runs are retained locally under `reports/scene-region-jobs/studio-sphere-v1` and `reports/scene-region-jobs/studio-box-v1`, with their five-frame development inputs registered separately. These are the existing perturbation fixtures, not new action coverage or held-out trials.

Browser/localhost inspection was unavailable under the session's tool policy. No live browser click-through or rendered layout approval is claimed. The implementation, component behavior and workers were checked offline. A visual selection/painting tool for mesh regions, long-clip validation, broader motion/rig/object coverage and human review remain open. Existing release tools also still require their own supported contact/geometry conditions. All 14 project release capabilities remain unapproved.
