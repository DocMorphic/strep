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
