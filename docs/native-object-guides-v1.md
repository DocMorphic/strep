# Declared primitive guides for native scene fitting

`surface-vector` fitting now accepts declared boxes, spheres and cylinders.
`native_object_surface_rows.py` queries every original actor triangle against
every declared object at the geometry policy's clocks. Object poses remain
authored rigid trajectories; the solver edits only permitted actor tracks.

Whole-triangle depth witnesses become barycentric actor points with analytic
primitive support planes. This includes intersections missed by vertex-only
tests. Separated broadphase witnesses are discarded only after the complete
query, using the explicit proposal clearance. The row budget is shared with
partner and plane rows; exceeding it raises an error instead of returning a
partial population. Fixed witnesses are rebuilt after retained motion changes.

A primitive fully enclosed by an actor can have zero triangle penetration.
Its center therefore receives a separate nearest-boundary escape guide.
Containment requires an unchanged closed outward-volume actor mesh. Unavailable
containment or degenerate triangles stop proposal construction. Stable analytic
subgradients and deterministic escape directions are recorded as ambiguous;
they never replace uniquely defined authored grip normals.

Geometry ranking uses the existing triangle depth upper bound for objects whose
centers are outside. For an enclosed or near-surface center, it additionally
uses **primitive bounding radius plus positive center depth**. This is an escape
severity proxy, not measured penetration. It lets an enclosed primitive approach
the boundary without treating newly appearing triangle overlap as an automatic
ranking regression. The first score component is the largest severity divided
by the unchanged penetration limit. Subsequent components remain crossing count,
deep-vertex/enclosed-center count and failed conditions. Partner-only ranking
is unchanged. Reduced escape severity can coexist with increased triangle depth;
neither approves geometry or animation quality.

All original motion and point-contact constraints, individual oriented-contact
guards when enabled, worst geometry proposal bounds, exported scalar decoding
and complete geometry acceptance checks remain in force. Passing local support
planes cannot certify collision freedom. This adds proposal support, not solved
lifting, grasp attachment, partner physics or general object manipulation.

## Retained development checks

The saved humanoid sphere candidate keeps its exact source JSON and permissions.
Three explicit geometry clocks are 0, 3 and 5.9666666984558105 seconds. Each clock
checks all 36,108 actor triangles against both declared objects. Sampled object
geometry passes, and no active primitive guide is needed. Of 281,219 original
native conditions, 53 fail; maximum normalized excess is 1.0395263893. Fitting
is therefore not attempted. The existing hold failure remains visible.

A separate read-only diagnostic translates that sphere by exactly 10 mm toward
the nearest actor surface at 3 seconds, preserving its shape and all authored
key times. It creates 333 active guides, independently replayed from posed skin
vertices. Worst triangle depth is bracketed at approximately 7.9096991 mm;
geometry fails. This deliberately changed scene is not an improvement to the
original hold and has no solver or quality approval.

A separate synthetic closed-cube/sphere protocol runs one fitting iteration
with explicit prototype contact limits and unchanged source motion caps. No
step is retained. All 12 controls re-export byte-identical GLBs; replay checks
exact original cap arrays, decoded native conditions, full geometry scores and
all 10 rejection decisions. Start and final GLBs are identical. Native conditions
pass, object geometry fails, originals remain selected. This is pipeline evidence,
not humanoid realism evidence.

Local results live under ignored `reports/native-object-guides-development-v3`.
Its completion receipt binds 216 files, all rehashed during verification.
Earlier request-binding and verifier-path errors, and the initial 8,758 inactive
broadphase rows, remain in separate retained versions. Generated meshes and
study payloads are excluded from the public source repository.

Fourteen focused cases cover all three shapes, rotated support planes, moving
objects, all actor/object populations, whole-triangle interior witnesses,
enclosure, unavailable containment, nontruncating budgets and original-cap model
integration. Broader release evidence, engine playback and developer review
remain required; no release gate or formal held-out trial is marked passed.

All 482 related model-free regression checks pass in the recorded local run.
