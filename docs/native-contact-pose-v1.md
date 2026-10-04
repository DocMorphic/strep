# Bounded native contact-pose diagnostic

`scripts/native_contact_pose.py` tests an explicit single-pose relaxation before attempting a complete motion correction. It edits only declared existing LINEAR rotation channels on supplied rigs. It supports active world, rigid-object and actor-surface contacts and retains every active authored point or centroid group. It does not infer anatomical hands, choose contact regions or output an approved animation.

```python
from native_contact_pose import ContactPose, fit

problem = ContactPose(scene, surface_policy, contacts_sha256, exact_time_s, permissions)
controls, search = fit(problem, evaluations=60, maximum_seconds=240,
                       maximum_calls=3000, geometry_penetration_m=0.005)
residuals, contacts, worlds, vertices = problem.measure(controls)
```

`scene` is an already validated `SceneContacts` instance, and the surface policy binds its exact source JSON. This is a Python API; a portable command and Studio integration are not provided by this change.

Permissions bind that same JSON and explicitly name actors and native rotation nodes:

```json
{
  "schema": "strep-native-contact-pose-permissions-v1",
  "contacts_sha256": "<exact source JSON SHA-256>",
  "actors": {
    "A": {
      "rotation_tracks": [{"node": 15, "maximum_change_degrees": 5.0}],
      "maximum_joint_displacement_m": 0.02
    }
  }
}
```

The example node is a supplied rig reference, not a universal hand index. Unknown, repeated, static or non-LINEAR tracks reject. Existing public native edit maxima apply: 45 degrees per source-relative rotation and 0.22 m joint displacement. A pose probe's chosen permissions do not replace the original clip's permissions or motion caps.

For each declared rotation, physical correction is `limit * raw / sqrt(1 + dot(raw, raw))`. Every visited vector stays strictly inside its rotation-norm ball; component clipping is not substituted for that bound. Corrections right-multiply the original local rotation. Local translations, unselected local rotations, placements, object trajectories and skin weights remain unchanged. Joint displacement is a measured violation condition, not a hard parameterization bound. Unpermitted actors retain their exact source world transforms.

Contact measurements use full source skin and complete incident-face populations with the original area/coherence reliability conditions. Target normals follow their explicit world/object coordinates or the partner's actual posed skin. Invalid normals remain unavailable and receive a positive violation; reports use JSON null rather than fabricated directions or nonstandard numeric values. Point distance, normal opposition, both facing-side projections and source-relative joint displacement remain separate conditions.

Least-squares fitting minimizes positive normalized violations and a small control regularizer. All source skin vertices against every declared primitive provide a geometry guide. That guide can miss triangle crossings or primitive enclosure; it cannot establish full geometry acceptance. The retained candidate minimizes maximum positive guide/condition violation, then squared violation, over every evaluated vector, including derivative evaluations. The seed and rejected search history remain measurable. Passing source conditions can regress during this diagnostic search; no optimizer flag permits promotion.

Explicit evaluation, objective-call and elapsed-time budgets bound the search. A stopped search retains its best visited vector and records exhaustion, without reporting solver success. Failure to find a witness is not proof that body/hand correction is impossible.

A pose result is still a temporal relaxation. Native key clocks, protected poses, velocity/acceleration caps, transition continuity, full collision, self-collision, imported CPU/GPU skin, dynamics and anatomical/human review remain separate. The existing motion solver and engine checks remain necessary before using a corrected animation. Original clips stay selected.

## Validation

Twenty-two model-free synthetic tests check hard rotation balls, independent source skin reconstruction, agreement with the existing normal audit, unchanged local translations and unselected rotations, source-relative geodesic rotation limits, world/object/partner coordinates, exact unpermitted actors, invalid permission rejection, unavailable normals and explicit search budget exhaustion. A synthetic pose objective can improve without implying motion or geometry acceptance.

## Retained sphere-hold probe

At 3.914583333 seconds, the probe keeps the same ten correspondences, sphere targets, 15-degree normal limit, 5 mm point limit and 0.5 mm facing allowance. Twelve explicit forearm, wrist and first-finger channels receive source-relative 45-degree pose permissions and a 0.22 m joint displacement condition. These are newly declared single-pose diagnostic permissions within the public edit maxima, not replacement permissions or acceptance limits for the original clip.

The seed and candidate use the canonical source GLB reader. That reader normalizes supplied skin weights on import; fitting adds no further weight normalization and does not edit the GLB. This epoch differs from the earlier Godot observations using raw imported weights. Their normal numbers must not be interchanged. The original selected grip vertices are mostly weighted to joints named LeftHandPinky1 and RightHandPinky1; names and weights are not anatomical annotations.

The bounded search reaches its 60-evaluation limit after 103.532 seconds and 1,644 objective calls. Its retained worst positive normalized violation falls from 2.060035 to 0.716226. Solver success is false; a valid pose witness is not found.

| Contact group | Seed point error | Candidate point error | Seed normal error | Candidate normal error |
| --- | ---: | ---: | ---: | ---: |
| Left grip | 2.015470 mm | 3.648831 mm | 15.427090 degrees | 4.991140 degrees |
| Right grip | 2.007782 mm | 4.389283 mm | 14.701341 degrees | 5.070717 degrees |
| Left neighbours | 4.678915 mm | 5.043094 mm | 47.083186 degrees | 25.889631 degrees |
| Right neighbours | 4.676915 mm | 5.010963 mm | 46.548447 degrees | 25.835627 degrees |

All ten normals remain available. The largest declared rotation change is 29.962932 degrees, inside the probe's 45-degree bounds. Neighbour point and normal conditions still fail. The separate complete mesh audit at the two unchanged endpoints and the probe pose covers all 18,056 vertices, 36,108 faces and both declared spheres. The probe pose fails with 5.478753 mm of triangle-depth upper bound against the unchanged 5 mm geometry limit. Both object centers remain outside. There is no ground plane or partner in this retained development scene. Three isolated poses are not a corrected animation, a temporal geometry certificate or the original 2,201-time scene trial.

Independent replay reconstructs the full hierarchy with Rodrigues rotations, scalar skinning and all ten complete incident-face populations. Contact measurements and six saved geometry reductions agree, and all 656 positive sphere witnesses at the probe pose reproduce their analytic depths. Complete collision and containment queries are not rerun; anatomy, self-collision, native curve/rate limits, import and human quality remain unverified. No candidate clip is exported or selected.

The actual solve's immutable archived version reports SciPy's evaluation-limit stop accurately in its message and count, but its generic budget flag only covered the explicit time/call callback. Current source fixes that flag and adds separate evaluation/time-or-call fields; a regression test verifies exhaustion at one evaluation. Numerical pose code, objective and solver call remain unchanged, as verified against the archive. The solve is not repeated to rewrite its metadata. An initial private driver setup failure and a Float32 replay-helper mismatch are retained separately; both are corrected without changing the measured targets or producer pose.

All 50 focused pose/surface checks pass locally and in a fresh source-only copy without vendor code, models or character assets. Local evidence: `reports/native-contact-pose-development-v1`, `reports/native-contact-pose-verification-v1`, and `reports/native-contact-pose-clean-source-v2`. The subsequent [protected pose search](guarded-contact-pose-v1.md) preserves passing contact conditions and audits complete triangle geometry before retaining each backoff. This original trial cannot justify weakening limits or claiming body correction is infeasible. All 14 release evidence lists and acceptance fields remain unchanged. The full project goal remains active.
