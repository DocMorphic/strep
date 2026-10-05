# Surface-aware native transfer calibration

`scripts/native_transfer_surface_calibration.py` extends whole-clip reference
calibration with authored contact-facing conditions and decoded scene geometry.
It uses the original source clip, target rig and transfer profile. Each output
is a separate candidate; original assets and selection remain preserved.

## Authoring contract

Begin with a verified native transfer scene comparison. Bind two additional
policies to its exact `contacts.json`: a `strep-native-surface-contact-v1` policy
covering every contact, and a `strep-native-scene-geometry-v1` policy declaring
the geometry clock, tolerances and world planes. World/object normals are
explicit author choices. Partner normals follow the exact reviewed target
vertices and complete incident-face winding. They do not identify palms or
infer anatomical correctness.

```json
{
  "schema": "strep-native-transfer-surface-calibration-v1",
  "comparison": {"path": "comparison", "sha256": "<result.json SHA256>"},
  "surface_policy": {"path": "surface.json", "sha256": "<policy SHA256>"},
  "geometry_policy": {"path": "geometry.json", "sha256": "<policy SHA256>"},
  "actors": {
    "A": {
      "role_rotations_degrees": {"LeftHand": 15},
      "maximum_root_offset_m": 0,
      "maximum_joint_displacement_m": 0.02
    }
  },
  "search": {"evaluations": 60, "calls": 400, "seconds": 90, "starts": 1}
}
```

```powershell
python scripts/native_transfer_surface_calibration.py recipe.json new-output
```

This is a CLI authoring path; Studio integration remains open. Existing native
transfer restrictions and author bounds apply. Targets, vertex correspondences,
contact timing, object motion, placements, original target clips and mesh/skin
payload stay protected. New policy files rebind only the derived contacts
checksum. Their normals, thresholds, planes and clocks stay exact.

## Correction and acceptance

The original necessary reach preflight still rejects incompatible fixed targets
without optimization. The least-squares objective now includes normal opposition
and signed facing-side conditions at every complete common contact time, in
addition to point/slip errors and original joint-displacement/rate bounds.
Unavailable normals cannot silently become passing conditions. Area and
coherence thresholds retain all incident faces. The existing 0.1% inward search
reserve applies to point and orientation targets; final readback uses the
unchanged authored limits.

The complete proposed normal population is counted before queries. It must fit
the explicit actor-pose limit and fixed 100,000 scalar normal-row limit. Planned
geometry observation scalars must fit 256 MiB. Exceeding a budget rejects the
full population; no body patch, partner, frame or condition is dropped.

After export, separate audits measure full loaded actor topology against every
actor/object pair, both directions of partner containment/crossing and every
declared plane at the complete policy clock. Geometry guides are not part of
the optimizer. A point/facing success with failing or unavailable geometry is
retained as a failed candidate. `sampled_authoring_conditions_pass` requires
all exported contacts, original movement/rate bounds, common-clock normals,
surface audit and sampled geometry to pass.

`verify(output, expected_result_sha256)` replays complete portable snapshots,
bounded profiles, native transfer fidelity, protected scene intent, normal and
geometry policies, clocks, raw observations and typed decisions. Rehashed
normals, tolerances, planes, controls, observations or approval flags reject.
Whole-clip boundaries may change, so transitions still require validation.

The result leaves geometry/collision certification, anatomical review, engine,
physics and human-quality approvals false. Sampled geometric success is not
continuous collision freedom, self-collision proof, physical balance or a
natural animation. The method accepts arbitrary supported clips and explicit
scene contacts; its evaluation fixtures are not an action whitelist.

## Initial evidence

An independent generated moving scene uses two 19-joint rigs with closed cube
skins, 152 vertices and 228 faces each, a moving box and an authored floor.
Four contacts cover a timed world foot touch, object grip and both partner
directions. The target starts with a deliberately incorrect 10-degree wrist
reference rotation. Point contacts pass before correction; facing and full-mesh
checks are evaluated separately.

The exported correction passes the original point/facing and complete declared
mesh samples. Maximum common-clock opposition error is 0.9989998 degrees
against the unchanged 1-degree limit; maximum point error is 1.036 mm against
5 mm, and maximum hold slip is 0.0112 mm/s against 2 mm/s. It moves no sampled
joint origin, retains the 20 mm author displacement cap, and passes all four
source-rate populations. The common surface population has 1,168 normal rows
and 1,946 actor-pose queries. This is generated software/surface evidence,
without production anatomy, dynamics, semantic action correctness or animator
approval. A declared floor failure remains a rejection even when contact and
normal conditions pass.

An actual serial CPU/headless Godot study saves and reloads both actor Animation
resources for the original and corrected scenes. Each run checks 416 query
times, including the complete common contact and geometry clocks. Each native
geometry audit covers 125 times, and each imported surface audit covers 295
contact samples. The original retains passing points with failing facing and
geometry; the correction passes all three in both native and imported checks.
Maximum imported opposition error falls from 10.0000161 to 0.9990157 degrees
under the same 1-degree limit. Maximum pose component error is 3.68e-7 and raw
skin position error is 3.84e-7 m under unchanged engine tolerances. Both owned
processes exit zero with clean logs. Original inputs and archived methods remain
unchanged; no engine result changes a human, physics or release approval flag.

Engine study receipt SHA256:
`eaa27e9c626fe24ee812a2643bb5eb4036ddeb6fae3a303525d7b20aab058817`.
Generated outputs stay locally under ignored
`reports/native-transfer-surface-calibration-engine-v1`. No live Studio/HTTP,
browser/rendering, GPU, production anatomical asset query, model sampling or
training, or human cleanup review was performed.

Frozen CPU-only regression validation passes **65 tests with zero skips**,
including 15 new surface-calibration contracts and the existing surface/contact
and full-mesh geometry suites. It covers protected intent, source-rate and old
clip preservation, all partner/object/plane populations, complete query budgets,
relocation, rehashed normals/limits/planes/observations/controls/scope changes and
geometry failure despite point/facing success. Copied method hashes still match
current source. Source receipt SHA256:
`a3d543c72acf5737844b2a890deb1e4620b7b41c44f3b79a4ed430a77926b9d6`.

The parsed CI proof adds only the new Python suite, preserving all other
workflow fields, dependencies, pins, environments, permissions, matrices and
time limits. Receipt SHA256:
`f197b1c3760926ac93394253c0c1dc20ca07fe71beb851d3e6c1bd5c92516a97`.
These are local results; hosted CI completion is not inferred.
