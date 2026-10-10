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
limit. No threshold is relaxed to accept this import.

The completed native geometry and fresh force witnesses do not transfer these
approvals to the engine import. The import output is retained at
`reports/departure-rate-curve-v2/engine-import-v1`; its independently replayed
resource trace contains 3,387 observations and a 722,001,920-byte peak process-tree
RSS under the original 2,048 MiB plus 600 MiB reserve profile. Independent geometry
arithmetic and native-authoring measurements remain separate pending work.
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
pass, covering the recorded disagreement plus 32 synthetic triangles. Complete
full-population replay of this revision is running and remains unproven.

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
