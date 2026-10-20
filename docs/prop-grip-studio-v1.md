# Object grip authoring in Studio

2026-10-20. The Scene window now includes **Object grip points**. Import a
self-contained static GLB, orbit its grey preview, choose **Pick grip**, click
the object, give the point a name and save it. The original GLB and each immutable
grip JSON can be downloaded. The displayed object ID reopens the same object and
its saved grips. This adds authoring access to the existing static-prop store;
it does not generate or approve a grasp animation.

The complete preview geometry comes from the backend's canonical transformed
vertices and triangles. This avoids translating a second loader's mesh/instance
ordering into saved face identifiers. The backend independently evaluates each
clicked triangle and barycentric point on its Float64 geometry before saving.
The GPU display uses Float32. Source coordinates, scene hierarchy transforms,
instance identity and source hashes remain attached to the selected point.
Winding normals are reported without claiming that they point outwards.

Changing the selected object invalidates pending picks and saves in the UI.
Late replies cannot restore an old point into the new object. Entering pick mode
clears the previous draft; Escape restores orbit controls. The original bounded
32 MiB / 200,000-vertex / 400,000-triangle intake remains unchanged. The new
geometry route uses the existing loopback host check and source-integrity checks.
Download matching now requires literal filename extensions. No source asset,
model weights, previously selected animation or release gate is changed.

## Verification

- `reports/prop-grip-ui-tests-v2`: **182 Python tests pass**, covering intake,
  actual API dispatch, transformed mirrored instances, geometry/point identity,
  saved downloads, source tampering, desktop rebuilds and existing mesh-scene
  evaluation/pose behavior. The editor's Node suite also passes import, reopen,
  saving, downloading, size rejection and asynchronous selection races.
- `reports/prop-grip-ui-browser-v2`: real Chromium/WebGL imports a self-created
  box, picks a face, saves a named grip, downloads the actual saved JSON, reopens
  the object and displays that grip. Framing and Escape work; no page errors.
  Requests are intercepted into the real Python dispatch and local files, with
  no listening server. This tests the mounted panel, **not a live full Studio
  session**. The saved screenshot was visually inspected. The complete desktop
  bundle's insertion, unique IDs and reproducibility are covered separately.
- Both completed guards and their resource journals replay. Python/Node tests
  peak at 145,416,192 sampled bytes under the 512 MiB cap; the browser process
  tree peaks at 568,807,424 bytes under its 1 GiB cap. Both retain the 600 MiB
  free-memory reserve and 15-second stable admission.
- The first browser attempt is preserved as failed: its Windows subprocess
  output decoding failed. The next version explicitly uses UTF-8 and the
  installed Chromium path, and fixes the generated box to use valid unindexed
  triangles. This is test-harness repair, not a relaxed product condition.
- The two new source suites are registered in the model-free CI inventory.
  Local results above do not assert completion of hosted CI.

Previous source bytes are archived against commit
`c1f84670cacc8874143164c4f486492add61541e` under
`reports/prop-grip-ui-source-epoch-v1`. Historical motion results remain bound to
their original implementations; they are not executions of this updated UI/API.

## Remaining integration

The saved point is an object-local intent landmark. Choosing an actor's hand,
placing the object in the scene, assigning contact times and running a bounded
correction still require the next authoring connection. The existing optional
mesh-scene evaluator can consume source-bound grips, but this panel does not
automatically submit a scene fit or infer attachment, load response, collision
clearance or animation quality. There is no new human review or cleanup-time
measurement. The latest high-five diagnostic still has 38 physical failures.
All fourteen release capabilities remain unapproved under the original full
project contract.
