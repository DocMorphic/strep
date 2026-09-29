# Visual grip placement in Studio

In **Scene interactions → Fit hand contacts**, select an actor and contact, then choose **Pick grip on object**. Playback pauses and the preview scrolls into view. Click the selected contact's box or sphere to update its object-local grip coordinates. Escape or the same button cancels. Numeric entry remains available.

The purple marker shows the selected draft grip and a short line points inward along the surface normal. It follows the object's saved translation and rotation during playback, turning grey outside the draft contact interval. Excluded contacts and unsaved placement edits hide the draft marker. Picking selects only the contact's target object, even if another scene element overlaps it. It does not select hand triangles or move the character.

The ray intersects the analytic sphere/box in object-local metres. This avoids the sphere render mesh's chord approximation creating a point inside the surface. Box edges and corners have ambiguous normals and are rejected. The renderer, marker and picker share the same interpolated object pose; frames beyond the last object key retain its last pose. Coordinates are stored at full JavaScript precision rather than rounded to the numeric input's step.

The source scene and motion remain unchanged. Picked coordinates use the existing persisted draft and immutable fit-request path. Fitting still creates a separately audited candidate, and changed grip placement defines a new authored condition. A surface hit does not establish reachability, contact success or natural motion.

## Verification and limits

- 33 Python tests pass, including the existing saved-scene request and region-contact tests.
- The actual JavaScript geometry code checks 300 analytic hits across all six box faces and the sphere, at five transformed/interpolated poses. Python independently checks every result with the backend's `Geometry.local_surface_normal` contract.
- A Node interaction test uses real Three.js math and scene objects with a minimal canvas mock. It checks marker transforms and interval colour, misses, click-to-place, Escape, hidden/changed scenes, preserving disabled camera controls, disposal and source immutability.
- The actual editor component test verifies picked coordinates survive draft storage and submission; existing failed-result and unavailable-storage checks pass. Embedded Studio modules and standalone modules parse.

These are offline code/component checks, not browser or WebGL rendering approval. Live browser inspection remains unavailable under the session's earlier tool-policy restriction. No fitting experiment was repeated, no action coverage was added, and no release capability was promoted. Hand-region painting, arbitrary mesh-object targets, broad motion-quality validation and human review remain open.
