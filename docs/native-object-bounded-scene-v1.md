# Bounded object motion with complete imported character checks

The experimental bounded-scene CLI joins [bounded fitting and rigid-object
export](native-object-bounded-fit-v1.md) with the existing [imported scene
checks](native-object-scene-engine-v1.md). A passing rigid object handoff is
only an input requirement; the character's imported motion and complete
declared scene still have to pass their own conditions.

```text
python scripts/native_object_bounded_scene.py passing-fit passing-object-handoff fresh-output --engine path/to/godot
```

The fit and object handoff must be complete and bound to the same checkpointed
proposal and engine executable, with unchanged recorded implementations,
source actors, contact intent, saved observations and geometry. Preflight
checks the original author scene, allows only byte-identical actor path
rebasing, and reconstructs all three saved object-epoch reports and actual
object pose/contact decisions. Altered summaries cannot substitute for their raw
observations. Original-relative movement limits and protected original poses
are preserved; initialization cannot reset the original epoch.

The command imports the unchanged character animation through headless native
Godot authoring on the complete object handoff clock. It archives imported
skin functions, triangle topology, weights, bone observations and Animation
resources. Raw imported weights are not renormalized. The actor producer has
its own contact, pose, full-skin and geometry report; its observations are
then combined with the **actual** object-resource transforms from the bound
handoff. Complete scene geometry is queried again for those combined
observations, rather than copied from the source fit or actor producer.

Read-only scene verification reconstructs all imported skin/contact/object
pose observations and checks every saved triangle-array reduction. It does
not repeat the expensive geometry queries. Producer receipt binding,
containment observations and shared imported-skin reconstruction remain
explicit dependencies. Both default-import and native-authoring object
comparisons are retained.

Object contact and pose fidelity remain separate conditions. For example,
default import may still reach a grip within its 5 mm contact limit while
exceeding the 1 micrometre object-transform fidelity limit. The combined
pose/contact decision retains that failure without rejecting an otherwise
valid native-authoring handoff.

The final decision requires the original bounded object handoff, the complete
combined scene conditions and the saved-result replay to pass together. A
terminal run can report a numerical failure; it preserves all outputs and
keeps the original selected. An execution error leaves a failed pipeline with
its stage outputs intact. Each child stage uses the existing single-worker
lock, and preflight/final handoff checks use that same lock. All output paths
must be fresh.

This remains a CPU/headless authoring operation. It does not certify continuous
collision, self/object-object collision, dynamics, normal-force/grasp stability,
GPU appearance, real-time playback, gameplay-event dispatch or human action
quality. No passing decision changes Studio selection, admits training data,
adds release evidence or marks the full project goal complete.

## Validation

All 11 focused workflow tests pass. Small procedural fixtures exercise the entire workflow with explicitly mocked
engine observations. They check passing full-scene composition and replay,
retained default-import failure, and rejection when actor motion drifts despite
a passing rigid-object handoff. Preflight rejects pending/failed jobs, another
engine, changed original motion, forged epoch summaries, changed raw clocks
and archived-method drift before starting actor import. These fixtures are
orchestration checks, not actual Godot execution or realistic-motion evidence.

The passing fixture uses a constant original object/actor path and binary
edit endpoints so its exterior values remain exactly representable. The
earlier moving-path fixture exposes `6.780e-11` exterior component drift after
export and is explicitly tested as a rejected input. That fixture change
does not loosen the production exterior-preservation gate.

## Actual retained humanoid study

The follow-up completed on the existing ten-point sphere fit and 2,201-time object handoff. The declared target named `box` is a sphere, not a box mesh. One unchanged humanoid has 18,056 vertices and 36,108 faces; the other prop remains unedited. No partner or ground plane is declared.

Both the actual imported-actor stage and the combined native object-resource stage pass their declared sampled conditions at all 2,201 times. Each stage separately queries the complete imported skin against both declared objects, yielding 4,402 actor/object records per stage. The combined skin error is 0.0950103 mm against the 0.1 mm source-fidelity limit. Maximum imported contact-position error is 4.683863 mm against 5 mm. The complete sampled geometry passes, with maximum penetration-depth upper bound 9.818365e-14 m.

Original-relative native object movement remains 1.998049 mm and 0.810380 degrees against unchanged 2 mm and 2 degree limits. All protected original object states are exact in their declared export epoch. Native object-resource pose fidelity and contacts pass; default import still fails and is retained separately. Default sphere pose error is 0.04820018 mm with basis error 0.00048475635. Default success is not inferred from native authoring.

The read-only verifier exactly reconstructs all recorded skin, contact and object observations and the complete saved geometry reductions. It does not independently rerun geometry or establish containment. Study execution and replay took 5,495.422 seconds on the local CPU. Raw source motion and retargeted/imported observations remain separate; the original remains selected.

This is one retained development hold, not a held-out study, anatomical grasp proof, physical support test, broad action-quality result or release approval. No self/object-object or continuous collision, dynamics, runtime gameplay, GPU appearance or human review is certified. Earlier fit/import failures and all release requirements remain unchanged. Local results: `reports/native-object-bounded-scene-development-v1/summary.json` and `scene/verification/result.json`. The publication finalizer verifies all saved receipts and current method bindings; all four prior public CI jobs pass.
