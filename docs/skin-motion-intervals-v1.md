# Skin movement bounds between sampled poses

The existing triangle-crossing diagnostic detects surface intersections at
discrete poses. Clear poses alone do not establish clearance between them:
rotating bones move vertices along curves, not straight lines between endpoint
vertices. `skin_motion_bounds.py` adds conservative speed and displacement bounds
for the actual hierarchy and linear-blend skinning used by `AnimationSampler`
and `RigAsset.vertices`. It does not change motion or certify animation quality.

## Construction and supported scope

Each requested interval is split at the union of native channel timestamps.
Within a span, translation has a constant derivative. Rotation follows the
sampler's shortest-arc SLERP or its small-angle normalized-linear branch. If the
angle between normalized, same-hemisphere quaternions is theta, the angular bound
is `4*tan(theta/2)/duration`; it bounds both branches. The angle uses an atan2
construction so different tiny rotations are not lost when a dot product rounds
to one. Channels outside their key ranges clamp as in the actual sampler.

For a node's world linear transform and translation, the implementation
propagates operator-norm, derivative-norm and translation-speed bounds through
the actual parent hierarchy. If parent bounds are M, D and V, local linear norm
is S, local angular bound is W, translation length bound is L and translation
speed is U, then the child bounds are:

```
M_child = M*S
D_child = D*S + M*W*S
V_child = V + D*L + M*U
```

Static matrix/scale drift is included in S. A skin influence with homogeneous
inverse-bind point `(p,h)` contributes at most `D*norm(p) + V*abs(h)` speed.
Nonnegative skin weights combine all influences; unskinned primitives use their
mesh-node transforms. The maximum per-vertex bound across native spans times
half the interval duration bounds displacement from the decoded center pose.
Each recurrence receives 1e-12 relative inflation and each radius receives
1e-10 m padding. These are explicit floating-point allowances, not exact interval
arithmetic or formally verified geometric predicates.

CUBICSPLINE, changing STEP channels and animated scale drift are rejected
explicitly. Constant STEP channels are supported. Arbitrary native key spacing,
clamped endpoints, constant scene placements, static scale drift and all supplied
skin influences are retained. The general bound supports multiple primitives;
the current paired audit adapter requires one primitive per actor. Moving scene
placements require their own motion bounds and are not accepted by this adapter.

`swept_surface_boxes.py` expands each triangle's vertex boxes with these radii
and streams all overlapping pairs through an R-tree. Zero pairs gives a surface
separation bound over that interval under the stated numerical assumptions.
Nonzero pairs are **unresolved**, not confirmed collisions. Counts are never
truncated; only the displayed examples are capped at sixteen. A contained object
can have separated boundaries while still penetrating, so vertex containment,
initial occupancy and self-collision checks remain necessary. Nothing is labeled
collision-free or quality-approved.

## Tests and actual decoded clips

All 805 minimal public Python checks pass. Nineteen new model-free tests cover tight translation bounds, rotating
hierarchies with moving joints and blended skin, inverse binds, unskinned mesh
vertices, different native clocks, clamping, quaternion sign and tiny angles,
static scale/homogeneous-bind drift, unsupported interpolation and invalid inputs.
A full-turn fixture has identical endpoint vertices but a large interior arc;
the bound contains it. A transit fixture has clear endpoints but is left
unresolved. Indexed candidate counts match exhaustive box comparisons.

`audit_interval_skin.py` binds source GLB hashes, explicit placements and requested
intervals before evaluation. It snapshots implementation files, checks seventeen
decoded poses per actor/interval against every vertex radius, records swept-box
outcomes and rechecks all bindings at completion. Sample replay validates the
implementation on those poses, not every possible continuous trajectory.

The first real audit uses the completed larger-trust hand study's two clips,
with the original actor placements and all 18,056 vertices per actor:

| Interval (s) | Candidate triangle-box pairs | Outcome |
| --- | ---: | --- |
| 0 to 0.008333333 | 0 | Surface separation bound |
| 1.9625 to 1.970833333 | 6,816 | Unresolved |
| 2.0625 to 2.070833333 | 16,401,274 | Unresolved |

All 102 decoded actor-pose replays remain inside their bounds: 1,841,712 vertex
observations. The largest observed displacement/radius ratio is 0.992742. The
largest radius across these actor/interval combinations is 33.167607 mm. The late
contact interval illustrates how loose broad-phase bounds can produce many
candidates; that count is not penetration, contact area or a realism score.

Local evidence:

- Protocol: `reports/skin-interval-protocol-v1.json`, SHA-256 `64412a5aacd69c634f591a7d462034481435db32bda12ee90c30905c2388ba5f`.
- Result: `reports/skin-interval-audit-v1/result.json`, SHA-256 `4ddf20ef3955a2d1c1234e3da788fdd750b78f944560d11d4da5c98379164945`.
- Intervals: `3598885546d07f549db250e1d024265e85d92b0ab439c1f6b23c5ff2577b216d`.

```powershell
.venv/Scripts/python.exe scripts/audit_interval_skin.py reports/skin-interval-protocol-v1.json reports/<fresh-output>
```

The protocol contains one or two actors with `name`, `path`, `sha256`, unit
`rotation_xyzw`, `translation_m`, plus `intervals_s` at the top level. Clip paths
resolve relative to the protocol. Local character payloads and reports remain
excluded from the public repository.

The [adaptive follow-up](adaptive-skin-intervals-v1.md) now combines bounded
subdivision with existing crossing and containment diagnostics, retaining
unresolved intervals when budgets prevent a conclusion. Full-clock, cubic/jump handling,
moving placements, self-collision and contact-quality policy remain open.
No new animation, training, held-out use or release approval is claimed.
