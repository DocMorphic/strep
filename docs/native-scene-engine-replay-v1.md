# Complete scene engine replay

`scripts/verify_native_scene_engine.py` replays a terminal, geometry-enabled
`native_scene_engine.py` study in either `import` or `native-authoring` mode.
It accepts the original actor, object, partner and declared-plane populations;
the existing actor-only and separately composed object-resource verifiers retain
their own contracts.

```powershell
python scripts/verify_native_scene_engine.py contacts.json geometry-policy.json reports/my-import reports/my-import-replay
```

Use an already provisioned Python environment with `requirements-ci.txt`.
The source contacts, policy, assets, engine executable, producer output and
implementation must still match their recorded hashes. The replay folder must
be fresh. No checkpoint or Godot subprocess is needed for this replay; the
original engine study must have executed and retained its raw evidence.
Native authoring retains the current LINEAR joint-TRS payload restriction.

The replay checks the complete source/snapshot/method bindings, selected
animations, executed scripts, mode-specific resources and exact original clocks.
It reconstructs all actor poses and loaded skin vertices, object poses and
contacts; checks the saved skin/contact numerical observations; and repeats declared-plane
depth and posed-triangle degeneracy measurements. It verifies geometry archive
transport and recomputes saved object/partner geometry reductions and decisions.
The verifier also freezes its own dependencies and rejects changes during replay.

This shares producer pose/contact decoding. Saved triangle depth, intersection
and partner containment reductions are **not independent geometry queries**.
A complete replay can verify a failed study: `recorded_sampled_conditions_pass`
remains false. It does not approve rendering, physics, runtime events, continuous
collision, human motion quality, training or release.

## Source checks

All **26 focused tests pass**: both modes across actors alone, objects, and
partners plus objects; preservation of a failed geometry result; eighteen altered
or coherently resealed incomplete-evidence cases; and a verifier dependency
change. The tests use tiny skinned fixtures and mocked engine output. They are
source checks, not actual Godot or humanoid motion evidence. The module is in the
public model-free source-test inventory; hosted CI remains separate.

## Complete-body development import

The actual headless Godot 4.7.2 import stage completed for the departure candidate
at all **2,426 original times**, with **18,056 loaded vertices, 36,108 faces and
both original spheres**. It fails the unchanged combined sampled conditions:
actor pose, loaded skin position, imported contact and imported geometry fail;
object pose passes. Maximum engine/native vertex error is
**0.0020734508883721043 m**, above the **0.0001 m** limit. Maximum joint-matrix
element error is **0.009649050242221235**, above its **0.0001** limit.
The imported geometry fails at **1,145 of 2,426 times**, with a worst upper
penetration depth of **0.005062852406036762 m** against the original **0.005 m**
limit. No threshold is relaxed to accept this import. Complete independent
geometry arithmetic now confirms this failed decision, as detailed below.

The completed native geometry and fresh force witnesses do not transfer these
approvals to the engine import. The import output is retained at
`reports/departure-rate-curve-v2/engine-import-v1`; its independently replayed
resource trace contains 3,387 observations and a 722,001,920-byte peak process-tree
RSS under the original 2,048 MiB plus 600 MiB reserve profile. Native-authoring
measurements are running separately; no result is yet claimed for that mode.
This one development fixture does not establish broader action, rig or object
quality. All fourteen release capabilities remain unapproved.

The new scene verifier subsequently completes on this actual import: all original
pose/skin/contact observations and saved geometry reductions agree exactly,
and the combined failed decision stays false. Its separately replayed resource
record covers 292 observations and a 551,944,192-byte peak process-tree RSS,
using the same full profile. The result is saved locally at
`reports/central-hand-physical-v1/general-departure-engine-import-replay-v1`.
This validates evidence consistency, not the independent triangle arithmetic
or acceptability of the animation.

## Independent query diagnosis

The first complete imported geometry arithmetic attempt stops at frame 585,
time 2.36875 s, on face 11683's sphere closest-point witness. It is a failed
attempt, not complete independent evidence. A second instrumented attempt
preserves the same disagreement: the reference witness differs by up to
1.37979517e-9 m, above the unchanged 2e-12 m comparison limit.

An 80-digit Decimal plane/edge calculation using the exact binary64 diagnostic
triangle finds the saved producer witness accurate to within 8e-16 m. The
reference's squared edge distances rounded to a tie near a shared corner,
selecting a distinct, incorrect point. The revised private reference retains
its SVD/edge calculation and uses exact-input, 80-digit refinement where rounded
edge distances are indistinguishable and the witnesses differ by more than the
original comparison tolerance. This changes the calculation; it does not relax
the witness, penetration or contact limits. All **33 focused numeric cases**
pass, covering the recorded disagreement plus 32 synthetic triangles. The complete
full-population replay of this revision subsequently finishes, confirming the
original failed geometry decision rather than accepting the animation.

The failed runs, exact diagnostic inputs, high-precision calculation and numeric
checks remain under `reports/central-hand-physical-v1`, respectively
`departure-engine-import-independent-geometry-guard-v1`,
`departure-engine-import-witness-forensics-guard-v1`,
`engine-import-witness-forensics-v1.json`, `engine-import-witness-decimal-v1.json`
and `engine-import-reference-checks-v2.json`. Their resource traces also replay;
this does not turn either failed full audit into a successful one.

Separately, the [pinned Godot glTF source](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/modules/gltf/gltf_document.cpp#L5472)
resamples joint TRS tracks at a bake rate; the same revision's `generate_scene`
binding defaults to 30 fps. The existing Strep import audit uses that default.
Fixed-rate interpolation is a hypothesis for the larger measured pose drift,
not an established causal attribution. Native-resource authoring preserves
original LINEAR source keys and must still be measured on this complete fixture.

## Complete independent import geometry replay

`independent-departure-engine-import-geometry-v2.json` completes and binds the
original engine/source/method files, stage prerequisites and entire geometry
archive. It independently compares raw eight-influence sum/matmul skin arithmetic,
reconstructs every triangle/object depth bracket and witness with SVD/edge queries,
replays directed closed topology, positive volume and finite-ray object-center
parity, verifies every numerical archive-array hash, and retains all sampled
pass/fail decisions. Engine pose decoding and imported-skin correspondence are
shared; triangle depth producer queries are not reused.

The population is unchanged: **2,426 times, 18,056 vertices, 36,108 faces, two
spheres, 175,196,016 triangle/object queries, 14,557 arrays and 7,007,860,048
logical bytes**. Seventy-six ambiguous edge comparisons receive exact-input
80-digit refinement. Maximum depth-bracket difference is
**1.6653345369377348e-16 m** and maximum witness difference is
**2.942091015256665e-14 m**, both below the unchanged **2e-12 m** comparison limit.
The separately scoped signed-center diagnostic differs by at most
**8.881784197001252e-16 m** under its existing 1e-9 m diagnostic limit.
`sampled_geometry_pass` remains **false**. All 1,145 failed geometry times stay
failed; the original engine drift, contact and pose failures remain unresolved.

The replay guard completes in 743.484 seconds, with all 751 resource observations
independently replayed and a 469,831,680-byte peak process-tree RSS. The original
full-body resource profile remains intact. Proofs remain local under
`reports/central-hand-physical-v1/independent-departure-engine-import-geometry-v2.json`
and `departure-engine-import-independent-geometry-resource-v2.json`. The two
failed earlier reference attempts remain immutable.

## Native-resource authoring retains a smaller geometry failure

The full native-resource run finishes at the same complete clock, geometry
population, source/binary/prerequisite bindings and original tolerances. Its
exported and reloaded Animation resource preserves the original LINEAR keys.
Joint poses, object poses and raw loaded vertex positions at all **2,426 times**
pass their respective tolerances, as do the declared contact samples. Maximum joint-matrix element
discrepancy is **6.813015989148852e-7**; maximum vertex discrepancy is
**9.501026181033346e-5 m**, below the unchanged **1e-4 m** vertex limit.

Full-mesh geometry remains **failed at 1,280 times**. Worst sampled penetration
upper bound is **0.005009943215486333 m**, above the unchanged **0.005 m** limit.
The import-only mode has 1,145 failed times and a larger worst bound of
0.005062852406036762 m. Different failure counts and smaller pose errors do not
establish acceptable geometry. The original native geometry's minimum reserve
is only about 1.96 micrometres. These are one actor and two spheres; the fixture's
object named `box` is a sphere, not the box-lifting benchmark.

The public generalized verifier replays every observation, source/skin/contact
binding and saved reduction exactly, retaining `recorded_sampled_conditions_pass`
as **false**. This is a complete observation/reduction replay, not independent
triangle-distance arithmetic. That separate full-mesh calculation is now running
with the validated independent SVD/edge/Decimal method and original tolerances.

The producer guard completes in **2,378.5 seconds**, with **2,356** resource
observations independently replayed and **932,675,584 bytes** peak process-tree
RSS. The generalized replay completes in **214.422 seconds**; its **229** resource
observations also replay, with **564,178,944 bytes** peak RSS. Both keep the full
2048+600-MiB admission profile. Results remain local in
`reports/departure-rate-curve-v2/engine-native-authoring-v1` and
`reports/central-hand-physical-v1/general-departure-engine-native-authoring-replay-v1`.

A full-clock, full-vertex ordered counterfactual diagnostic is prepared and
syntax-checked to separate Float32 weight normalization, unsigned-16 weight
storage, imported bind/mesh storage and engine pose precision. It requires the
completed independent geometry receipt before execution. No measured attribution
or correction is claimed yet. Native-resource authoring here remains manual
authoring seeks, not real-time AnimationPlayer, GPU skinning or event playback.
No rendering, physics, continuous collision, broader rig/action/interaction
quality or release approval is inferred.
