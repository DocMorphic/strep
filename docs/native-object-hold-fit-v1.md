# Bounded two-grip object trajectories

An explicit object-edit request can now fit one rigid object's trajectory to two
authored held grip points while keeping every actor GLB byte-identical. The
saved proposal is checked against all scene contacts, original-relative object
pose budgets and complete sampled actor/object/partner geometry. This is an
experimental CLI authoring operation; Studio defaults are unchanged.

## Request and checks

The source uses `strep-native-scene-contacts-v1`. A separate request binds its
exact SHA-256, names one declared object and two distinct existing contact IDs,
and specifies an enclosing edit window, translation/rotation budgets and key
budget. Both contacts must be holds on that object with the same complete
interval and one point correspondence each. An explicit centroid is supported.
Different intervals, missing IDs and oversized complete clocks reject the
request rather than silently shortening its scope.

```json
{
  "schema": "strep-native-object-hold-fit-v1",
  "contacts_sha256": "<SHA-256 of contacts.json>",
  "object": "prop",
  "contact_ids": ["left-grip", "right-grip"],
  "edit_window_s": [1.5, 4.5],
  "maximum_translation_m": 0.002,
  "maximum_rotation_degrees": 2.0,
  "maximum_keys": 3601
}
```

```powershell
python scripts/native_object_hold_fit.py contacts.json request.json geometry-policy.json reports/new-object-hold
```

The fitting clock includes both exact hold endpoints, actor and object native
keys in the hold and all twelve absolute 30/60/120 Hz phase populations. The
output also includes original object keys, edit-window endpoints and 120 Hz
ingress/egress keys. A two-point rigid fit aligns the grip axis with the measured
skin points and aligns their midpoints. Incompatible point separations leave
residual error; the original contact caps still decide acceptance. Twist left
unobserved by two points follows the reference orientation.

Quintic weights return the pose correction to zero outside the edit window.
Original authored keys outside that window retain their exact JSON values.
Other objects, contacts, actor placement, animations, geometry and bytes remain
unchanged. Only the selected object's keyframes are replaced in a separate
proposal JSON. No source animation or implicit attachment is overwritten.

The saved JSON is reopened before evaluating contacts; interpolation of the
actual saved rigid poses is authoritative. Geometry includes every loaded actor
triangle and declared actor/object, actor/partner and world-plane condition.
Its clock includes the original geometry-policy clock and every new object key;
`native-and-frame-populations` policies additionally retain their full expansion.
Pose budgets are evaluated on that expanded clock. Contact and geometry clocks
remain separate, explicit finite populations; this is no continuous-time proof.
Original limits, frame populations and source files are not relaxed.

Every run requires a fresh output directory and records authored snapshots,
unchanged actor snapshots, implementation hashes, source bindings, proposal
observations, contact observations, complete per-triangle geometry arrays and
separate pass/fail results. Failed proposals remain available for inspection;
the original remains selected and quality, training and release approval stay
false. The pure rigid-fit kernel imports without model dependencies; the legacy
motion auditor loads its model-specific helpers only when invoked.

## Development evidence

The retained humanoid sphere hold uses the same source clip as the previous
[individual-contact repair study](native-contact-repair-v1.md). It has 53 failed
right-grip speed rows despite passing point distances. A diagnosis on all 1,033
hold clocks separates actual object-local error from the chord through native
keys: only 0.11317 mm of between-key curvature accounts for almost all of the
worst 10.19763 mm/s speed. Good native-key positions therefore did not imply a
stable hold during interpolated poses.

This follow-up explicitly permits editing the object trajectory. It does not
change or approve the prior actor-only trial, whose object path was fixed. The
new request allows 2 mm translation, two degrees of rotation, a 1.5–4.5 second
edit window and at most 3,601 keys around the complete 2–4.0333333015 second hold.

| Saved proposal measurement | Result |
| --- | ---: |
| Object keys and complete geometry sample times | 1,266 |
| Maximum original-relative object translation | 0.994770 mm |
| Maximum original-relative object rotation | 0.014456 degrees |
| Maximum left/right grip position error | 2.001215 mm each |
| Maximum left/right held speed over all twelve populations | 3.076664 mm/s each |
| Original contact limits | 5 mm, 5 mm/s |
| All saved contact, sampled pose-budget and geometry conditions | Pass |
| Actor GLB bytes | Unchanged |

The geometry audit includes all 36,108 actor triangles against both declared
objects at every expanded sample time: 2,532 complete actor/object observations.
Both centers remain outside the unmodified closed actor volume, and depth upper
brackets remain below the unchanged 5 mm limit. No partner or world plane is
declared in this case; this result cannot establish partner or floor clearance.
Frozen poses outside the edit window differ by at most 3.47e-18 in the measured
components. These are finite sampled results, not continuous bounds.

Saved replay independently regenerates all 1,266 object key values, reopens the
proposal, reproduces every stored proposal/contact array exactly, recomputes
every contact distance and frame-population speed, and checks the complete
saved per-triangle depth-array reductions for all 2,532 observations. It binds
the raw files, original inputs, actor bytes and archived/current implementation
hashes. The expensive full geometry query is not redundantly rerun for replay;
its original observations and containment results remain recorded separately.

Ignored evidence is retained under `reports/native-sphere-clock-diagnosis-v1`
and `reports/native-object-hold-development-v1`. The source contact JSON SHA-256
is `59fc7f796ec40e42569dacfb5535c345851ef4d62a82c822127ec888e36f59a9`;
the unchanged actor GLB SHA-256 is
`aa650e4a9199ab356f54015b5b346bdca4da80db102aae9a690fb841bb69b5da`.
No new model inference or training data was used.

Eighteen focused regression cases cover box/sphere/cylinder trajectories,
complete clocks, saved interpolation, unchanged actor bytes, invalid requests,
resource-budget rejection, visible pose-budget failures, snapshots and isolated
model-free kernel imports. The two existing rigid-fit tests cover known poses,
incompatible hand separation and antipodal/degenerate axes.

All 512 related model-free regression checks pass in the recorded local run.

This operation does not establish grip normals, wrist orientation, forces,
balance, physical attachment/release, object/object collision, self-collision,
continuous collision freedom, engine playback or animation quality. It is not
a newly trained checkpoint, a general grasp solver or release approval. Added
object keys are deliberate authoring output; export into Float32 game-asset
tracks still needs separate saved-interpolation and clock-quantization checks.
