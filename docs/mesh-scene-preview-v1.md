# Saved character and object scene preview

Studio's imported-object contact editor now links each completed measurement job to a combined scene viewer. It loads the saved character clips and object placements, rather than the current mutable authoring draft. Arbitrary supplied humanoid clips are supported by this workflow; the validation examples are not an action whitelist.

## Use

1. In Studio's **Scene** window, import a static GLB and save a grip in **Object grip points**.
2. In **Characters**, prepare the native character scene and select the intended skin contact patch. In the imported-object contact editor, bind that scene, place the saved object, and add a touch or hold with explicit timing and limits.
3. Save the scene and use **Refresh measurements**. Once the guarded job completes, choose **View character and object together**.
4. Drag the view to orbit and scroll to zoom. **Frame scene** restores the camera framing. Clicking the canvas does not toggle character visibility.
5. Use the timeline or **Play** to inspect the shared animation. Choose a contact to see the blue character point, amber object grip and connecting gap line. **Largest saved gap** jumps to that contact's recorded worst position error.

The viewer opens in its own page and can be revisited through its job/result URL. An existing Studio process must load the updated server code before the new routes are available. This change does not launch a review server automatically.

## What the preview means

- Actors use the exact saved GLB hashes, explicit animation indices and rigid placements. Imported static meshes follow their saved translation and quaternion keyframes. Existing box/sphere/cylinder objects and declared planes are displayed too.
- Mesh-contact markers use the specified skin vertices and centroid/single-point reduction. Their targets use the saved canonical grip coordinates transformed with the object. The live display distinguishes times inside and outside the authored contact interval.
- A small live position gap does not imply the saved hold passes: relative speed and all declared samples still matter. The saved report's pass/fail result remains visible. Other native scene contacts are preserved in the package/report but do not yet have overlays in this viewer.
- The grid is only a reference. Declared infinite planes are drawn as finite translucent patches. Grey character materials override display materials; they do not modify source files.
- Camera framing samples 25 times and every character vertex at those times. This is a framing aid, not collision certification. The viewer limits combined source payloads to 128 MiB; it is not an offline installer.

## Skin convention and integrity

The contact measurement backend's `RigAsset` normalizes the total of all four/eight supplied influences per vertex. The preview follows that exact convention, recovering coefficients from untouched GLB bytes before Three.js can normalize only the first four. Original relative weights, joint assignments and inverse binds are retained; the in-memory coefficients are normalized across every influence together. No source asset or animation track is rewritten.

Both CPU markers and the graphics shader apply actor placement after skinning. The shader explicitly restores homogeneous position weight before that placement, avoiding an extra translation when Float32 coefficient sums differ slightly from one. Playback resets a clamped action before seeking, so scrubbing from the last frame to the beginning remains valid.

The descriptor and asset routes verify the completed job receipt, saved request, package member hashes and result hash. Asset paths are restricted to the package's named actor/prop GLBs. The browser checks downloaded asset hashes again. The seven measurement/parser implementation hashes must match the saved package; a changed sampling implementation requires remeasurement or the archived preview, rather than silently showing new results against an old report.

## Validation and limitations

The final automated evidence and resource receipts are retained locally under `reports/mesh-scene-preview-*`. Generated assets, screenshots, source epochs and failed investigations remain ignored by Git. Focused tests cover completed-job integrity, source/measurement changes, traversal rejection, explicit clip selection, all-influence normalization, translated mesh nodes, placement, object interpolation and backward scrubbing.

The first graphics stress study exposed a measurement-convention mismatch: raw non-unit weights produced a 0.75154-mm discrepancy against the backend's normalized skin. Both failed runs are retained. The final viewer follows the existing measurement convention; no backend thresholds or saved measurements were changed to make the preview pass.

Final local checks:

| Evidence | Result |
| --- | --- |
| `mesh-scene-preview-tests-v2` | 214 Python tests and three Node suites pass; sampled process-tree peak 155.0 MiB under a 512-MiB cap. |
| `mesh-scene-preview-browser-v2` | Actual Chromium/WebGL page and real Python dispatch, without opening a listening server. All 680 saved contact observations agree within 4.45e-16 m. Matching touch and deliberately missed hold retain their opposite results. Play/pause, canvas clicking, framing and endpoint/backward scrubbing pass without page or shader errors. |
| Full humanoid playback in that study | All 18,056 vertices at 120 native keys and 119 midpoints: 4,315,384 points. Peak difference from independent Python measurement skinning 2.441e-7 m; end-to-start peak 2.105e-7 m, both below the declared 1e-6-m check. |
| `mesh-scene-preview-gpu-v3` | Production skin shader executed into a floating-point render target. All 18,056 vertices at four times on the original humanoid and a deliberately translated/non-unit-weight derivative: 144,448 samples. Original peak 9.821e-7 m; stress peak 1.731e-6 m, both below the declared 1e-5-m check. The diagnostic changes raster positions for readback, not skinning calculations. |

The browser/full-body and shader workers reached sampled peaks of 625.7 and 471.2 MiB respectively, each below its 1-GiB cap. Each run retained the 600-MiB available-memory reserve and resource replay. The final progress replay independently reproduces the original contact arrays and gap/speed decisions, verifies current/source-epoch bindings, and checks the original release contract byte-for-byte except its permitted progress fields. These finite checks establish agreement on the tested assets; they are not a proof for every possible rig or graphics driver. Shader tests used Chromium's SwiftShader backend.

This is a preview and authoring improvement. It does not fit character motion, solve grasps, certify collision/physics, validate an engine import, or add semantic/animator approval. The existing high-five failures and all project release requirements remain. Next: expose explicit bounded correction for these saved scenes, then remeasure complete contacts and geometry before considering a candidate for export/review.
